import uvicorn
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base, SessionLocal
from app.models import User
from app.routes import api, views, websocket
from app.tasks import start_background_tasks
from app.services.persona import seed_database_internal

# Initialize Database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Social Ecosystem")

# Mount static files (using the templates folder for simplicity as per original)
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Include Routers
app.include_router(views.router)
app.include_router(api.router)
app.include_router(websocket.router)

@app.on_event("startup")
async def startup_event():
    # Auto Seed Logic
    db = SessionLocal()
    try:
        if not db.query(User).first():
            print("Database empty. Seeding users...")
            await seed_database_internal(db)
    finally:
        db.close()
    
    # Start Background Loops
    asyncio.create_task(start_background_tasks())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)