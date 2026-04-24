import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import User, Post, DraftPost
from app.services.stats import StatsService
from app.services.feedback_loop import FeedbackLoopService
from app.services.persona import PersonaEngine
from app.routes.websocket import manager

# --- NEW HELPER FUNCTION ---
# Manages an isolated DB session so the draft task can run in the background
async def _trigger_draft_generation(user_id: int):
    db_session = SessionLocal()
    try:
        await FeedbackLoopService.generate_draft_post(db_session, user_id, manager)
    finally:
        db_session.close()

async def run_autopost_loop():
    print("--- User-Aware Auto-Post Service Started ---")
    while True:
        try:
            db = SessionLocal()
            now = datetime.utcnow()
            active_users = db.query(User).filter(User.is_autopost_active == True).all()
            
            for user in active_users:
                # 1. Has the actual post time arrived?
                if user.next_post_time and now >= user.next_post_time:
                    draft = db.query(DraftPost).filter(DraftPost.user_id == user.id).first()
                    if draft:
                        # Auto-Publish
                        new_post = Post(user_id=user.id, content=draft.content)
                        db.add(new_post)
                        db.delete(draft)
                        db.commit()
                        
                        # --- FIX: Offload network/websocket calls to background tasks ---
                        asyncio.create_task(manager.broadcast({"type": "new_post", "user_id": user.id}))
                        asyncio.create_task(PersonaEngine.react_to_post(new_post.id, manager))
                    
                    # Advance timers for the next cycle
                    user.next_post_time = now + timedelta(seconds=user.autopost_interval_seconds)
                    user.next_preview_time = user.next_post_time - timedelta(seconds=user.preview_offset_seconds)
                    db.commit()
                    
                # 2. If not posting yet, has the preview time arrived?
                elif user.next_preview_time and now >= user.next_preview_time:
                    # Prevent generating a new draft if one is already pending
                    existing_draft = db.query(DraftPost).filter(DraftPost.user_id == user.id).first()
                    if not existing_draft:
                        # --- FIX: Trigger draft generation in an independent task ---
                        asyncio.create_task(_trigger_draft_generation(user.id))
                    
                    # Clear preview time so we don't keep generating
                    user.next_preview_time = None 
                    db.commit()
                    
            db.close()
        except Exception as e:
            print(f"Scheduler Error: {e}")
        
        # Reduced to 5 seconds to guarantee we catch 15-second minimum intervals
        await asyncio.sleep(5) 

async def run_metrics_updater_loop():
    while True:
        try:
            db = SessionLocal()
            posts = db.query(Post).all()
            for post in posts:
                post.cached_engagement_score = StatsService.calculate_engagement_score(db, post, post.author)
                post.cached_sentiment_score = await StatsService.calculate_sentiment_score(post)
            db.commit()
            await manager.broadcast({"type": "analytics_update"})
            db.close()
        except Exception as e:
            print(f"Metrics loop error: {e}")
        finally:
            db.close()
        await asyncio.sleep(15)

async def start_background_tasks():
    await asyncio.gather(
        run_autopost_loop(),
        run_metrics_updater_loop()
    )