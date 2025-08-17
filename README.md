# Telegram Bot with Blog System

A FastAPI-based Telegram bot that generates AI responses and creates blog posts using Gemini AI, with image generation capabilities.

## Features

- **Telegram Bot**: Handles messages, photos, videos, documents, audio, voice, and stickers
- **AI Chat**: Uses Google Gemini API for intelligent responses
- **Image Generation**: Creates images from text prompts using Together AI
- **Blog System**: Auto-generates and serves blog posts via web interface
- **Database**: MySQL storage for bot tokens, blogs, and image URLs

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Environment Variables**
   ```env
   # API Keys
   GEMINI_API_KEY=your_gemini_api_key
   TOGETHER_API_KEY=your_together_api_key
   OPENAI_API_KEY=your_openai_api_key

   # Database
   DB_USER=your_db_user
   DB_PASS=your_db_password
   DB_HOST=localhost
   DB_PORT=3307
   DB_NAME=telegram
   ```

4. **Run Application**
   ```bash
   uvicorn main:app --reload
   ```

## Usage

### Telegram Bot
- Set webhook: `POST /webhook/{bot_name}?token=YOUR_BOT_TOKEN`
- Text messages get AI responses
- Prefix with `.` for image generation (e.g., `.sunset beach`)

### Blog System
- View all blogs: `GET /blog`
- Specific blog: `GET /blog/{topic}`
- Auto-generates content if not exists

## API Endpoints

- `POST /webhook/{bot_name}` - Telegram webhook
- `GET /blog` - Blog listing with pagination
- `GET /blog/{query}` - Individual blog post

## Scripts

- `./start_bot.sh` - Start the application
- `./stop_bot.sh` - Stop the application