#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate test data for v1.1"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models.user import User, Music, Novel, Video, Tool
from app.utils.security import get_password_hash
from datetime import datetime
import random


def create_test_data():
    """Create test data"""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # Find or create admin user
        admin = db.query(User).filter(User.email == "admin@yexingchen.cn").first()
        if not admin:
            print("[INFO] Creating admin account...")
            admin = User(
                email="admin@yexingchen.cn",
                password_hash=get_password_hash("TestPassword123!"),  # 测试环境密码
                role="super_admin",
                status="approved",
                nickname="Admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("[OK] Admin account created")

        # Clean old test data
        db.query(Music).filter(Music.uploader_id == admin.id).delete()
        db.query(Novel).filter(Novel.uploader_id == admin.id).delete()
        db.query(Video).filter(Video.uploader_id == admin.id).delete()
        db.query(Tool).filter(Tool.uploader_id == admin.id).delete()
        db.commit()

        # ========== Music test data ==========
        music_list = [
            {"title": "Bamboo Forest", "file_path": "/uploads/music/bamboo_forest.mp3", "category": "Ambient", "tags": "nature,bamboo,peaceful"},
            {"title": "Starry Walk", "file_path": "/uploads/music/starry_walk.mp3", "category": "Electronic", "tags": "electronic,dreamy,stars"},
            {"title": "Morning Dew", "file_path": "/uploads/music/morning_dew.mp3", "category": "Ambient", "tags": "morning,calm,dew"},
            {"title": "Rainy Night", "file_path": "/uploads/music/rainy_night.mp3", "category": "Ambient", "tags": "rain,night,peaceful"},
            {"title": "Above Clouds", "file_path": "/uploads/music/above_clouds.mp3", "category": "Electronic", "tags": "electronic,cloud,ethereal"},
            {"title": "Mountain Stream", "file_path": "/uploads/music/mountain_stream.mp3", "category": "Ambient", "tags": "nature,water,mountain"},
            {"title": "Twilight Song", "file_path": "/uploads/music/twilight_song.mp3", "category": "Ambient", "tags": "twilight,dusk,melancholy"},
            {"title": "Deep Sea Whisper", "file_path": "/uploads/music/deep_sea_whisper.mp3", "category": "Electronic", "tags": "electronic,deep sea,mysterious"},
        ]

        for music_data in music_list:
            music = Music(
                uploader_id=admin.id,
                original_filename=music_data["title"] + ".mp3",
                file_size=random.randint(3000000, 15000000),
                duration=random.randint(180, 360),
                **music_data
            )
            db.add(music)

        # ========== Novel test data ==========
        novel_list = [
            {"title": "Xian Tu", "author": "Cloud Seeker", "category": "Xianxia", "tags": "xianxia,cultivation", "cover_path": "/uploads/covers/xiantu.jpg"},
            {"title": "City Wanderer", "author": "Urban Drifter", "category": "Urban", "tags": "urban,action,system", "cover_path": "/uploads/covers/city.jpg"},
            {"title": "Star Trek", "author": "Galaxy Walker", "category": "Sci-Fi", "tags": "scifi,space,adventure", "cover_path": "/uploads/covers/space.jpg"},
            {"title": "Ming Dynasty", "author": "Historian", "category": "Historical", "tags": "history,ming,politics", "cover_path": "/uploads/covers/ming.jpg"},
            {"title": "New Martial Era", "author": "Jianghu Junior", "category": "Wuxia", "tags": "wuxia,new style", "cover_path": "/uploads/covers/wuxia.jpg"},
            {"title": "Mystery Files", "author": "Night Scholar", "category": "Mystery", "tags": "mystery,supernatural", "cover_path": "/uploads/covers/mystery.jpg"},
        ]

        for novel_data in novel_list:
            novel = Novel(
                uploader_id=admin.id,
                file_path=f"/uploads/novels/{novel_data['title']}.epub",
                original_filename=novel_data["title"] + ".epub",
                file_size=random.randint(500000, 3000000),
                **novel_data
            )
            db.add(novel)

        # ========== Video test data ==========
        video_list = [
            {"title": "Coding Journey", "cos_url": "https://yexingfiles-1409757734.cos.ap-guangzhou.myqcloud.com/videos/coding.mp4", "category": "Tech", "tags": "coding,humor"},
            {"title": "Quantum Mechanics", "cos_url": "https://yexingfiles-1409757734.cos.ap-guangzhou.myqcloud.com/videos/quantum.mp4", "category": "Education", "tags": "physics,quantum"},
            {"title": "2024 Best Mix", "cos_url": "https://yexingfiles-1409757734.cos.ap-guangzhou.myqcloud.com/videos/mix2024.mp4", "category": "Entertainment", "tags": "mix,highlights"},
            {"title": "Creative Inventions", "cos_url": "https://yexingfiles-1409757734.cos.ap-guangzhou.myqcloud.com/videos/shougong.mp4", "category": "Entertainment", "tags": "diy,invention"},
        ]

        for video_data in video_list:
            video = Video(
                uploader_id=admin.id,
                cover_path=f"/uploads/covers/{video_data['title'][:5]}.jpg",
                original_filename=video_data["title"] + ".mp4",
                file_size=random.randint(10000000, 100000000),
                **video_data
            )
            db.add(video)

        # ========== Tool test data ==========
        tool_list = [
            {"title": "GitHub", "url": "https://github.com", "description": "Code hosting platform", "icon": "github"},
            {"title": "Stack Overflow", "url": "https://stackoverflow.com", "description": "Developer Q&A", "icon": "stack"},
            {"title": "MDN Web Docs", "url": "https://developer.mozilla.org", "description": "Web documentation", "icon": "mdn"},
            {"title": "ChatGPT", "url": "https://chat.openai.com", "description": "AI assistant", "icon": "ai"},
            {"title": "LeetCode", "url": "https://leetcode.com", "description": "Algorithm practice", "icon": "code"},
            {"title": "Notion", "url": "https://notion.so", "description": "Notes & knowledge", "icon": "note"},
            {"title": "Figma", "url": "https://figma.com", "description": "UI design tool", "icon": "design"},
            {"title": "Docker Hub", "url": "https://hub.docker.com", "description": "Container registry", "icon": "docker"},
        ]

        for tool_data in tool_list:
            tool = Tool(uploader_id=admin.id, **tool_data)
            db.add(tool)

        db.commit()
        print("[OK] Test data created successfully!")
        print(f"   - Music: {len(music_list)} tracks")
        print(f"   - Novels: {len(novel_list)} books")
        print(f"   - Videos: {len(video_list)} videos")
        print(f"   - Tools: {len(tool_list)} links")

    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()