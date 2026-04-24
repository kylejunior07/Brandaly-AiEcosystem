import re
from sqlalchemy.orm import Session
from app.models import Post, User
from app.services.llm import query_llm

class StatsService:
    @staticmethod
    def calculate_engagement_score(db: Session, post: Post, user: User) -> float:
        post_likes_count = len(post.likes)
        user_posts = db.query(Post).filter(Post.user_id == user.id).all()
        if not user_posts: return 0.0
            
        total_likes = sum(len(p.likes) for p in user_posts)
        avg_likes = total_likes / len(user_posts)

        if avg_likes == 0: return 0.0
        return (post_likes_count - avg_likes) / avg_likes

    @staticmethod
    async def calculate_sentiment_score(post: Post) -> float:
        if not post.comments: return 0.5
        comments_text = "\n".join([f"- {c.content}" for c in post.comments])
        prompt = (
            f"Analyze the following comments for a post:\n\n{comments_text}\n\n"
            "Scoring Scale:\n"
            "0: Extremely hostile, hateful, or negative.\n"
            "50: Neutral, mixed, or purely informational.\n"
            "100: Extremely positive, supportive, or enthusiastic.\n\n"
            "What is the collective sentiment score? (0-100):"
        )
        system_prompt = (
            "You are a linguistic sentiment analyst. Your task is to evaluate the collective mood of social media comments. "
            "Output ONLY a single integer between 0 and 100. No text, no explanation."
        )

        response = await query_llm(system_prompt, prompt)
        try:
            import re
            match = re.search(r'\d+', response)
            if match: return min(max(int(match.group()), 0), 100) / 100.0
            return 0.5
        except: return 0.5
