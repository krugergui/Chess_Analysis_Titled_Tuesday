import os
import re
import time

import pymongo
import requests
import tqdm

MONGO_DB_USER = os.environ["MONGO_DB_USER"]
MONGO_DB_PASSWORD = os.environ["MONGO_DB_PASSWORD"]
MONGO_DB_HOST = os.environ["MONGO_DB_HOST"]
MONGO_DB_PORT = os.environ["MONGO_DB_PORT"]

client = pymongo.MongoClient(
    f"mongodb://{MONGO_DB_USER}:{MONGO_DB_PASSWORD}@{MONGO_DB_HOST}:{MONGO_DB_PORT}/"
)

landing_area = client.landing_area
log_db = client.logs


def log(message):
    log_db.logs.insert_one({"time": time.time(), "message": message, "file": __file__})


def insert_new_games():
    start_time = time.time()

    url = "https://chessnerd.net/pgn/chesscom/titled-tuesday/"
    res = requests.get(url)

    # This pattern finds all the links on the titled tuesday page with a ".pgn" extension
    pattern = r'<a\s+(?:[^>]*?\s+)?href="([^"]*?\.pgn)"'
    all_links = re.findall(pattern, res.text)
    already_processed_urls = landing_area.games.distinct("url")

    new_links = [link for link in all_links if link not in already_processed_urls]

    log(f"Started inserting new PGNs at {time.ctime()}")
    try:
        for link in tqdm.tqdm(new_links, desc="Inserting new games", unit="pgn files"):
            game_url = f"https://chessnerd.net/{link}"
            game_res = requests.get(game_url)
            game_data = game_res.text

            log(f"Inserting {game_url} with filesize {len(game_data)}")

            landing_area.games.insert_one({"url": link, "data": game_data})
    except Exception as e:
        log(f"Error while inserting {link}: {e}")

    log(
        f"Finished inserting new PGNs at {time.ctime()}, total time: {time.time() - start_time} seconds"
    )


if __name__ == "__main__":
    insert_new_games()

    client.close()
