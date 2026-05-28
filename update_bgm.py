import sqlite3

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

# Update bg_music to mp3
cursor.execute("UPDATE global_settings SET value = '/uploads/bgm/garden_music.mp3' WHERE \"key\" = 'bg_music'")
print('Updated bg_music')

# Update available_bgm to use mp3
new_available_bgm = '[{"id": "garden_music", "name": "🎵 庭院音乐", "file": "/uploads/bgm/garden_music.mp3"}, {"id": "pluck_lute", "name": "🎸 古琴弹奏（青花瓷风）", "file": "/uploads/bgm/pluck_lute.mp3"}, {"id": "bamboo_flute", "name": "🎶 笛子独奏（兰亭序风）", "file": "/uploads/bgm/bamboo_flute.mp3"}]'
cursor.execute("UPDATE global_settings SET value = ? WHERE \"key\" = 'available_bgm'", (new_available_bgm,))
print('Updated available_bgm')

conn.commit()
conn.close()
print('Done!')