"""从干净 1024 图标缩出 Android 各密度 ic_launcher PNG（配合 build_webview_apk.py 重打 APK）"""
import os
from PIL import Image

SRC = os.path.join(os.path.dirname(__file__), "app-icon-1024.png")
OUT = os.path.dirname(__file__)
SIZES = [48, 72, 96, 144, 192]

img = Image.open(SRC).convert("RGBA")
for n in SIZES:
    (img.resize((n, n), Image.LANCZOS)
        .save(os.path.join(OUT, "ic_launcher_%d.png" % n)))
    print("OK", n)