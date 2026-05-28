import sqlite3

conn = sqlite3.connect('/var/www/yexingchen/backend/yexingchen.db')
cursor = conn.cursor()

# Update bg_music to mp3
cursor.execute("UPDATE global_settings SET value = '/uploads/bgm/garden_music.mp3' WHERE \"key\" = 'bg_music'")
print('Updated bg_music to mp3')

# Update available_bgm to use mp3
available_bgm = '[{"id": "garden_music", "name": "garden_music", "file": "/uploads/bgm/garden_music.mp3"}, {"id": "pluck_lute", "name": "pluck_lute", "file": "/uploads/bgm/pluck_lute.mp3"}, {"id": "bamboo_flute", "name": "bamboo_flute", "file": "/uploads/bgm/bamboo_flute.mp3"}]'
cursor.execute("UPDATE global_settings SET value = ? WHERE \"key\" = 'available_bgm'", (available_bgm,))
print('Updated available_bgm to mp3')

conn.commit()
conn.close()
print('Done!')