import connexion
from connexion import NoContent
import json
import os
from datetime import datetime
import functools
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select 
import time
import yaml
import logging
import logging.config
from datetime import datetime as dt
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from flask import jsonify
import requests
import time
from datetime import datetime
import pytz


with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


# Configuration for external services
processing_url = 'http://processing:8100/processing/ccc/stats'
analyzer_url = 'http://analyzer:8110/analyzer/ccc/clientcase_ids'
storage_url = 'http://storage:8090/storage/ccc/stats'
json_data_store_path = app_config['datastore']['filename']

def get_event_counts(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching event counts from {url}: {e}")
        return None

def get_event_ids(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching event IDs from {url}: {e}")
        return None

def run_consistency_checks():
    start_time = time.time()

    # Get event counts
    processing_stats = get_event_counts(processing_url)
    analyzer_event_ids = get_event_ids(analyzer_url)
    storage_event_ids = get_event_ids(storage_url)

    if not processing_stats or not analyzer_event_ids or not storage_event_ids:
        return {"message": "Error fetching data from services"}

    # Extract counts and event IDs
    processing_counts = processing_stats['counts']
    analyzer_ids = analyzer_event_ids['ids']
    storage_ids = storage_event_ids['ids']

    # Compare event IDs
    missing_in_db = [event for event in analyzer_ids if event['trace_id'] not in [item['trace_id'] for item in storage_ids]]
    missing_in_queue = [event for event in storage_ids if event['trace_id'] not in [item['trace_id'] for item in analyzer_ids]]
    # Prepare result
    result = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "counts": {
            "db": processing_counts['db'],
            "queue": processing_counts['queue'],
            "processing": processing_counts['processing'],
        },
        "missing_in_db": missing_in_db,
        "missing_in_queue": missing_in_queue
    }

    # Write result to JSON datastore
    with open(json_data_store_path, 'w') as f:
        json.dump(result, f, indent=4)

    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Log the results
    print(f"Consistency checks completed | processing_time_ms={processing_time_ms} | missing_in_db={len(missing_in_db)} | missing_in_queue={len(missing_in_queue)}")

    return {"processing_time_ms": processing_time_ms}

def get_checks():
    try:
        with open(json_data_store_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"message": "No consistency checks have been run yet"}





app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/check", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(port=8111, host="0.0.0.0")