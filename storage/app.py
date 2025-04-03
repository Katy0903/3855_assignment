import connexion
from connexion import NoContent
import json
import os
from datetime import datetime
import functools
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from db import engine, make_session, create_tables
from models import ClientCase, Survey  
import time
import yaml
import logging
import logging.config
from datetime import datetime as dt
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
from flask import jsonify


with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


MAX_EVENTS = 5
EVENT_FILE = "events.json"  


create_tables()

# def use_db_session(func):
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         session = make_session()
#         try:
#             return func(session, *args, **kwargs)
#         finally:
#             session.close()
#     return wrapper



kafka_config = app_config['events']
kafka_host = kafka_config['hostname']
kafka_port = kafka_config['port']
kafka_topic = kafka_config['topic']


def process_messages():
    """Process event messages from Kafka"""
    hostname = f"{kafka_host}:{kafka_port}"
    topic_name = kafka_topic

  
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(topic_name)]

    
    consumer = topic.get_simple_consumer(
        consumer_group=b'event_group',
        reset_offset_on_start=False,  
        auto_offset_reset=OffsetType.LATEST  
    )

    logger.info(f"Connected to Kafka at {hostname}, listening for messages on topic {topic_name}")

 
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')  
        msg = json.loads(msg_str)  

        logger.info(f"Received message: {msg}")

        payload = msg["payload"]
        event_type = msg["type"]

     
        if event_type == "clientcase":
            store_clientcase(payload)  
        elif event_type == "survey":
            store_survey(payload) 
        else:
            logger.warning(f"Unknown event type: {event_type}")

        consumer.commit_offsets()


def setup_kafka_thread():
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()



def store_clientcase(payload):
    session = make_session()
    try:
        case_id = payload.get("case_id")
        client_id = payload.get("client_id")
        timestamp = payload.get("timestamp")
        conversation_time_in_min = payload.get("conversation_time_in_min")
        trace_id = payload.get("trace_id")

        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

        client_case = ClientCase(
            case_id=case_id,
            client_id=client_id,
            timestamp=timestamp,
            conversation_time_in_min=conversation_time_in_min,
            trace_id=trace_id
        )

        session.add(client_case)
        session.commit()
        logger.info(f"Stored client case with trace_id {trace_id}")

    except Exception as e:
        session.rollback()
        logger.error(f"Error storing clientcase: {e}")
    finally:
        session.close()


def store_survey(payload):
    session = make_session()
    try:
        survey_id = payload.get("survey_id")
        client_id = payload.get("client_id")
        timestamp = payload.get("timestamp")
        satisfaction = payload.get("satisfaction")
        trace_id = payload.get("trace_id")

        timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

        survey = Survey(
            survey_id=survey_id,
            client_id=client_id,
            timestamp=timestamp,
            satisfaction=satisfaction,
            trace_id=trace_id,
        )

        session.add(survey)
        session.commit()
        logger.info(f"Stored survey with trace_id {trace_id}")

    except Exception as e:
        session.rollback()
        logger.error(f"Error storing survey: {e}")
    finally:
        session.close()


def get_clientcase_by_timestamp(start_timestamp, end_timestamp):
    session = make_session()
    try:
        # start_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
        # end_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")

        start_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        end_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")

        statement = select(ClientCase).where(ClientCase.date_created >= start_timestamp).where(ClientCase.date_created < end_timestamp)

        results = [
            result.to_dict() 
            for result in session.execute(statement).scalars().all()
        ]
    
        session.close()
        logger.info("Found %d client cases (start: %s, end: %s)", len(results), start_timestamp, end_timestamp)

        return results 
    
    except Exception as e:
        session.close()
        return []
    
def get_survey_by_timestamp(start_timestamp, end_timestamp):
    session = make_session()
    try:
        start_timestamp = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
        end_timestamp = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")

        statement = select(Survey).where(Survey.date_created >= start_timestamp).where(Survey.date_created < end_timestamp)

        results = [
            result.to_dict() 
            for result in session.execute(statement).scalars().all()
        ]
    
        session.close()
        logger.info("Found %d survey cases (start: %s, end: %s)", len(results), start_timestamp, end_timestamp)

        return results 
    
    except Exception as e:
        session.close()
        return []


def get_event_counts():
    session = make_session()
    try:
        # Count for ClientCase
        client_case_count = session.query(ClientCase).count()

        # Count for Survey
        survey_count = session.query(Survey).count()

        # Return counts in JSON format
        return jsonify({
            "count_clientcase": client_case_count,
            "count_survey": survey_count
        })

    except Exception as e:
        logger.error(f"Error retrieving counts: {e}")
        return jsonify({"error": "Error retrieving counts"}), 500
    finally:
        session.close()

def get_event_ids_and_trace_ids():
    session = make_session()
    try:
        # Retrieve ClientCase IDs and Trace IDs
        client_cases = session.query(ClientCase.event_id, ClientCase.trace_id).all()

        # Retrieve Survey IDs and Trace IDs
        surveys = session.query(Survey.survey_id, Survey.trace_id).all()

        # Combine both lists
        all_events = [{"event_id": case.event_id, "trace_id": case.trace_id, "type": "clientcase"} for case in client_cases]
        all_events += [{"event_id": survey.survey_id, "trace_id": survey.trace_id, "type": "survey"} for survey in surveys]

        return jsonify(all_events)

    except Exception as e:
        logger.error(f"Error retrieving event IDs and trace IDs: {e}")
        return jsonify({"error": "Error retrieving event IDs and trace IDs"}), 500
    finally:
        session.close()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/storage", strict_validation=True, validate_responses=True)

# app.app.add_url_rule('/ccc/stats', 'get_event_counts', get_event_counts, methods=['GET'])
# app.add_url_rule('/ccc/stats/ids', 'get_event_ids_and_trace_ids', get_event_ids_and_trace_ids, methods=['GET'])


if __name__ == "__main__":
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")