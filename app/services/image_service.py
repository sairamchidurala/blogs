import requests
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.config import settings
from models import ImageUrl

class ImageService:
    def __init__(self):
        self.together_url = "https://api.together.xyz/v1/images/generations"

    async def generate_image(self, prompt: str, user: str, chat_id: int, db: AsyncSession) -> Optional[str]:
        try:
            headers = {
                "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "black-forest-labs/FLUX.1-schnell-Free",
                "prompt": prompt,
                "width": 432,
                "height": 768
            }
            
            response = requests.post(self.together_url, json=payload, headers=headers)
            if response.ok:
                image_url = response.json()["data"][0]["url"]
                await self._save_image_record(user, prompt, image_url, chat_id, db)
                return image_url
            return None
        except Exception:
            return None

    async def _save_image_record(self, user: str, query: str, link: str, chat_id: int, db: AsyncSession):
        new_entry = ImageUrl(user=user, query=query, link=link, chat_id=chat_id)
        db.add(new_entry)
        await db.commit()