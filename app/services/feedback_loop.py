import re
import random
from sqlalchemy.orm import Session
from app.models import User, Post, DraftPost
from app.services.stats import StatsService
from app.services.llm import query_llm
from app.services.persona import PersonaEngine
from app.config import NUM_PAST_POSTS, W_ENGAGEMENT, W_SENTIMENT

class FeedbackLoopService:
    @staticmethod
    async def generate_draft_post(db: Session, user_id: int, manager):
        # 1. Fetch User and History
        user = db.query(User).filter(User.id == user_id).first()
        past_posts = db.query(Post).filter(Post.user_id == user_id)\
            .order_by(Post.created_at.desc()).limit(NUM_PAST_POSTS).all()
        
        # 2. Analyze Performance & Extract "Banned" Keywords
        context_data = []
        banned_keywords = set()
        total_performance = 0
        
        for p in past_posts:
            # Refresh scores if necessary
            if p.cached_engagement_score == 0.0 or p.cached_sentiment_score == 0.0:
                p.cached_engagement_score = StatsService.calculate_engagement_score(db, p, user)
                p.cached_sentiment_score = await StatsService.calculate_sentiment_score(p)
            
            ult_score = (W_ENGAGEMENT * p.cached_engagement_score) + (W_SENTIMENT * p.cached_sentiment_score)
            total_performance += ult_score
            
            # If the post failed (Low Ult), extract words to avoid repetition
            if ult_score < 0.1:
                # Basic regex to get words > 4 chars to avoid common stop words
                words = re.findall(r'\b\w{5,}\b', p.content.lower())
                banned_keywords.update(words)
            
            context_data.append(
                f"- Content: \"{p.content}\" | Score: {ult_score:.2f} (Eng: {p.cached_engagement_score:.2f}, Sent: {p.cached_sentiment_score:.2f})"
            )
        
        db.commit()

        # 3. Determine Strategy (Exploration vs. Exploitation)
        avg_perf = total_performance / len(past_posts) if past_posts else 0
        is_stagnant = avg_perf < 0.4
        go_rogue = random.random() < 0.25 # 25% chance to force a total topic pivot
        
        # 4. Construct Generalized Prompt
        system_prompt = (
            "You are a Growth Strategist AI. Your goal is to maximize audience attention. "
            "You view 'stagnation' (repetitive scores) as total failure. You are willing "
            "to be provocative, contrarian, or experimental to break a plateau."
        )

        history_text = "\n".join(context_data) if context_data else "No history. This is a fresh start."
        blacklist_str = ", ".join(list(banned_keywords)[:12])

        instruction = (
            f"CORE PERSONA: {user.persona}\n\n"
            f"PERFORMANCE HISTORY:\n{history_text}\n\n"
            f"BANNED KEYWORDS (Audience Rejection): [{blacklist_str}]\n\n"
            "STRATEGIC DIRECTIVE:\n"
        )

        if not past_posts or go_rogue:
            instruction += (
                "ACTION: [EXPLORATION MODE]\n"
                "Ignore recent trends. Write a high-impact, surprising post that introduces a NEW "
                "facet of your persona. Be bold and experimental."
            )
        elif is_stagnant:
            instruction += (
                "ACTION: [CONTRARIAN PIVOT]\n"
                "The current narrative is stale. Identify the 'theme' of your last few posts and "
                "write something that challenges that theme or takes a 180-degree opposite stance "
                "to trigger engagement through debate."
            )
        else:
            instruction += (
                "ACTION: [EVOLUTION MODE]\n"
                "Performance is decent. Slightly evolve the winning concept by adding a "
                "provocative question or a new 'hook,' but DO NOT repeat the same keywords."
            )

        instruction += (
            "\n\nRULES:\n"
            "1. Max 200 characters.\n"
            "2. Do NOT use any Banned Keywords.\n"
            "3. No hashtags or bot-like 'Hello everyone' greetings.\n"
            "4. Return ONLY the post content."
        )

        # 5. Execute LLM Call & Clean Output
        new_content = await query_llm(system_prompt, instruction)
        new_content = new_content.replace('"', '').replace('“', '').replace('”', '').strip()
        
        # 6. Save and Broadcast
        draft = DraftPost(user_id=user.id, content=new_content)
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        await manager.broadcast({
            "type": "draft_ready", 
            "user_id": user_id
        })

    @staticmethod
    async def rewrite_draft(db: Session, draft_id: int, user_directions: str):
        draft = db.query(DraftPost).filter(DraftPost.id == draft_id).first()
        user = draft.author
        
        system_prompt = "You are an AI assistant helping a user refine their social media post."
        instruction = (
            f"Original Draft: {draft.content}\n"
            f"User Persona: {user.persona}\n\n"
            f"User's Directions for Improvement: {user_directions}\n\n"
            "Please rewrite the draft incorporating the user's directions while maintaining their persona. "
            "Return ONLY the updated post content."
        )
        
        updated_content = await query_llm(system_prompt, instruction)
        draft.content = updated_content.replace('"', '').replace('“', '').replace('”', '').strip()
        db.commit()
        return draft.content