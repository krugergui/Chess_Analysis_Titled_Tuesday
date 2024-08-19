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
    array_results = []

    for player in results:
        array_results.append({"player": player, "score": results[player]})

    sorted_results = sorted(array_results, key=lambda x: x["score"], reverse=True)

    current_score = None
    position = 1
    for i in range(len(sorted_results)):
        if not current_score:
            current_score = sorted_results[i]["score"]

        sorted_results[i]["position"] = position

        if sorted_results[i]["score"] != current_score:
            current_score = sorted_results[i]["score"]
            position += 1

    silver_events.insert_one(
        {
            "date_processed": datetime.utcnow(),
            "Event": chess_objects[0]["Event"],
            "results": results,
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

            chess_objects.append(chess_object)

        save_to_silver_events(chess_objects, results_event)
        save_to_silver_games(chess_objects)

        chess_objects = []
        results_event = {}

        log_to_logs_silver(f"Finished processing {landing_area_document['url']}")

    log_to_logs_silver("Finished processing all documents")

    client.close()
