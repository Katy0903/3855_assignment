import connexion
from connexion import NoContent
import json
import os
from datetime import datetime
import httpx
import yaml
import logging
import logging.config
import uuid
from pykafka import KafkaClient


# STORAGE_SERVICE_URL = "http://localhost:8090"

with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')


kafka_config = app_config['events']
kafka_host = kafka_config['hostname']
kafka_port = kafka_config['port']
kafka_topic = kafka_config['topic']


# def send_to_storage_service(event_type, data):
#     try:

#         logger.info(f"Received event {event_type} with a trace id of {data.get('trace_id')}")

#         storage_url = app_config['events'][event_type]['url']
        
#         data["trace_id"] = str(uuid.uuid4())

#         response = httpx.post(storage_url, json=data)

#         logger.info(f"Response for event {event_type} (id: {data.get('trace_id')}) has status {response.status_code}")

#         response.raise_for_status()
#         return response
    
#     except Exception as e:
#         print(f"Error: {e}")
#         return None


def send_to_kafka(event_type, data):
    try:
        logger.info(f"Received event {event_type} with a trace id of {data.get('trace_id')}")

      
        client = KafkaClient(hosts=f'{kafka_host}:{kafka_port}')
        topic = client.topics[str.encode(kafka_topic)]
        producer = topic.get_sync_producer()

     
        data["trace_id"] = str(uuid.uuid4())

        msg = {
            "type": event_type,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "payload": data
        }

        
        msg_str = json.dumps(msg)
        producer.produce(msg_str.encode('utf-8'))  

        logger.info(f"Message for event {event_type} has been sent to Kafka.")
    
    except Exception as e:
        logger.error(f"Error sending to Kafka: {e}")
        return None
    

def post_clientcase(body):

    send_to_kafka("clientcase", body)

    return NoContent, 201  


def post_survey(body):
   
    send_to_kafka("survey", body)

    return NoContent, 201  


app = connexion.FlaskApp(__name__, specification_dir=".")
app.add_api("openapi.yml", base_path="/receiver", strict_validation=True, validate_responses=True)



if __name__ == "__main__":
    app.run(port=8080, host="0.0.0.0")


