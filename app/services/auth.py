import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Request, Depends

from app.database import get_db
from app.models import User


# In production, load this from your .env file
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-simulation-key-2026")
ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the hashed version."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Generates a JSON Web Token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=1440)) # 24 hour expiry
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Reads the HTTP-Only cookie to authenticate the user for protected routes."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    try:
        # Strip out 'Bearer ' if it exists in the cookie string
        if token.startswith("Bearer "):
            token = token[7:]
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except jwt.PyJWTError:
        return None
        
    return db.query(User).filter(User.id == int(user_id)).first()