
import sys
sys.path.insert(0, '/var/www/yexingchen/backend')
from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check if bg_music exists
    result = conn.execute(text('SELECT setting_value FROM global_settings WHERE setting_key = "bg_music"'))
    row = result.fetchone()
    if row:
        print(f'Current bg_music: {row[0]}')
    else:
        print('No bg_music setting found')
    
    # Check available_bgm
    result2 = conn.execute(text('SELECT setting_value FROM global_settings WHERE setting_key = "available_bgm"'))
    row2 = result2.fetchone()
    if row2:
        print(f'available_bgm: {row2[0]}')
    else:
        print('No available_bgm setting found')
