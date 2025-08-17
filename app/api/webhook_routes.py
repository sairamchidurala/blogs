from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import httpx
import logging

from ..core.database import get_db
from ..services.ai_service import AIService
from ..services.image_service import ImageService
from models import BotConfig

router = APIRouter()
logger = logging.getLogger(__name__)
ai_service = AIService()
image_service = ImageService()

async def send_api_request(token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        logger.error(f"Telegram API Error: {e}")
        return False

@router.post("/{bot_name}")
async def telegram_webhook(bot_name: str, request: Request, db: AsyncSession = Depends(get_db)):
    query_params = dict(request.query_params)
    token_from_query = query_params.get("token")

    if token_from_query:
        # Upsert bot token
        result = await db.execute(select(BotConfig).where(BotConfig.name == bot_name))
        bot = result.scalars().first()
        if bot:
            bot.token = token_from_query
        else:
            bot = BotConfig(name=bot_name, token=token_from_query)
            db.add(bot)
        await db.commit()

    # Get bot token
    result = await db.execute(select(BotConfig).where(BotConfig.name == bot_name))
    bot = result.scalars().first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot token not found")

    update = await request.json()
    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]

    if "text" in message:
        user_input = message["text"]
        user_name = message["from"].get("first_name", "User")
        
        if user_input.startswith('.'):
            # Generate image
            prompt = user_input[1:]
            image_url = await image_service.generate_image(prompt, user_name, chat_id, db)
            
            if image_url:
                await send_api_request(bot.token, "sendPhoto", {
                    "chat_id": chat_id,
                    "photo": image_url,
                    "caption": "Here is your generated image"
                })
            else:
                await send_api_request(bot.token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "⚠️ Failed to generate image. Please try again later."
                })
        else:
            # Generate text response
            try:
                gpt_reply = await ai_service.generate_response(user_input)
                sanitized_text = gpt_reply.replace('<', '&lt;').replace('>', '&gt;').replace('`', "'")
                success = await send_api_request(bot.token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": sanitized_text
                })
                if not success:
                    logger.error(f"Failed to send message to chat {chat_id}")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await send_api_request(bot.token, "sendMessage", {
                    "chat_id": chat_id,
                    "text": "⚠️ Sorry, I encountered an error. Please try again."
                })

    return {"ok": True}