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

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

@app.on_event("startup")
async def startup():
    await init_db()

async def send_api_request(token: str, method: str, payload: dict):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as e:
        print(f"[Telegram API Error] {e}")

@app.post("/webhook/{bot_name}")
async def telegram_webhook(bot_name: str, request: Request):
    query_params = dict(request.query_params)
    print("\n=== FastAPI Request ===")
    print("Method:", request.method)
    print("URL:", request.url)
    print("Headers:", dict(request.headers))
    print("Query Params:", dict(request.query_params))
    print("Client Host:", request.client.host)
    try:
        body = await request.json()
        print("JSON Body:", body)
    except:
        print("No JSON body")
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
        if user_input.startswith('.'):
            text = user_input[1:]
            print(f"Generating image for text: {text}")
            await generate_image(text, chat_id, token, message["from"]["first_name"])
            return {"ok": True}
        print(f"Got text: " + user_input)
        gemini_reply = await call_gemini(user_input, False)
        await send_api_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": gemini_reply.replace('<', '&lt;').replace('>', '&gt;').replace('`', "'").replace("trained by Google", "trained by Hell0Kiler")
        })

    elif "photo" in message:
        file_id = message["photo"][-1]["file_id"]
        await send_api_request(token, "sendPhoto", {
            "chat_id": chat_id,
            "photo": file_id,
            "caption": message.get("caption", "")
        })
    elif "video" in message:
        file_id = message["video"]["file_id"]
        await send_api_request(token, "sendVideo", {
            "chat_id": chat_id,
            "video": file_id,
            "caption": message.get("caption", "")
        })
    elif "document" in message:
        file_id = message["document"]["file_id"]
        await send_api_request(token, "sendDocument", {
            "chat_id": chat_id,
            "document": file_id,
            "caption": message.get("caption", "")
        })
    elif "audio" in message:
        file_id = message["audio"]["file_id"]
        await send_api_request(token, "sendAudio", {
            "chat_id": chat_id,
            "audio": file_id,
            "caption": message.get("caption", "")
        })
    elif "voice" in message:
        file_id = message["voice"]["file_id"]
        await send_api_request(token, "sendVoice", {
            "chat_id": chat_id,
            "voice": file_id
        })
    elif "sticker" in message:
        file_id = message["sticker"]["file_id"]
        await send_api_request(token, "sendSticker", {
            "chat_id": chat_id,
            "sticker": file_id
        })
    else:
        await send_api_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "Unsupported message type received."
        })

    return {"ok": True}

@app.get("/blog/{query:path}", response_class=HTMLResponse)
async def blog_page(request: Request, query: str):
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

        # If not found, call Gemini and save
        content = await call_gemini(topic, blog_text=True)
        if content.startswith("⚠️"):
            return templates.TemplateResponse("blog.html", {
                "request": request,
                "content": "",
                "error": content,
                "title": topic.title()
            })

        # Extract title from markdown (usually line starting with ##)
        title_line = next((line for line in content.splitlines() if line.startswith("## ")), None)
        title = title_line[3:].strip() if title_line else topic.title()

        blog = Blog(query=topic.lower(), title=title, content=content)
        session.add(blog)
        await session.commit()

        return templates.TemplateResponse("blog.html", {
            "request": request,
            "content": markdown(content),
            "error": None,
            "title": title
        })

@app.get("/blog", response_class=HTMLResponse)
async def blog_page(request: Request, query: str = None, page: int = 1):
    # Validate page parameter
    if page < 1:
        page = 1
        
    async with SessionLocal() as session:
        if query:
            # Check if blog already exists
            result = await session.execute(select(Blog).where(Blog.query == query))
            existing = result.scalar_one_or_none()

            if existing:
                content_html = markdown(existing.content)
                return templates.TemplateResponse("blog.html", {
                    "request": request,
                    "title": existing.title,
                    "content": content_html
                })
            else:
                # Call Gemini to generate
                raw_content = await call_gemini(query, blog_text=True)
                if raw_content.startswith("⚠️"):
                    return templates.TemplateResponse("blog.html", {
                        "request": request,
                        "title": query,
                        "content": "",
                        "error": raw_content
                    })

                # Extract title from markdown content (e.g., first `## `)
                for line in raw_content.splitlines():
                    if line.strip().startswith("## "):
                        title = line.replace("##", "").strip()
                        break
                else:
                    title = query

                # Save to DB
                new_blog = Blog(query=query, title=title, content=raw_content)
                session.add(new_blog)
                await session.commit()

                content_html = markdown(raw_content)
                return templates.TemplateResponse("blog.html", {
                    "request": request,
                    "title": title,
                    "content": content_html
                })
        else:
            blogs_per_page = 12
            offset = (page - 1) * blogs_per_page
            
            # Get total count
            total_blogs = await session.execute(select(func.count(Blog.id)))
            total = total_blogs.scalar() or 0  # Handle None case
            
            # Return empty response if no blogs
            if total == 0:
                return templates.TemplateResponse("blogs.html", {
                    "request": request,
                    "blogs": [],
                    "current_page": 1,
                    "total_pages": 1,
                    "datetime": datetime
                })
            
            # Get paginated results
            result = await session.execute(
                select(Blog)
                .order_by(Blog.created_at.desc())
                .offset(offset)
                .limit(blogs_per_page)
            )
            blogs = result.scalars().all()
            
            # Calculate total pages (at least 1)
            total_pages = max(1, (total + blogs_per_page - 1) // blogs_per_page)
            
            # If requested page exceeds total, redirect to last page
            if page > total_pages:
                return RedirectResponse(url=f"/blog?page={total_pages}")
            
            return templates.TemplateResponse("blogs.html", {
                "request": request,
                "blogs": blogs,
                "current_page": page,
                "total_pages": total_pages,
                "datetime": datetime
            })

async def call_gemini(prompt: str, blog_text: bool = False) -> str:
    
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    if blog_text:
        prompt = f"Write a detailed blog article about: {prompt}. Include an introduction, 3 main sections, and a conclusion."

    json_data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(GEMINI_URL, headers=headers, params=params, json=json_data)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except httpx.HTTPError as e:
        print(f"[Gemini API Error] {e}")
        return "⚠️ Sorry, I couldn't reach the AI service. Please try again later."
    except Exception as e:
        print(f"[Gemini Unexpected Error] {e}")
        return "⚠️ Something went wrong. Try again later."

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
    print(f"Generating image with prompt: {prompt}")
    print(f"Payload: {payload}")
    response = requests.post(together_url, json=payload, headers=together_headers)
    if response.ok:
        image_url = response.json()["data"][0]["url"]
        print(f"Generated image URL: {image_url}")
        new_id = await insert_image_url(
            user=user,
            query=prompt,
            link=image_url,
            chat_id=chat_id
        )
        print("Inserted row id:", new_id)
        await send_image_to_telegram(image_url, chat_id, token, user)
    else:
        await send_api_request(token, "sendMessage", {
            "chat_id": chat_id,
            "text": "⚠️ Failed to generate image. Please try again later."
        })
        exit()

async def send_image_to_telegram(image_url: str, chat_id: int, token: str, user: str):
    payload = {
        "chat_id": chat_id,
        "photo": image_url
    }
    telegram_payload = {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": "Here is your generated image"
    }
    await send_api_request(token, "sendPhoto", telegram_payload)

# --- Insert Function ---
async def insert_image_url(user: str, query: str, link: str, chat_id: int):
    async with SessionLocal() as session:
        new_entry = ImageUrl(user=user, query=query, link=link, chat_id=chat_id)
        session.add(new_entry)
        await session.commit()
        await session.refresh(new_entry)  # get id after insert
        return new_entry.id   # returning inserted row id
