from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    poi_id = Column(Integer, nullable=False)
    lang = Column(String(10), nullable=False)
    markdown = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
