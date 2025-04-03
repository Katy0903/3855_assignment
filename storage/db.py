from sqlalchemy import create_engine
from models import Base
import sys
from sqlalchemy.orm import sessionmaker
import yaml


with open('./config/app_conf.yml', 'r') as f:
    app_config = yaml.safe_load(f.read())


config = app_config['datastore']
user = config['user']
password = config['password']
hostname = config['hostname']
port = config['port']
db_name = config['db']



# engine = create_engine("sqlite:///my_storage.db")
# engine = create_engine("mysql://katy:Password@localhost:3306/acit3855_db")
engine = create_engine(f"mysql://{user}:{password}@{hostname}:{port}/{db_name}")


def make_session():
    return sessionmaker(bind=engine)()


def create_tables():
    Base.metadata.create_all(engine)

    
def drop_tables():
    Base.metadata.drop_all(engine)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        drop_tables()
    create_tables()