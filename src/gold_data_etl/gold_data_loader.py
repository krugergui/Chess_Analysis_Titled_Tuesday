import os
from datetime import datetime

import pymongo

MONGO_DB_USER = os.environ["MONGO_DB_USER"]
MONGO_DB_PASSWORD = os.environ["MONGO_DB_PASSWORD"]
MONGO_DB_HOST = os.environ["MONGO_DB_HOST"]
MONGO_DB_PORT = os.environ["MONGO_DB_PORT"]

client = pymongo.MongoClient(
    f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}/"
)

match_double_elimination_era = {
    "$match": {
        "Date": {
            "$gte": datetime(2022, 1, 31),
        }
    }
}


def get_total_number_of_editions():
    query_total_editions = [
        match_double_elimination_era,
        {"$count": "total_editions"},
    ]

    return list(client.silver.events.aggregate(query_total_editions))


def get_total_number_of_players():
    query_total_number_of_players = [
        {
            "$group": {
                "_id": None,
                "black_players": {"$addToSet": "$Black"},
                "white_players": {"$addToSet": "$White"},
            }
        },
        {
            "$project": {
                "_id": None,
                "players": {"$concatArrays": ["$black_players", "$white_players"]},
            }
        },
        {"$unwind": {"path": "$players"}},
        {"$group": {"_id": None, "players": {"$addToSet": "$players"}}},
        {"$project": {"_id": 0, "size": {"$size": "$players"}}},
    ]

    return list(client.silver.games.aggregate(query_total_number_of_players))


def get_most_sucessuful_players():
    winners = client.silver.events.aggregate(
        [
            match_double_elimination_era,
            {
                "$project": {
                    "results": {
                        "$filter": {
                            "input": "$results",
                            "as": "r",
                            "cond": {"$eq": ["$$r.position", 1]},
                        }
                    }
                }
            },
        ]
    )

    dict_winners = {}

    for i in winners:
        for winner in i["results"]:
            dict_winners.setdefault(winner["player"], 0)
            dict_winners[winner["player"]] += 1

    dict_winners = [{"player": key, "wins": value} for key, value in dict_winners.items()]

    return dict_winners


def get_players_with_most_games_played():
    query_total_games_per_player = [
        match_double_elimination_era,
        {"$project": {"White": 1, "Black": 1, "_id": 0}},
        {"$project": {"values": {"$objectToArray": "$$ROOT"}}},
        {"$unwind": "$values"},
        {"$group": {"_id": "$values.v", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
        {"$project": {"_id": 0, "player": "$_id", "count": 1}},
    ]

    return list(client.silver.games.aggregate(query_total_games_per_player))


def get_players_with_most_editions():
    query_total_games_per_player = [
        {
            "$project": {
                "Event": 1,
                "White": {"Event": "$Event", "player": "$White"},
                "Black": {"Event": "$Event", "player": "$Black"},
            }
        },
        {"$project": {"Event": 1, "players": {"$setUnion": [["$White"], ["$Black"]]}}},
        {"$unwind": "$players"},
        {"$replaceRoot": {"newRoot": "$players"}},
        {
            "$group": {
                "_id": {"event": "$Event", "player": "$player"},
            }
        },
        {"$replaceRoot": {"newRoot": "$_id"}},
        {"$group": {"_id": "$player", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 100},
        {"$project": {"_id": 0, "player": "$_id", "count": 1}},
    ]

    return list(client.silver.games.aggregate(query_total_games_per_player))


def get_biggest_upsets(player=None):
    query_biggest_upsets = [
        match_double_elimination_era,
        {"$match": {"WhiteElo": {"$gt": 1000}, "BlackElo": {"$gt": 1000}}},
        {"$sort": {"Upset": 1}},
        {"$limit": 20},
        {
            "$project": {
                "_id": 0,
                "Event": 1,
                "Upset": 1,
                "White": 1,
                "WhiteElo": 1,
                "Black": 1,
                "BlackElo": 1,
            },
        },
    ]

    if player:
        query_biggest_upsets.insert(1, {"$match": {"$or": [{"White": player}, {"Black": player}]}})

    biggest_upsets = list(client.silver.games.aggregate(query_biggest_upsets))

    for game in biggest_upsets:
        game["Chances of Upset in %"] = 1 / (1 + 10 ** (-game["Upset"] / 400)) * 100

    return biggest_upsets


def get_winrate_white():
    white_wins = client.silver.games.aggregate(
        [
            match_double_elimination_era,
            {"$match": {"Result": "1-0"}},
            {"$count": "white_wins"},
        ]
    ).next()["white_wins"]

    black_wins = client.silver.games.aggregate(
        [
            match_double_elimination_era,
            {"$match": {"Result": "0-1"}},
            {"$count": "black_wins"},
        ]
    ).next()["black_wins"]

    return {"winrate_in_percentage": white_wins / (black_wins + white_wins) * 100}


if __name__ == "__main__":
    client.gold.biggest_upsets.insert_many(get_biggest_upsets())
    client.gold.biggest_upsets_magnus_calsen.insert_many(get_biggest_upsets("Carlsen, Magnus"))
    client.gold.biggest_upsets_nakamura_hikaru.insert_many(get_biggest_upsets("Nakamura, Hikaru"))

    client.gold.players_with_most_editions.insert_many(get_players_with_most_editions())

    client.gold.players_with_most_games_played.insert_many(get_players_with_most_games_played())

    client.gold.most_sucessuful_players.insert_many(get_most_sucessuful_players())

    client.gold.total_number_of_players.insert_many(get_total_number_of_players())

    client.gold.total_number_of_editions.insert_many(get_total_number_of_editions())

    client.gold.winrate_white.insert_one(get_winrate_white())

    client.close()
