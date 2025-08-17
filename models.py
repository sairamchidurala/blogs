from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class BotConfig(Base):
    __tablename__ = "bot_config"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    token = Column(Text, nullable=False)

class Blog(Base):
    __tablename__ = "blogs"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ImageUrl(Base):
    __tablename__ = "image_urls"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user = Column(String(255), nullable=False)
    query = Column(String(255), nullable=False)
    link = Column(String(500), nullable=False)
    chat_id = Column(Integer, nullable=False)
    createdOn = Column(DateTime, default=func.now())

