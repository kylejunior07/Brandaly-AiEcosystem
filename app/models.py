from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    fn = Column(String)
    ln = Column(String)
    password = Column(String)
    persona = Column(Text)
    
    # Auto-Post Settings (Upgraded to Seconds)
    is_autopost_active = Column(Boolean, default=False)
    autopost_interval_seconds = Column(Integer, default=3600)
    preview_offset_seconds = Column(Integer, default=300)
    next_preview_time = Column(DateTime, nullable=True)
    next_post_time = Column(DateTime, nullable=True)
    
    posts = relationship("Post", back_populates="author")
    comments = relationship("Comment", back_populates="author")
    likes = relationship("Like", back_populates="user")
    drafts = relationship("DraftPost", back_populates="author")

class DraftPost(Base):
    __tablename__ = "draft_posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    author = relationship("User", back_populates="drafts")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    cached_sentiment_score = Column(Float, default=0.0)
    cached_engagement_score = Column(Float, default=0.0)
    
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post")
    likes = relationship("Like", back_populates="post")

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")