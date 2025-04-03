from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, BigInteger, Float, String, DateTime, func
from datetime import datetime


class Base(DeclarativeBase):
    pass


class ClientCase(Base):
    __tablename__ = "client_case"

    case_id = mapped_column(String(36), primary_key=True)  
    client_id = mapped_column(String(36), nullable=False) 
    timestamp = mapped_column(DateTime, nullable=False)  
    conversation_time_in_min = mapped_column(Float, nullable=False)  
    date_created = mapped_column(DateTime, nullable=False, default=func.now())  
    trace_id = mapped_column(String(36), nullable=False) 

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "client_id": self.client_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),  
            "conversation_time_in_min": self.conversation_time_in_min,
            "date_created": self.date_created.strftime("%Y-%m-%dT%H:%M:%S"),  
            "trace_id": self.trace_id
        }

class Survey(Base):
    __tablename__ = "survey"

    survey_id = mapped_column(String(36), primary_key=True) 
    client_id = mapped_column(String(36), nullable=False)  
    timestamp = mapped_column(DateTime, nullable=False)  
    satisfaction = mapped_column(Integer, nullable=False)  
    date_created = mapped_column(DateTime, nullable=False, default=func.now()) 
    trace_id = mapped_column(String(36), nullable=False) 

    def to_dict(self):
        return {
            "survey_id": self.survey_id,
            "client_id": self.client_id,
            "timestamp": self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"),  
            "satisfaction": self.satisfaction,
            "date_created": self.date_created.strftime("%Y-%m-%dT%H:%M:%S"),  
            "trace_id": self.trace_id
        }