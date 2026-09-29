"""「美食记忆」端到端取证（打生产 API，全程用临时记录并在结束时删除）。

覆盖 v2.41 新增 / 变更的部分：
  1. GET  /api/life/meals            列表可读，字段齐全
  2. POST /api/life/meals            新场合（feast/memory/travel/home）可建
  3. PATCH /api/life/meals/{id}      改标题 / 改场合 / 改时间 / 改归属
  4. PATCH 换图                       换图后 photo_path 变化，且旧图被删
  5. PATCH 老值兼容                   仍可回写 breakfast/lunch/dinner/snack
  6. PATCH 非法值被拒                 meal_type=xxx → code != 0
  7. DELETE                          删后列表查不到，物理文件也删掉

副作用：生产库临时建 1 条记录，脚本结束前一定删除（try/finally）。
用法：python scripts/verify_life_meals.py
"""
import io
import struct
import sys
import zlib

import requests

BASE = "https://yexingchen.cn"


def _load_creds():
    """凭据不写进仓库（本仓库为公开仓库，见 docs/ISSUES.md V2441-005）。

    优先环境变量 YX_EMAIL / YX_PASSWORD；否则读 <repo>/../.secrets/local.env。
    """
    import os
    import re
    from pathlib import Path

    email = os.environ.get("YX_EMAIL")
    pw = os.environ.get("YX_PASSWORD")
    if not (email and pw):
        path = Path(__file__).resolve().parents[2] / ".secrets" / "local.env"
        try:
            seg = path.read_text(encoding="utf-8", errors="replace").split("#项目网站信息")[-1]
            email = email or (re.search(r"账号：\s*(\S+)", seg) or [None, None])[1]
            pw = pw or (re.search(r"密码：\s*(\S+)", seg) or [None, None])[1]
        except OSError:
            pass
    if not (email and pw):
        raise SystemExit("缺少凭据：请设置 YX_EMAIL / YX_PASSWORD，或提供 ../.secrets/local.env")
    return email, pw


EMAIL, PW = _load_creds()

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def login():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": EMAIL, "password": PW}, timeout=30).json()
    if r.get("code") != 0:
        raise SystemExit(f"login failed: {r}")
    return r["data"]["token"], r["data"]["user"]["id"]


def png_bytes(rgb):
    """生成一张 8x8 纯色 PNG，避免依赖 Pillow。"""
    w = h = 8
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


tok, uid = login()
H = {"Authorization": f"Bearer {tok}"}


def api_get(path, params=None):
    return requests.get(f"{BASE}{path}", params=params or {}, headers=H, timeout=60).json()


def api_post(path, data=None, files=None):
    return requests.post(f"{BASE}{path}", data=data or {}, files=files or {}, headers=H, timeout=120).json()


def api_patch(path, data=None, files=None):
    return requests.patch(f"{BASE}{path}", data=data or {}, files=files or {}, headers=H, timeout=120).json()


def api_delete(path):
    return requests.delete(f"{BASE}{path}", headers=H, timeout=60).json()


print("== 0. 准备：登录 + 家人档案 ==")
members = api_get("/api/life/members").get("data", {}).get("list", [])
check("家人列表可读", len(members) > 0, f"{len(members)} 位")
me = next((m for m in members if m.get("user_id") == uid), members[0] if members else None)
other = next((m for m in members if m.get("id") != me["id"]), None) if me else None
check("找到本人成员档案", bool(me), f"member_id={me and me['id']}")

meal_id = None
try:
    print("\n== 1. 新建（新场合） ==")
    r = api_post("/api/life/meals", data={
        "member_id": me["id"], "meal_type": "feast",
        "note": "探针·美食记忆·待删", "taken_at": "2026-09-29T12:30:00",
    }, files={"photo": ("probe_a.png", png_bytes((200, 120, 60)), "image/png")})
    meal = r.get("data") or {}
    meal_id = meal.get("id")
    check("POST 大餐成功", r.get("code") == 0 and meal_id, f"id={meal_id} {r.get('msg')}")
    check("新场合值原样存回", meal.get("meal_type") == "feast", f"meal_type={meal.get('meal_type')}")
    old_photo = meal.get("photo_path", "")

    print("\n== 2. 列表可读到刚建的记录 ==")
    lst = api_get("/api/life/meals", {"limit": 100}).get("data", {}).get("list", [])
    hit = next((m for m in lst if m.get("id") == meal_id), None)
    check("列表命中临时记录", bool(hit), f"共 {len(lst)} 条")
    check("列表带成员名（非空）", bool(hit and hit.get("member_name")), f"member_name={hit and hit.get('member_name')}")

    print("\n== 3. 编辑：改标题 / 场合 / 时间 / 归属 ==")
    data = {"meal_type": "memory", "note": "探针·已改名", "taken_at": "2026-09-28T19:05:00"}
    if other:
        data["member_id"] = other["id"]
    r = api_patch(f"/api/life/meals/{meal_id}", data=data)
    up = r.get("data") or {}
    check("PATCH 成功", r.get("code") == 0, f"msg={r.get('msg')}")
    check("场合已改为 memory", up.get("meal_type") == "memory", f"meal_type={up.get('meal_type')}")
    check("标题已改", up.get("note") == "探针·已改名", f"note={up.get('note')}")
    check("时间已改", (up.get("taken_at") or "").startswith("2026-09-28"), f"taken_at={up.get('taken_at')}")
    if other:
        check("归属已改", up.get("member_id") == other["id"], f"member_id={up.get('member_id')}")
    check("未换图时 photo_path 不变", up.get("photo_path") == old_photo, f"{old_photo} → {up.get('photo_path')}")

    print("\n== 4. 换图：路径变化 + 旧图被删 ==")
    r = api_patch(f"/api/life/meals/{meal_id}",
                  data={"note": "探针·已换图"},
                  files={"photo": ("probe_b.png", png_bytes((60, 120, 200)), "image/png")})
    up2 = r.get("data") or {}
    new_photo = up2.get("photo_path", "")
    check("PATCH 换图成功", r.get("code") == 0 and new_photo, f"msg={r.get('msg')}")
    check("photo_path 已变", new_photo and new_photo != old_photo, f"{old_photo} → {new_photo}")
    old_url = f"{BASE}/uploads{old_photo}" if old_photo.startswith("/") else f"{BASE}/uploads/{old_photo}"
    check("旧图已从磁盘删除（404）", requests.get(old_url, timeout=30).status_code == 404, old_url)
    new_url = f"{BASE}/uploads{new_photo}" if new_photo.startswith("/") else f"{BASE}/uploads/{new_photo}"
    check("新图可访问（200）", requests.get(new_url, timeout=30).status_code == 200, new_url)

    print("\n== 5. 老值兼容（v2.41 之前的三餐值仍可回写） ==")
    r = api_patch(f"/api/life/meals/{meal_id}", data={"meal_type": "dinner"})
    check("回写 dinner 不被拒", r.get("code") == 0 and (r.get("data") or {}).get("meal_type") == "dinner",
          f"meal_type={(r.get('data') or {}).get('meal_type')} msg={r.get('msg')}")
    r = api_patch(f"/api/life/meals/{meal_id}", data={"meal_type": "feast"})

    print("\n== 6. 非法场合被拒 ==")
    r = api_patch(f"/api/life/meals/{meal_id}", data={"meal_type": "brunch"})
    check("meal_type=brunch 被拒", r.get("code") != 0, f"code={r.get('code')} msg={r.get('msg')}")

    print("\n== 7. 删除 ==")
    r = api_delete(f"/api/life/meals/{meal_id}")
    check("DELETE 成功", r.get("code") == 0, f"msg={r.get('msg')}")
    lst2 = api_get("/api/life/meals", {"limit": 100}).get("data", {}).get("list", [])
    check("列表已查不到", not any(m.get("id") == meal_id for m in lst2), f"共 {len(lst2)} 条")
    check("删除后图片也 404", requests.get(new_url, timeout=30).status_code == 404, new_url)
    meal_id = None
finally:
    if meal_id:
        print("\n[cleanup] 兜底删除临时记录", meal_id)
        try:
            api_delete(f"/api/life/meals/{meal_id}")
        except Exception as e:  # noqa: BLE001
            print("  cleanup failed:", e)

print("\n== 汇总 ==")
failed = [n for n, ok, _ in results if not ok]
print(f"  {len(results) - len(failed)}/{len(results)} 通过")
if failed:
    for n in failed:
        print("  FAIL:", n)
    sys.exit(1)