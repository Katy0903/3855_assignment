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
from apscheduler.schedulers.background import BackgroundScheduler


with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


# Configuration for external services
processing_url = 'http://acit3855lab9.eastus.cloudapp.azure.com/processing/ccc/stats'
analyzer_url = 'http://acit3855lab9.eastus.cloudapp.azure.com/analyzer/ccc/clientcase_ids'
storage_url = 'http://acit3855lab9.eastus.cloudapp.azure.com/storage/ccc/stats'
DATA_FILE = app_config['datastore']['filename']

def run_consistency_checks():
    start_time = time.time()

    processing_stats = httpx.get(f'{APP_CONF["processing"]["url"]}/stats').json()
    analyzer_stats = httpx.get(f'{APP_CONF["analyzer"]["url"]}/stats').json()
    storage_counts = httpx.get(f'{APP_CONF["storage"]["url"]}/counts').json()

    analyzer_air_ids = httpx.get(f'{APP_CONF["analyzer"]["url"]}/ids/air').json()
    analyzer_traffic_ids = httpx.get(f'{APP_CONF["analyzer"]["url"]}/ids/traffic').json()

    storage_air_ids = httpx.get(f'{APP_CONF["storage"]["url"]}/ids/air').json()
    storage_traffic_ids = httpx.get(f'{APP_CONF["storage"]["url"]}/ids/traffic').json()

    # Tag type with each entry
    analyzer_ids = [
        {"trace_id": e["trace_id"], "event_id": e["event_id"], "type": "air"} for e in analyzer_air_ids
    ] + [
        {"trace_id": e["trace_id"], "event_id": e["event_id"], "type": "traffic"} for e in analyzer_traffic_ids
    ]

    storage_ids = [
        {"trace_id": e["trace_id"], "event_id": e["event_id"], "type": "air"} for e in storage_air_ids
    ] + [
        {"trace_id": e["trace_id"], "event_id": e["event_id"], "type": "traffic"} for e in storage_traffic_ids
    ]

    # Use sets of tuples with type included
    analyzer_set = {(e["trace_id"], e["event_id"], e["type"]) for e in analyzer_ids}
    storage_set = {(e["trace_id"], e["event_id"], e["type"]) for e in storage_ids}

    missing_in_db = [
        {"trace_id": t[0], "event_id": t[1], "type": t[2]} for t in analyzer_set - storage_set
    ]
    missing_in_queue = [
        {"trace_id": t[0], "event_id": t[1], "type": t[2]} for t in storage_set - analyzer_set
    ]

    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "counts": {
            "processing": processing_stats,
            "queue": analyzer_stats,
            "db": storage_counts
        },
        "missing_in_db": missing_in_db,
        "missing_in_queue": missing_in_queue
    }

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=4)

    duration_ms = int((time.time() - start_time) * 1000)
    return {"processing_time_ms": duration_ms}, 200


def get_checks():
    if not os.path.exists(DATA_FILE):
        return {"message": "No consistency check has been run."}, 404

    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data, 200



app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/consistency_check", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(port=8111, host="0.0.0.0")