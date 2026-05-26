import sys
sys.path.insert(0, "/var/www/yexingchen/backend")
from app.database import engine
from sqlalchemy import text
result = engine.execute(text("SELECT * FROM users"))
for row in result:
    print(dict(row))
