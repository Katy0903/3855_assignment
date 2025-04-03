import connexion
from connexion import NoContent
from connexion import FlaskApp
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import json
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import ClientCase, Survey  
import yaml
import logging
import logging.config
from datetime import datetime as dt
from apscheduler.schedulers.background import BackgroundScheduler
from flask import jsonify
from pykafka import KafkaClient
from pykafka.common import OffsetType
import os

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

client = KafkaClient(hosts=kafka_url)
topic = client.topics[str.encode(kafka_topic)]

def get_event(event_type, index):

    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    counter = 0
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)

        if data["type"] == event_type:
            if counter == index:
                logger.info(f"Returning {event_type} event at index {index}")
                return data["payload"], 200
            counter += 1 

    return { "message": f"No {event_type} message at index {index}!"}, 404


def get_clientcase_event(index):
    return get_event("clientcase", index)


def get_survey_event(index):
    return get_event("survey", index)



def get_event_stats():
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)

    clientcase_count = 0
    survey_count = 0

    for msg in consumer:
        # if msg is None:
        #     break
        message = msg.value.decode("utf-8")
        data = json.loads(message)

        # logger.info(f"Consumed message: {data}")  

        if data["type"] == "clientcase":
            clientcase_count += 1
        elif data["type"] == "survey":
            survey_count += 1

    stats = {
        "num_clientcase_events": clientcase_count,
        "num_survey_events": survey_count
    }

    logger.info(f"Returning event stats: {stats}")
    return jsonify(stats), 200

def get_all_clientcase_ids():
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    
    results = []
    
    for msg in consumer:

        if msg is None:
            break
        try:
            message = msg.value.decode("utf-8")
            data = json.loads(message)
            
            if data["type"] == "clientcase":
                payload = data["payload"]
                results.append({
                    "event_id": payload.get("case_id"),  
                    "trace_id": payload.get("trace_id")
                })
    
        except Exception as e:
            logger.warning("Skipping message: %s", str(e))
            continue

    return results, 200

def get_all_survey_ids():
    consumer = topic.get_simple_consumer(reset_offset_on_start=True, consumer_timeout_ms=1000)
    
    results = []
    
    for msg in consumer:

        if msg is None:
            break
        try:
            message = msg.value.decode("utf-8")
            data = json.loads(message)
            
            if data["type"] == "survey":
                payload = data["payload"]
                results.append({
                    "event_id": payload.get("survey_id"),  
                    "trace_id": payload.get("trace_id")
                })
    
        except Exception as e:
            logger.warning("Skipping message: %s", str(e))
            continue

    return results, 200


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

app.add_api("openapi.yml", base_path="/analyzer", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(port=8110, host="0.0.0.0")