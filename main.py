from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from db import get_bot_token, upsert_bot_token, init_db, ImageUrl
import httpx
import os
import requests
from fastapi.templating import Jinja2Templates
import urllib.parse
from markdown import markdown
import re
from sqlalchemy import func
from sqlalchemy.future import select
from db import SessionLocal
from models import Blog
from datetime import datetime
from dotenv import load_dotenv
from gptapi import call_openai, get_category_and_blog
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
async def startup():
    await init_db()

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

@app.post("/webhook/{bot_name}")
async def telegram_webhook(bot_name: str, request: Request):
    query_params = dict(request.query_params)
    token_from_query = query_params.get("token")

    if token_from_query:
        await upsert_bot_token(bot_name, token_from_query)

    token = await get_bot_token(bot_name)
    if not token:
        raise HTTPException(status_code=404, detail="Bot token not found")

    update = await request.json()
    message = update.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]

    if "text" in message:
        user_input = message["text"]
        if user_input.startswith('.image'):
            text = user_input[7:]
            await generate_image(text, chat_id, token, message["from"]["first_name"])
            return {"ok": True}
        
        try:
            gpt_reply = await call_openai(user_input, False)
            sanitized_text = gpt_reply.replace('<', '&lt;').replace('>', '&gt;').replace('`', "'")
            success = await send_api_request(token, "sendMessage", {
                "chat_id": chat_id,
                "text": sanitized_text
            })
            if not success:
                logger.error(f"Failed to send message to chat {chat_id}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await send_api_request(token, "sendMessage", {
                "chat_id": chat_id,
                "text": "⚠️ Sorry, I encountered an error. Please try again."
            })

    return {"ok": True}

@app.get("/blog/category/{category}", response_class=HTMLResponse)
async def category_blogs(request: Request, category: str, page: int = 1):
    if page < 1:
        page = 1
        
    blogs_per_page = 12
    offset = (page - 1) * blogs_per_page
    
    async with SessionLocal() as session:
        # Get total count for category
        total_result = await session.execute(
            select(func.count(Blog.id)).where(Blog.category == category)
        )
        total = total_result.scalar() or 0
        
        if total == 0:
            return templates.TemplateResponse("category_blogs.html", {
                "request": request,
                "blogs": [],
                "category": category,
                "current_page": 1,
                "total_pages": 1
            })
        
        # Get paginated blogs for category
        blogs_result = await session.execute(
            select(Blog)
            .where(Blog.category == category)
            .order_by(Blog.created_at.desc())
            .offset(offset)
            .limit(blogs_per_page)
        )
        blogs = blogs_result.scalars().all()
        
        total_pages = max(1, (total + blogs_per_page - 1) // blogs_per_page)
        
        if page > total_pages:
            return RedirectResponse(url=f"/blog/category/{category}?page={total_pages}")
        
        return templates.TemplateResponse("category_blogs.html", {
            "request": request,
            "blogs": blogs,
            "category": category,
            "current_page": page,
            "total_pages": total_pages
        })

@app.get("/blog/post/{query:path}", response_class=HTMLResponse)
async def individual_blog(request: Request, query: str):
    topic = urllib.parse.unquote(query)
    async with SessionLocal() as session:
        result = await session.execute(select(Blog).where(Blog.query == topic.lower()))
        blog = result.scalar_one_or_none()

        if blog:
            content = markdown(blog.content)
            return templates.TemplateResponse("blog.html", {
                "request": request,
                "content": content,
                "error": None,
                "title": blog.title
            })

        # If not found, get category and generate blog
        category, title, content = await get_category_and_blog(topic)
        if content.startswith("⚠️"):
            return templates.TemplateResponse("blog.html", {
                "request": request,
                "content": "",
                "error": content,
                "title": topic.title()
            })

        blog = Blog(query=topic.lower(), title=title, content=content, category=category)
        session.add(blog)
        await session.commit()

        return templates.TemplateResponse("blog.html", {
            "request": request,
            "content": markdown(content),
            "error": None,
            "title": title
        })

@app.get("/blog", response_class=HTMLResponse)
async def blogs_home(request: Request, query: str = None, page: int = 1):
    if page < 1:
        page = 1
        
    async with SessionLocal() as session:
        if query:
            # Redirect to individual blog post
            return RedirectResponse(url=f"/blog/post/{urllib.parse.quote(query)}")
        
        # Get blogs grouped by category (max 3 per category)
        categories_result = await session.execute(
            select(Blog.category, func.count(Blog.id).label('count'))
            .where(Blog.category.isnot(None))
            .group_by(Blog.category)
            .order_by(func.count(Blog.id).desc())
        )
        categories = categories_result.all()
        
        blogs_by_category = {}
        for category, count in categories:
            blogs_result = await session.execute(
                select(Blog)
                .where(Blog.category == category)
                .order_by(Blog.created_at.desc())
                .limit(3)
            )
            blogs_by_category[category] = {
                'blogs': blogs_result.scalars().all(),
                'total': count
            }
        
        return templates.TemplateResponse("blogs.html", {
            "request": request,
            "blogs_by_category": blogs_by_category,
            "datetime": datetime
        })

async def generate_image(prompt: str, chat_id: int, token: str, user: str):
    together_api_key = os.getenv("TOGETHER_API_KEY")
    together_url = "https://api.together.xyz/v1/images/generations"
    together_headers = {
        "Authorization": f"Bearer {together_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": 432,
        "height": 768
    }
    response = requests.post(together_url, json=payload, headers=together_headers)
    if response.ok:
        image_url = response.json()["data"][0]["url"]
        new_id = await insert_image_url(
            user=user,
            query=prompt,
            link=image_url,
            chat_id=chat_id
        )
        await send_image_to_telegram(image_url, chat_id, token, user)
    else:
        await send_api_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "⚠️ Failed to generate image. Please try again later."
        })

async def send_image_to_telegram(image_url: str, chat_id: int, token: str, user: str):
    telegram_payload = {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": "Here is your generated image"
    }
    await send_api_request(token, "sendPhoto", telegram_payload)

async def insert_image_url(user: str, query: str, link: str, chat_id: int):
    async with SessionLocal() as session:
        new_entry = ImageUrl(user=user, query=query, link=link, chat_id=chat_id)
        session.add(new_entry)
        await session.commit()
        await session.refresh(new_entry)
        return new_entry.id

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/")
async def root():
    return RedirectResponse(url="/blog")