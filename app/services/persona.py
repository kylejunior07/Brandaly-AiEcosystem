import random
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Post, Like, Comment
from app.services.llm import query_llm
from app.config import NUM_REACTORS
from app.services.auth import get_password_hash

class PersonaEngine:
    @staticmethod
    async def react_to_post(post_id: int, manager):
        db = SessionLocal()
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post: return
        
        author = post.author
        other_users = db.query(User).filter(User.id != author.id).all()
        limit = min(len(other_users), NUM_REACTORS)
        reactors = random.sample(other_users, limit) 

        for user in reactors:
            # 1. Check Like
            like_system = (
                "You are simulating a specific social media user. "
                "Your goal is to decide if a post aligns with your values, interests, or sense of humor."
            )
            like_user = (
                f"YOUR PERSONA: {user.persona}\n"
                f"POST CONTENT: \"{post.content}\"\n\n"
                "Would you 'Like' this post? Consider if it triggers a positive or supportive reaction "
                "based on your specific likes and hates. Answer ONLY 1 (YES) or 0 (NO)"
            )

            decision = await query_llm(like_system, like_user)

            existing_like = db.query(Like).filter(Like.user_id == user.id, Like.post_id == post.id).first()

            if decision == "1" and not existing_like:
                db.add(Like(user_id=user.id, post_id=post.id))
                db.commit()
                # Broadcast Like
                updated_post = db.query(Post).filter(Post.id == post.id).first()
                await manager.broadcast({
                    "type": "update_likes",
                    "post_id": post.id,
                    "count": len(updated_post.likes),
                    "likers": [u.user_id for u in updated_post.likes]
                })

            if (decision == "1" and random.random() < 0.5) or (decision != "1" and random.random() < 0.25) :
                if decision == "1":    
                    comment_user = (
                        f"YOUR PERSONA: {user.persona}\n"
                        f"POST YOU JUST LIKED THIS POST: \"{post.content}\"\n\n"
                        "Task: Decide if you have something to add. If you do, provide a short comment."
                        "Constraint: Keep it under 15 words and match your persona's vocabulary."
                        "You should have a positive tone"
                    )
                else:
                    comment_user = (
                        f"YOUR PERSONA: {user.persona}\n"
                        f"POST YOU DIDN'T LIKED THIS POST: \"{post.content}\"\n\n"
                        "Task: Decide if you have something to add. If you do, provide a short comment "
                        "Constraint: Keep it under 15 words and match your persona's vocabulary."
                        "You should have a negative tone"
                    )
                                    
                comment_system = (
                    "You are a social media user with a distinct personality. "
                    "When you comment, you use your specific tone (e.g., sarcastic, enthusiastic, brief, or academic)."
                )
                comment_content = await query_llm(comment_system, comment_user)
                
                if comment_content:
                    # Clean up quotes
                    comment_content = comment_content.replace('"', '').strip()
                    db.add(Comment(user_id=user.id, post_id=post.id, content=comment_content))
                    db.commit()
                    
                    updated_post_c = db.query(Post).filter(Post.id == post.id).first()
                    await manager.broadcast({
                        "type": "update_comments",
                        "post_id": post.id,
                        "count": len(updated_post_c.comments),
                        "content": comment_content,
                        "author": user.username
                    })
        db.close()

async def seed_database_internal(db: Session):
    personas = [
        ("TradFi_Terry", "Loves gold bullion, compound interest, and physical bank branches. Hates crypto volatility and digital wallets."),
        ("Eco_Emma", "Loves reforestation, carbon neutrality, and hiking. Hates the energy consumption of Bitcoin mining and e-waste."),
        ("No-Nonsense_Nancy", "Loves knitting, local farmers markets, and tangible assets. Hates 'imaginary internet money' and tech hype."),
        ("Regulator_Ray", "Loves consumer protection laws, oversight, and financial stability. Hates unregulated exchanges and rug pulls."),
        ("Luddite_Luke", "Loves typewriters, handwritten letters, and cash. Hates the blockchain, smartphones, and anything requiring a Wi-Fi signal."),
        ("TechBro_99", "Loves crypto, AI, and hustling. Hates sleep and laziness."),
        ("DeFi_Daisy", "Loves yield farming, liquidity pools, and decentralization. Hates centralized banks and high wire fees."),
        ("NFT_Nate", "Loves digital art, smart contracts, and the metaverse. Hates right-click-savers and physical galleries."),
        ("Sat_Stacker", "Loves DCA strategies, cold storage, and 'The Bitcoin Standard'. Hates fiat inflation and selling."),
        ("Web3_Wendy", "Loves dApps, DAO governance, and digital identity. Hates Big Tech data harvesting."),
        ("Moonshot_Max", "Loves low-cap gems, 100x leverage, and hype cycles. Hates FUD and 'paper hands'."),
        ("Coder_Caleb", "Loves Solidity, Rust, and open-source protocols. Hates proprietary code and bugs."),
        ("Privacy_Pat", "Loves Monero, VPNs, and encrypted messaging. Hates KYC requirements and surveillance capitalism."),
        ("HODL_Holly", "Loves diamond hands, community memes, and long-term charts. Hates panic sellers and day trading."),
        ("Altcoin_Al", "Loves diverse portfolios, ecosystem airdrops, and new Layer-1s. Hates Bitcoin maximalism."),
        ("Mining_Mitch", "Loves ASIC rigs, cheap electricity, and hash rates. Hates proof-of-stake transitions."),
        ("Alpha_Alice", "Loves whitelist spots, Discord alpha groups, and early-stage VC. Hates missing the mint."),
        ("Blockchain_Ben", "Loves supply chain transparency, immutable ledgers, and logistics. Hates inefficient bureaucracy."),
        ("Validator_Val", "Loves staking rewards, node uptime, and network security. Hates slashing risks and downtime."),
        ("Ethereum_Ethan", "Loves The Merge, gas fee optimizations, and Vitalik Buterin. Hates high Gwei and 'Ethereum killers'.")
    ]

    for uname, pers in personas:
        if not db.query(User).filter(User.username == uname).first():
            parts = uname.split('_')
            fn = parts[0] if len(parts) > 0 else "Bot"
            ln = parts[1] if len(parts) > 1 else "User"

            u = User(
                username=uname, 
                fn=fn,
                ln=ln,
                password=get_password_hash(f"{uname}@2026"), 
                persona=pers, 
                is_autopost_active=False,
                autopost_interval_seconds=3600,
                preview_offset_seconds=300
            )
            db.add(u)
    db.commit()