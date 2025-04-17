import connexion
from connexion import NoContent
from connexion import FlaskApp
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import yaml
import logging
import logging.config
from datetime import datetime as dt
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify
from pykafka import KafkaClient
from pykafka.common import OffsetType
import os
import time
import pytz


with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

EVENTSTORE_CLIENTCASE_URL = app_config['eventstores']['clientcase']['url']
EVENTSTORE_SURVEY_URL = app_config['eventstores']['survey']['url']

kafka_config = app_config['events']
kafka_host = kafka_config['hostname']
kafka_port = kafka_config['port']
kafka_topic = kafka_config['topic']
kafka_url = f"{kafka_host}:{kafka_port}" 
DATA_FILE = app_config['datastore']['filename']


client = KafkaClient(hosts=kafka_url)
topic = client.topics[str.encode(kafka_topic)]

Max_conversation_time_in_min = 15
Min_satisfaction = 3

def run_anomaly_checks(event_type, index):
    start_time = time.time()

    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    counter = 0
    anomaly=0


    output = { 
        "clientcase": {},
        "survey": {}
    }
    
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)

        if data["type"] == event_type:
            if counter == index:
                logger.info(f"Returning {event_type} event at index {index}")
                
                if event_type == "clientcase":
                    conversation_time_in_min = data["payload"].get("conversation_time_in_min")
                    if conversation_time_in_min > Max_conversation_time_in_min:
                        anomaly += 1
                        output["clientcase"] = data["payload"]
                        logger.debug(f"Anomaly detected in clientcase: {data['payload']}, threshold exceeded: {Max_conversation_time_in_min}")

                elif event_type == "survey":
                    satisfaction = data["payload"].get("satisfaction")
                    if satisfaction < Min_satisfaction:
                        anomaly += 1
                        output["survey"] = data["payload"]
                        logger.debug(f"Anomaly detected in survey: {data['payload']}, threshold exceeded: {Min_satisfaction}")

            counter += 1 



        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump(output, f, indent=4)
        else:
            default_stats = {}
            with open(DATA_FILE, 'w') as file:
                json.dump(default_stats, file, indent=4)


        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Anomaly checks completed | processing_time_ms={duration_ms} "
        )

        return f"anomaly detect: {anomaly}", 200



def get_clientcase_event(index):
    return run_anomaly_checks("clientcase", index)


def get_survey_event(index):
    return run_anomaly_checks("survey", index)



def get_anomalies(event_type=None):

    logger.debug(f"GET /anomalies called with event_type: {event_type}")

    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    if event_type != "clientcase" and event_type != "survey":
        return {"message": "No check has been run."}, 404

    elif event_type == None:
        return data, 200

    elif event_type == "clientcase":
        data = data["clientcase"]
        if data == {}:
            return {"message": "No anomaly detected."}, 204
        return data, 200
    
    elif event_type == "survey":
        data = data["clientcase"]
        if data == {}:
            return {"message": "No anomaly detected."}, 204
        return data, 200


# app = connexion.FlaskApp(__name__, specification_dir='')

app = FlaskApp(__name__)

if "CORS_ALLOW_ALL" in os.environ and os.environ["CORS_ALLOW_ALL"] == "yes":
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )    

app.add_api("openapi.yml", base_path="/anomaly_detector", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(port=8200, host="0.0.0.0")