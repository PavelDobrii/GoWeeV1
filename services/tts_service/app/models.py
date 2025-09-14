from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True)
    story_id = Column(Integer, nullable=False)
    voice = Column(String(50), nullable=False)
    format = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    duration_sec = Column(Integer, nullable=False, default=0)
