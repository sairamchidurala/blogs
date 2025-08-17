import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS") 
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME")
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
    
    # App
    USE_GPT = os.getenv("USE_GPT", "true").lower() == "true"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    @property
    def database_url(self) -> str:
        return f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

settings = Settings()