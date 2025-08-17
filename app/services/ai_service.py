import openai
import httpx
from typing import Tuple, Optional
from ..core.config import settings

class AIService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.USE_GPT else None
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    async def generate_response(self, prompt: str) -> str:
        if settings.USE_GPT:
            return await self._call_openai(prompt)
        return await self._call_gemini(prompt)

    async def generate_blog_with_category(self, topic: str) -> Tuple[Optional[str], Optional[str], str]:
        try:
            if settings.USE_GPT:
                return await self._generate_blog_gpt(topic)
            return await self._generate_blog_gemini(topic)
        except Exception as e:
            return None, None, "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

    async def _call_openai(self, prompt: str) -> str:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception:
            return "⚠️ Sorry, I couldn't reach the AI service. Please try again later."

    async def _generate_blog_gpt(self, topic: str) -> Tuple[str, str, str]:
        # Get category
        category_response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Categorize this topic into one word: {topic}"}],
            max_tokens=10,
            temperature=0.3
        )
        category = category_response.choices[0].message.content.strip().lower()
        
        # Generate blog
        blog_response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Write a comprehensive blog article about: {topic}"}],
            max_tokens=3000,
            temperature=0.7
        )
        content = blog_response.choices[0].message.content
        
        # Extract title
        title_line = next((line for line in content.splitlines() if line.startswith("# ")), None)
        title = title_line[2:].strip() if title_line else topic.title()
        
        return category, title, content

    async def _call_gemini(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        params = {"key": settings.GEMINI_API_KEY}
        json_data = {"contents": [{"parts": [{"text": prompt}]}]}
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(self.gemini_url, headers=headers, params=params, json=json_data)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]

    async def _generate_blog_gemini(self, topic: str) -> Tuple[str, str, str]:
        category = await self._call_gemini(f"Categorize this topic into one word: {topic}")
        category = category.strip().lower()
        
        content = await self._call_gemini(f"Write a comprehensive blog article about: {topic}")
        
        title_line = next((line for line in content.splitlines() if line.startswith("# ")), None)
        title = title_line[2:].strip() if title_line else topic.title()
        
        return category, title, content