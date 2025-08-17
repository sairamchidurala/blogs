from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
import urllib.parse
from markdown import markdown
from datetime import datetime

from ..core.database import get_db
from ..services.ai_service import AIService
from models import Blog

router = APIRouter()
templates = Jinja2Templates(directory="templates")
ai_service = AIService()

@router.get("/", response_class=HTMLResponse)
async def blogs_home(request: Request, query: str = None, db: AsyncSession = Depends(get_db)):
    if query:
        return RedirectResponse(url=f"/blog/post/{urllib.parse.quote(query)}")
    
    # Get blogs grouped by category
    categories_result = await db.execute(
        select(Blog.category, func.count(Blog.id).label('count'))
        .where(Blog.category.isnot(None))
        .group_by(Blog.category)
        .order_by(func.count(Blog.id).desc())
    )
    categories = categories_result.all()
    
    blogs_by_category = {}
    for category, count in categories:
        blogs_result = await db.execute(
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

@router.get("/post/{query:path}", response_class=HTMLResponse)
async def individual_blog(request: Request, query: str, db: AsyncSession = Depends(get_db)):
    topic = urllib.parse.unquote(query)
    
    # Check if blog exists
    result = await db.execute(select(Blog).where(Blog.query == topic.lower()))
    blog = result.scalar_one_or_none()

    if blog:
        return templates.TemplateResponse("blog.html", {
            "request": request,
            "content": markdown(blog.content),
            "error": None,
            "title": blog.title
        })

    # Generate new blog
    category, title, content = await ai_service.generate_blog_with_category(topic)
    
    if content.startswith("⚠️"):
        return templates.TemplateResponse("blog.html", {
            "request": request,
            "content": "",
            "error": content,
            "title": topic.title()
        })

    # Save to database
    blog = Blog(query=topic.lower(), title=title, content=content, category=category)
    db.add(blog)
    await db.commit()

    return templates.TemplateResponse("blog.html", {
        "request": request,
        "content": markdown(content),
        "error": None,
        "title": title
    })

@router.get("/category/{category}", response_class=HTMLResponse)
async def category_blogs(request: Request, category: str, page: int = 1, db: AsyncSession = Depends(get_db)):
    if page < 1:
        page = 1
        
    blogs_per_page = 12
    offset = (page - 1) * blogs_per_page
    
    # Get total count
    total_result = await db.execute(
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
    
    # Get paginated blogs
    blogs_result = await db.execute(
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