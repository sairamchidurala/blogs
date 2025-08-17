import openai
import os
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if USE_GPT else None

async def call_openai(prompt: str, blog_text: bool = False) -> str:
    if USE_GPT:
        return await _call_openai_gpt(prompt, blog_text)
    else:
        return await _call_gemini_simple(prompt, blog_text)

async def _call_openai_gpt(prompt: str, blog_text: bool = False) -> str:
    try:
        if blog_text:
            prompt = f"Write a detailed blog article about: {prompt}. Include an introduction, 3 main sections, and a conclusion. Format with markdown headers."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[OpenAI API Error] {e}")
        return "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

async def _call_gemini_simple(prompt: str, blog_text: bool = False) -> str:
    try:
        if blog_text:
            prompt = f"Write a detailed blog article about: {prompt}. Include an introduction, 3 main sections, and a conclusion. Format with markdown headers."
        
        return await _call_gemini(prompt)
    except Exception as e:
        print(f"[Gemini API Error] {e}")
        return "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

import httpx

USE_GPT = os.getenv("USE_GPT", "true").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

async def get_category_and_blog(topic: str) -> tuple:
    """Get category first, then generate full blog"""
    if USE_GPT:
        return await _get_category_and_blog_gpt(topic)
    else:
        return await _get_category_and_blog_gemini(topic)

async def _get_category_and_blog_gpt(topic: str) -> tuple:
    try:
        # Step 1: Get category
        category_prompt = f"Categorize this topic into one word (fitness, tech, cooking, travel, business, health, finance, education, lifestyle, etc.): {topic}"
        category_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": category_prompt}],
            max_tokens=10,
            temperature=0.3
        )
        category = category_response.choices[0].message.content.strip().lower()
        
        # Step 2: Generate full blog
        blog_prompt = f"Write a comprehensive blog article about: {topic}. Cover all points mentioned in the title. Use markdown headers and provide detailed explanations."
        blog_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": blog_prompt}],
            max_tokens=3000,
            temperature=0.7
        )
        content = blog_response.choices[0].message.content
        
        # Extract title from content
        title_line = next((line for line in content.splitlines() if line.startswith("# ")), None)
        title = title_line[2:].strip() if title_line else topic.title()
        
        return category, title, content
        
    except Exception as e:
        print(f"[OpenAI API Error] {e}")
        return None, None, "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

async def _get_category_and_blog_gemini(topic: str) -> tuple:
    try:
        # Step 1: Get category
        category_prompt = f"Categorize this topic into one word (fitness, tech, cooking, travel, business, health, finance, education, lifestyle, etc.): {topic}"
        category = await _call_gemini(category_prompt)
        category = category.strip().lower()
        
        # Step 2: Generate full blog
        blog_prompt = f"Write a comprehensive blog article about: {topic}. Cover all points mentioned in the title. Use markdown headers and provide detailed explanations."
        content = await _call_gemini(blog_prompt)
        
        # Extract title from content
        title_line = next((line for line in content.splitlines() if line.startswith("# ")), None)
        title = title_line[2:].strip() if title_line else topic.title()
        
        return category, title, content
        
    except Exception as e:
        print(f"[Gemini API Error] {e}")
        return None, None, "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

async def _call_gemini(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    json_data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(GEMINI_URL, headers=headers, params=params, json=json_data)
        response.raise_for_status()
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
