import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Form, HTTPException, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Post, Comment, Like, DraftPost
from app.routes.websocket import manager
from app.services.persona import PersonaEngine
from app.services.feedback_loop import FeedbackLoopService
from app.config import W_ENGAGEMENT, W_SENTIMENT
from app.services.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter()

@router.post("/post")
async def create_post(user_id: int = Form(...), content: str = Form(...), background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    new_post = Post(user_id=user_id, content=content)
    db.add(new_post)
    db.commit()
    await manager.broadcast({"type": "new_post"})
    background_tasks.add_task(PersonaEngine.react_to_post, new_post.id, manager)
    return {"status": "Posted"}

@router.post("/like")
async def like_post(user_id: int = Form(...), post_id: int = Form(...), db: Session = Depends(get_db)):
    existing = db.query(Like).filter(Like.user_id == user_id, Like.post_id == post_id).first()
    if existing: db.delete(existing)
    else: db.add(Like(user_id=user_id, post_id=post_id))
    db.commit()
    post = db.query(Post).filter(Post.id == post_id).first()
    await manager.broadcast({"type": "update_likes", "post_id": post_id, "count": len(post.likes), "likers": [u.user_id for u in post.likes]})
    return {"status": "Updated"}

@router.post("/comment")
async def create_comment(user_id: int = Form(...), post_id: int = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    comment = Comment(user_id=user_id, post_id=post_id, content=content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    post = db.query(Post).filter(Post.id == post_id).first()
    await manager.broadcast({"type": "update_comments", "post_id": post_id, "count": len(post.comments), "content": content, "author": comment.author.username})
    return {"status": "Commented"}

@router.post("/api/toggle-autopost")
async def toggle_autopost(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user = db.query(User).filter(User.id == data.get("user_id")).first()
    if user:
        was_active = user.is_autopost_active
        user.is_autopost_active = data.get("active")
        
        if user.is_autopost_active and not was_active:
            user.next_post_time = datetime.utcnow() + timedelta(seconds=user.autopost_interval_seconds)
            user.next_preview_time = user.next_post_time - timedelta(seconds=user.preview_offset_seconds)
        elif not user.is_autopost_active:
            user.next_post_time = None
            user.next_preview_time = None
            
        db.commit()
        return {"status": "updated", "is_autopost_active": user.is_autopost_active}
    raise HTTPException(status_code=404, detail="User not found")

@router.post("/api/profile")
async def update_profile(
    request: Request,
    fn: str = Form(...),
    ln: str = Form(...),
    username: str = Form(...),
    password: str = Form(""),
    persona: str = Form(...),
    is_autopost_active: str = Form(None),
    autopost_interval_value: int = Form(60),
    autopost_interval_unit: str = Form("minutes"),
    preview_offset_value: int = Form(5),
    preview_offset_unit: str = Form("minutes"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: raise HTTPException(status_code=401, detail="Unauthorized")
    
    if username != user.username and db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Calculate total seconds
    multipliers = {"seconds": 1, "minutes": 60, "hours": 3600}
    interval_sec = autopost_interval_value * multipliers.get(autopost_interval_unit, 60)
    offset_sec = preview_offset_value * multipliers.get(preview_offset_unit, 60)

    # Validations
    if interval_sec < 30:
        raise HTTPException(status_code=400, detail="Autopost interval must be at least 30 seconds.")
    if offset_sec < 15:
        raise HTTPException(status_code=400, detail="Preview notification offset must be at least 15 seconds.")
    if offset_sec >= interval_sec:
         raise HTTPException(status_code=400, detail="Preview offset must be smaller than the posting interval.")
        
    user.fn = fn
    user.ln = ln
    user.username = username
    if password.strip():
        user.password = get_password_hash(password)
    user.persona = persona

    was_active = user.is_autopost_active
    active_bool = is_autopost_active == "on"
    user.is_autopost_active = active_bool
    user.autopost_interval_seconds = interval_sec
    user.preview_offset_seconds = offset_sec
    
    if active_bool and not was_active:
        user.next_post_time = datetime.utcnow() + timedelta(seconds=user.autopost_interval_seconds)
        user.next_preview_time = user.next_post_time - timedelta(seconds=user.preview_offset_seconds)
    elif not active_bool:
        user.next_post_time = None
        user.next_preview_time = None
        
    db.commit()
    return {"status": "success"}

@router.get("/api/user-info/{user_id}")
async def get_user_info(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return {"is_autopost_active": user.is_autopost_active if user else False}

@router.get("/api/stats/{user_id}")
async def get_user_stats(user_id: int, db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.user_id == user_id).all()
    data = []
    for p in posts:
        ultimate = (W_ENGAGEMENT * p.cached_engagement_score) + (W_SENTIMENT * p.cached_sentiment_score)
        data.append({"content": p.content[:30], "engagement_score": p.cached_engagement_score, "sentiment_score": p.cached_sentiment_score, "ultimate_score": ultimate})
    return data

@router.post("/api/signup")
async def signup(
    response: Response,
    fn: str = Form(...), 
    ln: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...), 
    persona: str = Form(...), 
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username, 
        fn=fn, 
        ln=ln, 
        password=hashed_password, 
        persona=persona,
        is_autopost_active=False,
        autopost_interval_seconds=3600,
        preview_offset_seconds=300
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token({"sub": str(new_user.id)})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, samesite="lax", max_age=86400)
    return {"status": "success"}

@router.post("/api/login")
async def login(
    response: Response,
    username: str = Form(...), 
    password: str = Form(...), 
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_access_token({"sub": str(user.id)})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, samesite="lax", max_age=86400)
    return {"status": "success"}

@router.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "success"}

@router.get("/api/draft")
async def get_draft(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return None
    draft = db.query(DraftPost).filter(DraftPost.user_id == user.id).first()
    if draft:
        sched = user.next_post_time.timestamp() * 1000 if user.next_post_time else None
        return {"id": draft.id, "content": draft.content, "scheduled_for": sched}
    return None

@router.post("/api/draft/action")
async def handle_draft_action(
    request: Request,
    action: str = Form(...), 
    content: str = Form(None),
    instructions: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: raise HTTPException(status_code=401)
    
    draft = db.query(DraftPost).filter(DraftPost.user_id == user.id).first()
    if not draft: return {"status": "no_draft"}

    if action == "publish":
        new_post = Post(user_id=user.id, content=content or draft.content)
        db.add(new_post)
        db.delete(draft)
        # Advance timers
        user.next_post_time = datetime.utcnow() + timedelta(seconds=user.autopost_interval_seconds)
        user.next_preview_time = user.next_post_time - timedelta(seconds=user.preview_offset_seconds)
        db.commit()
        await manager.broadcast({"type": "new_post"})
        asyncio.create_task(PersonaEngine.react_to_post(new_post.id, manager))
        return {"status": "published"}

    elif action == "save":
        draft.content = content
        db.commit()
        return {"status": "saved"}

    elif action == "refine":
        refined = await FeedbackLoopService.rewrite_draft(db, draft.id, instructions)
        return {"status": "refined", "content": refined}

    elif action == "cancel":
        db.delete(draft)
        user.next_post_time = datetime.utcnow() + timedelta(seconds=user.autopost_interval_seconds)
        user.next_preview_time = user.next_post_time - timedelta(seconds=user.preview_offset_seconds)
        db.commit()
        return {"status": "canceled"}