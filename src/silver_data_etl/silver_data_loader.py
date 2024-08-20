import os
import re
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()


import pymongo
from tqdm import tqdm

MOVES_REGEX = r"[NBRQK]?[a-h]?[1-8]?x?[a-h][1-8][\+|#]?|O-O(?:-O)?"
TIME_REGEX = r"%clk[ |\n]([^\]]+)"

MONGO_DB_USER = os.environ["MONGO_DB_USER"]
MONGO_DB_PASSWORD = os.environ["MONGO_DB_PASSWORD"]
MONGO_DB_HOST = os.environ["MONGO_DB_HOST"]
MONGO_DB_PORT = os.environ["MONGO_DB_PORT"]

client = pymongo.MongoClient(
    f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}/"
)

landing_area_db = client.landing_area
landing_area_games = landing_area_db.games

silver_db = client.silver
silver_games = silver_db.games
silver_events = silver_db.events

logs_db = client.logs
logs_silver = logs_db.silver

timestamp = datetime.now(timezone.utc)


def get_move_clock(times):
    """
    Extract the move times from the moves_with_clock attribute of a chess game object.

    Parameters:
    - times (str): The moves_with_clock attribute containing the move times.

    Returns:
    - list: A list of move times in the format [total time - move 1 time + increment,
             total time - move 2 time + increment, ...].
    """
    # Print example of input string:
    return [int(x[2:4]) * 60 + float(x[5:]) for x in re.findall(TIME_REGEX, times)]


def get_move_times(chess_object):
    """
    Extract the move times from a chess game object.

    Parameters:
    - chess_object (dict): The chess game object containing the move times.

    Returns:
    - list: A list of move times in the format [total time - move 1 time + increment,
             total time - move 2 time + increment, ...].
    """
    times = chess_object["clock"]
    increment = chess_object["Increment"]
    total_time = chess_object["TotalTime"]

    if not times:
        return []

    # If there is only one move, return its time from the total time
    if len(times) == 1:
        return [total_time - times[0] + increment]

    # Initialize the list of move times with the first two moves
    all_times = [total_time - times[0] + increment, total_time - times[1] + increment]

    # Iterate over the remaining moves and calculate their time
    for i in range(2, len(times)):
        all_times.append(times[i - 2] - times[i] + increment)

    return all_times


def get_time_control(chess_object):
    """
    Extract the time control from a chess game.

    Parameters:
    - chess_object (dict): The chess game object containing the time control.

    Returns:
    - (float, float): The time control in the format (total time, increment).
    """
    chess_object.setdefault("TimeControl", "180+2")
    split = chess_object["TimeControl"].split("+")
    return float(split[0]), float(split[1])


def parse_landing_area_document(landing_area_document):
    """
    Parse the landing area document to extract chess game information.

    Parameters:
    - landing_area_document (dict): The landing area document containing data and URL.

    Yields:
    - dict: A dictionary containing extracted chess game information.
    """
    # Split the data into lines
    event_text = landing_area_document["data"]
    url = landing_area_document["url"]
    source = "landing_area.games"

    # Create an empty chess game object
    chess_object = {
        "url": url,
        "source": source,
        "processed_at": timestamp,
    }

    # Iterate over each line in the document
    for line in event_text.splitlines():
        # If the line starts with a bracket, it's a key-value pair
        if line.startswith("["):
            # Extract the key and value from it and add it to the chess object
            key, value = line.strip(" []").split(" ", 1)
            value = value.strip('"')
            chess_object[key] = value
        # Otherwise it's a move
        else:
            # Make sure we have a moves_with_clock key
            chess_object.setdefault("moves_with_clock", "")
            # Add the move to the moves_with_clock
            chess_object["moves_with_clock"] += line.strip() + "\n"

        # If the line ends with a result, means it's the end of the chess object
        if line.endswith("1-0") or line.endswith("0-1") or line.endswith("1/2-1/2"):
            # Extract the time control
            chess_object["TotalTime"], chess_object["Increment"] = get_time_control(chess_object)
            # Extract all the moves and times from the chess object
            chess_object["clock"] = get_move_clock(chess_object["moves_with_clock"])
            chess_object["move_times"] = get_move_times(chess_object)
            chess_object["moves"] = re.findall(MOVES_REGEX, chess_object["moves_with_clock"])

            # Conver elos to float
            if "WhiteElo" in chess_object and "BlackElo" in chess_object:
                chess_object["WhiteElo"], chess_object["BlackElo"] = map(
                    float, (chess_object["WhiteElo"], chess_object["BlackElo"])
                )

            # Yield the completed chess object,
            yield chess_object

            # And start a new chess object
            chess_object = {
                "url": url,
                "source": source,
                "processed_at": timestamp,
            }


def save_to_silver_games(chess_objects):
    """
    Insert many chess objects into the silver_games collection.

    Args:
        chess_objects (list): List of chess objects to be inserted.
    """
    silver_games.insert_many(chess_objects)


def save_to_silver_events(chess_objects, results):
    # Calculate Tie Breaks according to Chess.com Swiss Tournaments Rules
    # https://support.chess.com/en/articles/8572860-how-do-ties-in-tournaments-work
    dict_tiebreaks = {}

    for game in chess_objects:
        # Initialize the tiebreaks for each player
        dict_tiebreaks.setdefault(game["White"], {"player": game["White"]})
        dict_tiebreaks.setdefault(game["Black"], {"player": game["Black"]})
        dict_tiebreaks[game["White"]].setdefault("direct_encounters", [])
        dict_tiebreaks[game["Black"]].setdefault("direct_encounters", [])

        # Set the score for each player that didn't won a single game
        results.setdefault(game["White"], 0)
        results.setdefault(game["Black"], 0)

        dict_tiebreaks[game["White"]]["direct_encounters"].append(results[game["Black"]])
        dict_tiebreaks[game["Black"]]["direct_encounters"].append(results[game["White"]])

        # Sonnenborn-Berger, number of wins, number of wins with black and direct encounter wins
        dict_tiebreaks[game["White"]].setdefault("sonnenborn_berger", 0)
        dict_tiebreaks[game["Black"]].setdefault("sonnenborn_berger", 0)
        dict_tiebreaks[game["White"]].setdefault("number_of_wins", 0)
        dict_tiebreaks[game["Black"]].setdefault("number_of_wins", 0)
        dict_tiebreaks[game["White"]].setdefault("number_of_wins_with_black", 0)
        dict_tiebreaks[game["Black"]].setdefault("number_of_wins_with_black", 0)
        dict_tiebreaks[game["White"]].setdefault("direct_encounter_wins", [])
        dict_tiebreaks[game["Black"]].setdefault("direct_encounter_wins", [])

        if game["Result"] == "1-0":  # white wins
            dict_tiebreaks[game["White"]]["sonnenborn_berger"] += results[game["Black"]]
            dict_tiebreaks[game["White"]]["number_of_wins"] += 1
            dict_tiebreaks[game["White"]]["direct_encounter_wins"].append(game["Black"])
        elif game["Result"] == "0-1":  # black wins
            dict_tiebreaks[game["Black"]]["sonnenborn_berger"] += results[game["White"]]
            dict_tiebreaks[game["Black"]]["direct_encounter_wins"].append(game["White"])
            dict_tiebreaks[game["Black"]]["number_of_wins"] += 1
            dict_tiebreaks[game["Black"]]["number_of_wins_with_black"] += 1
        elif game["Result"] == "1/2-1/2":  # draw
            dict_tiebreaks[game["White"]]["sonnenborn_berger"] += 0.5 * results[game["Black"]]
            dict_tiebreaks[game["Black"]]["sonnenborn_berger"] += 0.5 * results[game["White"]]

        # AROC 1
        dict_tiebreaks[game["White"]].setdefault("opponet_ratings", [])
        dict_tiebreaks[game["Black"]].setdefault("opponet_ratings", [])

        # Some games don't have ratings
        game.setdefault("WhiteElo", 0)
        game.setdefault("BlackElo", 0)
        dict_tiebreaks[game["White"]]["opponet_ratings"].append(game["BlackElo"])
        dict_tiebreaks[game["Black"]]["opponet_ratings"].append(game["WhiteElo"])

        # Own Rating and score
        dict_tiebreaks[game["White"]]["own_rating"] = game["WhiteElo"]
        dict_tiebreaks[game["Black"]]["own_rating"] = game["BlackElo"]
        dict_tiebreaks[game["White"]]["score"] = results[game["White"]]
        dict_tiebreaks[game["Black"]]["score"] = results[game["Black"]]

    # Buchholz cut 1, Buchholz, AROC 1
    for player in dict_tiebreaks:
        # Buchholz cut 1
        dict_tiebreaks[player]["buchholz_cut_1"] = sorted(
            dict_tiebreaks[player]["direct_encounters"]
        )[1:]
        dict_tiebreaks[player]["buchholz_cut_1"] = sum(dict_tiebreaks[player]["buchholz_cut_1"])

        # Buchholz
        dict_tiebreaks[player]["buchholz"] = sum(dict_tiebreaks[player]["direct_encounters"])

        # AROC 1
        dict_tiebreaks[player]["aroc_1"] = sum(
            sorted(dict_tiebreaks[player]["opponet_ratings"])[1:]
        )

    # Sort players by score
    sorted_results = sorted(
        dict_tiebreaks.items(),
        key=lambda x: (
            x[1]["score"],
            x[1]["buchholz_cut_1"],
            x[1]["buchholz"],
            x[1]["sonnenborn_berger"],
            x[1]["number_of_wins"],
            x[1]["number_of_wins_with_black"],
            x[1]["aroc_1"],
            x[1]["own_rating"],
        ),
        reverse=True,
    )

    # Check by direct encounter
    player1 = sorted_results[0]
    player2 = sorted_results[1]

    first_and_second_place_tie = True
    fields_to_check = ["score", "buchholz_cut_1", "buchholz", "sonnenborn_berger"]

    for field in fields_to_check:
        if player1[1][field] != player2[1][field]:
            first_and_second_place_tie = False
            break

    if first_and_second_place_tie:
        sorted_results = sorted_results

    # Save position
    for i in range(len(sorted_results)):
        sorted_results[i][1]["position"] = i + 1
        sorted_results[i] = sorted_results[i][1]

    # Save to Silver_events
    silver_events.insert_one(
        {
            "date_processed": datetime.utcnow(),
            "Event": chess_objects[0]["Event"],
            "Date": chess_objects[0]["Date"],
            "url": chess_objects[0]["url"],
            "results": sorted_results,
        }
    )


def log_to_logs_silver(message):
    logs_silver.insert_one({"time": datetime.utcnow(), "message": message, "file": __file__})


if __name__ == "__main__":
    chess_objects = []
    already_processed_urls = silver_games.distinct("url")
    new_documents = landing_area_games.find({"url": {"$nin": already_processed_urls}})

    total_count = len(list(new_documents.clone()))
    results_event = {}

    for landing_area_document in tqdm(
        new_documents,
        total=total_count,
        desc="Processing documents",
    ):
        log_to_logs_silver(f"Started processing {landing_area_document['url']}")
        for chess_object in parse_landing_area_document(landing_area_document):
            result = chess_object["Result"]
            chess_object["Upset"] = 0
            if result == "1-0":
                results_event.setdefault(chess_object["White"], 0)
                results_event[chess_object["White"]] += 1
                if "WhiteElo" in chess_object and "BlackElo" in chess_object:
                    chess_object["Upset"] = chess_object["WhiteElo"] - chess_object["BlackElo"]
            elif result == "0-1":
                results_event.setdefault(chess_object["Black"], 0)
                results_event[chess_object["Black"]] += 1
                if "WhiteElo" in chess_object and "BlackElo" in chess_object:
                    chess_object["Upset"] = chess_object["BlackElo"] - chess_object["WhiteElo"]
            else:
                results_event.setdefault(chess_object["White"], 0.5)
                results_event.setdefault(chess_object["Black"], 0.5)
                results_event[chess_object["White"]] += 0.5
                results_event[chess_object["Black"]] += 0.5

            # Converts the elos to int or 0 if no elos are available
            chess_object.setdefault("WhiteElo", 0)
            chess_object.setdefault("BlackElo", 0)
            chess_object["WhiteElo"] = int(chess_object["WhiteElo"])
            chess_object["BlackElo"] = int(chess_object["BlackElo"])

            # Converts date to datetime
            chess_object["Date"] = datetime.strptime(chess_object["Date"], "%Y.%m.%d")

            chess_objects.append(chess_object)

        save_to_silver_events(chess_objects, results_event)
        save_to_silver_games(chess_objects)

        chess_objects = []
        results_event = {}

        log_to_logs_silver(f"Finished processing {landing_area_document['url']}")

    log_to_logs_silver("Finished processing all documents")

    client.close()
