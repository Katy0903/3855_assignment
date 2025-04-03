import connexion
from connexion import NoContent
from connexion import FlaskApp
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
import json
import os
from datetime import datetime
import functools
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models import ClientCase, Survey  
import time
import yaml
import logging
import logging.config
from datetime import datetime as dt
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import httpx
import pytz


with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


with open("./config/log_conf.yml", "r") as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

STATS_FILE_PATH = app_config['datastore']['filename']

EVENTSTORE_CLIENTCASE_URL = app_config['eventstores']['clientcase']['url']
EVENTSTORE_SURVEY_URL = app_config['eventstores']['survey']['url']




def read_stats():

    if os.path.exists(STATS_FILE_PATH):
        with open(STATS_FILE_PATH, 'r') as file:
            return json.load(file)
    else:
        default_stats = {
            "num_client_case_readings": 0,
            "max_conversation_time": 0.0,
            "num_survey_readings": 0,
            "max_survey_satisfaction": 0,
            "last_updated": "2024-01-01 00:00:00"
        }
        write_stats(default_stats)
        return default_stats

def write_stats(stats):

    with open(STATS_FILE_PATH, 'w') as file:
        json.dump(stats, file, indent=4)

   

def get_stats():
    logger.info("Received request for /stats")
    
    stats = read_stats()

    logger.debug(f"Current stats: {stats}")
    logger.info("Request for /stats completed.")
    
    return stats, 200



def populate_stats():
    logger.info("Periodic processing has started.")
    
    stats = read_stats()
    
    last_updated_timestamp = stats["last_updated"]
    last_updated = datetime.strptime(last_updated_timestamp, "%Y-%m-%d %H:%M:%S")
    
    now = datetime.now(pytz.utc) 

    start_timestamp = last_updated.strftime("%Y-%m-%d %H:%M:%S")
    end_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
       
        response_clientcase = httpx.get(f"{EVENTSTORE_CLIENTCASE_URL}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
        if response_clientcase.status_code == 200:
            clientcases = response_clientcase.json()
            logger.info(f"Received {len(clientcases)} new client case events")
        else:
            logger.error(f"Error retrieving client case events: {response_clientcase.status_code}")
            clientcases = []
        
      
        response_survey = httpx.get(f"{EVENTSTORE_SURVEY_URL}?start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")
        if response_survey.status_code == 200:
            surveys = response_survey.json()
            logger.info(f"Received {len(surveys)} new survey events")
        else:
            logger.error(f"Error retrieving survey events: {response_survey.status_code}")
            surveys = []

       
        stats["num_client_case_readings"] += len(clientcases)
        if clientcases:
            max_conversation_time = max([case['conversation_time_in_min'] for case in clientcases])
            stats["max_conversation_time"] = max(stats["max_conversation_time"], max_conversation_time)
        
        stats["num_survey_readings"] += len(surveys)
        if surveys:
            max_satisfaction = max([survey['satisfaction'] for survey in surveys])
            stats["max_survey_satisfaction"] = max(stats["max_survey_satisfaction"], max_satisfaction)

        
        stats["last_updated"] = now.strftime("%Y-%m-%d %H:%M:%S")
        
       
        write_stats(stats)

        logger.info("Periodic processing has ended.")
    
    except Exception as e:
        logger.error(f"Error during periodic processing: {e}")



def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats, 'interval', seconds=app_config['scheduler']['interval'])
    sched.start()


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

app.add_api("openapi.yml", base_path="/processing", strict_validation=True, validate_responses=True)



if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")