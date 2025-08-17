from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy import Column, Integer, String, DateTime, func
from datetime import datetime
from models import Base, BotConfig
from config import DB_USER, DB_PASS, DB_HOST, DB_NAME, DB_PORT

DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_bot_token(name: str):
    async with SessionLocal() as session:
        result = await session.execute(select(BotConfig).where(BotConfig.name == name))
        bot = result.scalars().first()
        return bot.token if bot else None

async def upsert_bot_token(name: str, token: str):
    async with SessionLocal() as session:
        result = await session.execute(select(BotConfig).where(BotConfig.name == name))
        bot = result.scalars().first()
        if bot:
            bot.token = token
        else:
            bot = BotConfig(name=name, token=token)
            session.add(bot)
        await session.commit()

# --- Model ---
class ImageUrl(Base):
    __tablename__ = "image_urls"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user = Column(String(255), nullable=False)
    query = Column(String(255), nullable=False)
    link = Column(String(500), nullable=False)
    chat_id = Column(Integer, nullable=False)
    createdOn = Column(DateTime, default=func.now())  # auto timestamp
