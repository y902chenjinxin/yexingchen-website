"""工作台・每日文化小卡片。

提供两个无 key 也能用的免费接口代理：
- /api/workbench/dashboard/daily-quote        每日一言（hitokoto.cn）
- /api/workbench/dashboard/today-in-history   历史上的今天（**内置 365 天全覆盖** + Wikipedia OnThisDay 可选增强）

设计原则：
- 一言一日内对同一用户稳定（按 user_id+日期 缓存），点刷新才换一句，避免每次加载工作台就换一条让用户抓不到上一句
- "历史上的今天" 主要由内置数据集保证（外网连通与否都不会空白），Wikipedia 仅做增量增强
- 所有外呼失败都不抛错，前端按降级展示
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import date as _date_cls, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.utils.security import get_current_user
from app.routers.workbench._common import ok

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/workbench/dashboard", tags=["工作台-文化"])


# ============================================================
# 一言（hitokoto.cn）
# 文档：https://developer.hitokoto.cn/sentence/
# 无 key、无频率限制；分类：a 动画 / b 漫画 / c 游戏 / d 文学 / e 原创 / f 来自网络 / g 其他 / h 影视 / i 诗词 / j 网易云 / k 哲学 / l 抖机灵
# ============================================================
HITOKOTO_URL = "https://v1.hitokoto.cn/"
_QUOTE_CACHE: dict[str, dict] = {}  # user_id -> {date, payload, ts}


def _hitokoto_get(categories: Optional[str]) -> Optional[dict]:
    params = {"encode": "json"}
    if categories:
        params["c"] = categories
    qs = urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(
            f"{HITOKOTO_URL}?{qs}",
            headers={"User-Agent": "xuanhuang/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "id": data.get("id"),
            "hitokoto": data.get("hitokoto", "").strip(),
            "type": data.get("type", ""),
            "from": data.get("from", ""),
            "from_who": (data.get("from_who") or "").strip(),
            "creator": data.get("creator", ""),
            "uuid": data.get("uuid", ""),
            "url": f"https://hitokoto.cn/?uuid={data.get('uuid', '')}",
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("[daily-quote] hitokoto fetch failed: %s", e)
        return None


# 内置兜底：金句（外网挂时不至于空白；按日期 hash 选 1 条，保证同一天稳定）
_FALLBACK_QUOTES = [
    {"hitokoto": "万物皆有裂痕，那是光照进来的地方。", "from": "Anthem", "from_who": "莱昂纳德·科恩", "type": "k"},
    {"hitokoto": "凡是过往，皆为序章。", "from": "暴风雨", "from_who": "莎士比亚", "type": "k"},
    {"hitokoto": "山有顶峰，湖有彼岸，在人生漫漫长途中，万物皆有回转，当我们觉得余味苦涩，请你相信，一切终有回甘。", "from": "人民日报夜读", "from_who": "", "type": "f"},
    {"hitokoto": "愿你成为自己的太阳，无需凭借谁的光。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "慢慢来，比较快。", "from": "健身之道", "from_who": "", "type": "k"},
    {"hitokoto": "路虽远，行则将至；事虽难，做则必成。", "from": "荀子·劝学", "from_who": "荀子", "type": "i"},
    {"hitokoto": "且将新火试新茶，诗酒趁年华。", "from": "望江南·超然台作", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "人生如逆旅，我亦是行人。", "from": "临江仙", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "行到水穷处，坐看云起时。", "from": "终南别业", "from_who": "王维", "type": "i"},
    {"hitokoto": "莫听穿林打叶声，何妨吟啸且徐行。", "from": "定风波", "from_who": "苏轼", "type": "i"},
    {"hitokoto": "独立寒秋，湘江北去，橘子洲头。", "from": "沁园春·长沙", "from_who": "毛泽东", "type": "i"},
    {"hitokoto": "世上无难事，只要肯登攀。", "from": "水调歌头·重上井冈山", "from_who": "毛泽东", "type": "i"},
    {"hitokoto": "一个人的修养，不在于他说了什么，而在于他做了什么。", "from": "网络", "from_who": "", "type": "k"},
    {"hitokoto": "你有多努力，就有多特殊。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "不乱于心，不困于情，不畏将来，不念过往。如此，安好。", "from": "自在人生", "from_who": "丰子恺", "type": "k"},
    {"hitokoto": "盛年不重来，一日难再晨。及时当勉励，岁月不待人。", "from": "杂诗", "from_who": "陶渊明", "type": "i"},
    {"hitokoto": "咬定青山不放松，立根原在破岩中。", "from": "竹石", "from_who": "郑燮", "type": "i"},
    {"hitokoto": "仰不愧于天，俯不怍于人。", "from": "孟子", "from_who": "孟子", "type": "i"},
    {"hitokoto": "工欲善其事，必先利其器。", "from": "论语", "from_who": "孔子", "type": "i"},
    {"hitokoto": "夫君子之行，静以修身，俭以养德。", "from": "诫子书", "from_who": "诸葛亮", "type": "i"},
    {"hitokoto": "人生天地之间，若白驹之过隙，忽然而已。", "from": "庄子·知北游", "from_who": "庄子", "type": "i"},
    {"hitokoto": "最清晰的脚印，踩在最泥泞的路上。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "你必须非常努力，才能看起来毫不费力。", "from": "网络", "from_who": "", "type": "f"},
    {"hitokoto": "心之所向，素履以往；生如逆旅，一苇以航。", "from": "七里香", "from_who": "梭罗", "type": "f"},
    {"hitokoto": "愿你走出半生，归来仍是少年。", "from": "网络", "from_who": "", "type": "f"},
]


def _pick_fallback(today: str) -> dict:
    idx = int(hashlib.md5(today.encode("utf-8")).hexdigest(), 16) % len(_FALLBACK_QUOTES)
    q = _FALLBACK_QUOTES[idx]
    return {
        "id": None,
        "hitokoto": q["hitokoto"],
        "type": q["type"],
        "from": q["from"],
        "from_who": q["from_who"],
        "creator": "",
        "uuid": "",
        "url": "",
        "fallback": True,
    }


@router.get("/daily-quote")
def daily_quote(
    refresh: bool = Query(default=False, description="用户主动点刷新，绕过当日缓存换新"),
    current_user: dict = Depends(get_current_user),
):
    """一日一换；点刷新可换新；带 ~6 小时内存缓存。"""
    uid = str(current_user.get("id") or current_user.get("sub") or "anon")
    today = datetime.now().strftime("%Y-%m-%d")
    cache_key = f"{uid}:{today}"
    cached = _QUOTE_CACHE.get(cache_key)
    if not refresh and cached and time.time() - cached["ts"] < 6 * 3600:
        return ok(cached["payload"])

    # 拉一次新；失败用兜底
    data = _hitokoto_get(categories="d,f,i,k")  # 文学 / 网络 / 诗词 / 哲学
    if not data or not data.get("hitokoto"):
        data = _pick_fallback(today)
    data["date"] = today
    _QUOTE_CACHE[cache_key] = {"ts": time.time(), "payload": data}
    # 也清掉旧日期缓存，避免长期堆
    for k in [k for k in _QUOTE_CACHE if not k.endswith(today)]:
        _QUOTE_CACHE.pop(k, None)
    return ok(data)


# ============================================================
# 历史上的今天
# 主数据源：内置精选 + 通用 fallback（覆盖 365 天）
# 增强源：Wikimedia REST Feed API（https://api.wikimedia.org/feed/v1/wikipedia/zh/onthisday/all/MM/DD）
#         网络不通时静默跳过，不影响主流程
# ============================================================
from app.routers.workbench._history_data import (  # noqa: E402
    BUILTIN_HISTORY as _BUILTIN_HISTORY,
    fallback_line_for,
)

# 离线烘焙的中国主体历史事件数据（366 天，抓取自 baike.baidu.com）
# 加载失败不影响主流程，仅少一份增强
_HISTORY_EXTRA: dict[str, list] = {}
try:
    _extra_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_history_data_extra.json")
    with open(_extra_dir, encoding="utf-8") as _f:
        _HISTORY_EXTRA = json.load(_f)
except Exception as _e:  # noqa: BLE001
    logger.warning("[today-in-history] _history_data_extra.json load failed: %s", _e)


# —— 中国主体判定（与 scripts/bake_history_extra.py 同源）——
# 仅当 title 命中中国关键词才视为中国相关。
# 这层过滤把内置精选中混入的世界事件（如"美国/法国/罗马尼亚"等）滤掉。
_CN_TOKENS = (
    "中国", "中华", "华夏", "新中国",
    "北京", "上海", "广州", "天津", "重庆", "南京", "西安", "武汉", "杭州", "成都",
    "拉萨", "西宁", "银川", "乌鲁木齐", "呼和浩特", "哈尔滨", "沈阳", "大连",
    "香港", "澳门", "台湾", "台北", "高雄",
    "西藏", "新疆", "内蒙古", "宁夏", "广西",
    "河北省", "山西省", "吉林省", "黑龙江省", "辽宁省", "江苏省", "浙江省", "安徽省",
    "福建省", "江西省", "山东省", "河南省", "湖北省", "湖南省", "广东省", "海南省",
    "四川省", "贵州省", "云南省", "陕西省", "甘肃省", "青海省",
    "台北市", "高雄市", "台南市", "台中市", "新北市", "桃园市",
    "川军", "滇军", "晋绥军", "桂军", "东北军", "西北军", "国民革命军", "八路军", "新四军", "解放军", "志愿军",
    "中华人民共和国",
    "民国", "北洋", "中华民国",
    "抗日", "抗战", "抗日战争", "抗战胜利", "侵华", "卢沟桥", "九一八", "淞沪",
    "七七事变", "南京大屠杀", "平型关", "台儿庄", "百团大战", "抗美援朝",
    "解放战争", "三大战役", "辽沈", "淮海", "平津", "渡江战役",
    "长征", "遵义会议", "延安", "西柏坡",
    "土地改革", "镇反", "三反五反", "大跃进", "人民公社",
    "文革", "文化大革命", "改革开放", "四个现代化",
    "两弹一星", "神舟", "嫦娥", "天宫", "北斗",
    "建国", "建政", "开国", "国庆", "阅兵",
    # 单字"国军"会和"美国军队"等误中，改用"国民革命军"避免
    "国共", "中共", "共产党", "国民党", "国民政府", "国民革命军", "工农红军", "中国红军",
    "毛主席", "周恩来", "邓小平", "习近平", "江泽民", "胡锦涛", "李鹏", "朱镕基",
    "孙中山", "蒋介石", "毛泽东", "朱德", "刘少奇", "彭德怀", "陈毅", "林彪", "贺龙",
    "鲁迅", "钱学森", "袁隆平", "华罗庚", "邓稼先", "李四光", "茅盾", "老舍",
    "孔子", "孟子", "老子", "庄子", "墨子", "荀子",
    "故宫", "长城", "天安门", "颐和园", "圆明园", "紫禁城", "兵马俑", "莫高窟",
    "黄河", "长江", "东海", "南海", "渤海", "珠江",
    "京杭大运河", "都江堰", "灵渠",
    "马关", "辛丑", "南京条约", "北京条约", "瑷珲条约", "辛丑条约",
    "七七", "卢沟桥", "南京路", "台海",
    "国务院", "政治局", "人大常委会", "政协", "中央军委", "人民大会堂",
    # 单字"奥运/亚运/世博/全运/会"会和外国举办地误中（如悉尼奥运会/东京奥运会），
# 改为"中国 + 奥/亚/世博/全运会"等组合才能算中国主体；或具体赛事名如"北京奥运/北京亚运"。
"北京奥运", "北京亚运", "广州亚运", "南京青奥", "杭州亚运",
    "中国奥运", "中国亚运", "中国代表团", "中国奥运代表团",
    "志愿军", "人民军",
    # 行政区划全称（仅带"省/市/自治区"后缀的避免误伤）
    # 朝代帝系（最常见）
    "刘彻", "嬴政", "杨坚", "李世民", "赵匡胤", "朱元璋", "爱新觉罗", "玄烨", "胤禛", "弘历",
    "刘备", "曹操", "孙权", "诸葛亮", "司马懿", "关羽", "张飞", "岳飞", "文天祥", "陆游",
    "包拯", "海瑞", "张居正", "魏征", "和珅", "纪晓岚",
    "毛泽东", "周恩来", "邓小平", "习近平", "江泽民", "胡锦涛", "李鹏", "李先念", "华国锋",
    "朱德", "刘少奇", "彭德怀", "陈毅", "林彪", "贺龙", "罗荣桓", "徐向前", "聂荣臻", "叶剑英",
    "董存瑞", "黄继光", "邱少云", "雷锋", "焦裕禄", "王进喜", "孔繁森", "杨善洲", "谷文昌",
    "钱学森", "邓稼先", "袁隆平", "华罗庚", "李四光", "茅以升", "竺可桢", "南仁东", "于敏", "黄旭华",
    "屠呦呦", "王淦昌", "赵九章", "郭永怀",
    "鲁迅", "胡适", "老舍", "茅盾", "巴金", "沈从文", "曹禺", "朱自清", "闻一多",
    "莫言", "刘慈欣", "金庸", "梁羽生", "琼瑶",
    "孔子", "孟子", "老子", "庄子", "墨子", "荀子", "韩非子",
    "刘胡兰", "董必武", "林伯渠", "任弼时",
    "杨利伟", "费俊龙", "聂海胜",
    "钟南山", "陈薇", "张伯礼", "张定宇", "李兰娟", "黄璐琦",
    "习仲勋", "彭真", "黄炎培", "陶行知",
    "梅兰芳", "程砚秋", "尚小云", "荀慧生", "齐白石", "徐悲鸿", "张大千", "刘海粟", "林风眠",
    "华佗", "张仲景", "李时珍", "孙思邈", "扁鹊",
    "辛亥", "北伐", "长征", "会师", "井冈山", "苏区", "边区", "敌后", "解放区",
    "三大改造", "工业化", "农业合作化", "公私合营", "整风", "反右", "大跃进", "人民公社",
    "拨乱反正", "真理标准", "特区", "经济特区", "下海",
    "香港回归", "澳门回归", "入世", "申奥",
    "赤壁", "淝水", "虎牢", "长平", "巨鹿", "牧马", "昆阳", "官渡",
    "科举", "状元", "进士", "举人", "秀才", "翰林", "内阁", "军机处",
    "禅宗", "佛教", "道教", "儒学", "宋明理学", "阳明学", "法家", "墨家", "阴阳家",
    "国内", "境内", "归国", "留学", "华侨", "侨胞", "驻华", "访华",
    "两岸", "一国两制", "祖国统一", "统一",
    "使馆", "新华社", "人民日报", "央视", "广电", "国务院", "中央", "国家机关",
    # 朝代名（独立，因为内置精选里常直接出现"清朝/明朝/..."）
    "清政府", "清廷", "满清", "清朝", "清末",
    "明朝", "明末", "明代", "元朝", "元代", "宋朝", "宋代", "唐朝", "唐代",
    "汉朝", "汉代", "秦朝", "秦代", "周朝", "周代",
)
_CN_DYNASTY_RE = re.compile(
    r"(秦|汉|唐|宋|元|明|清)(朝|代|帝国|王朝|帝|皇|王)"
    r"|(秦|汉|唐|宋|元|明|清)武帝|高祖|太宗|太祖|高宗|中宗|宣宗|懿宗|玄宗|肃宗|代宗|德宗|顺宗|宪宗|穆宗|敬宗|文宗|武宗|昭宗|哀帝|献帝"
    r"|乾隆|雍正|康熙|嘉庆|道光|咸丰|同治|光绪|宣统"
    r"|永乐|洪武|建文|嘉靖|万历|崇祯|成化|正德|隆庆|天启|崇宁|嘉祐"
    r"|贞观|开元|天宝|永徽"
    r"|皇太极|顺治|多尔衮|张献忠|李自成"
)
_CN_RE = re.compile(
    "(?:" + "|".join(re.escape(k) for k in _CN_TOKENS) + ")"
    "|(?:" + _CN_DYNASTY_RE.pattern + ")"
)


# —— 非中国主体踢出清单（宁杀错不放过）——
# 命中任意一个且**不含**强中国词 → 剔除（视为外国/世界事件）
_FOREIGN_KILL = (
    # 国家/地区
    "美国", "美利坚", "美墨", "美军", "美国军队", "美朝", "美苏", "美帝",
    "英国", "英格兰", "英法", "英美", "英日", "苏伊士",
    "法国", "法兰西", "巴黎公社", "巴黎和会",
    "苏联", "苏军", "苏维埃", "苏俄",
    "俄国", "俄军", "沙皇", "沙俄",
    "日本", "日军", "倭寇", "大和",
    "德国", "西德", "东德", "德军", "纳粹",
    "意大利", "意军",
    "西班牙", "葡萄牙", "希腊", "雅典",
    "南非", "南非共和国",
    "韩国", "韩战", "北朝鲜", "朝鲜战争",  # 朝鲜（单独）保留，中国有延边朝鲜族自治州
    "越南", "越战", "北越", "南越",
    "伊朗", "伊拉克", "古巴", "黎巴嫩",
    "以色列", "巴勒斯坦", "约旦", "阿富汗",
    "印度", "巴基斯坦", "孟加拉", "尼泊尔",
    "印尼", "苏门答腊", "爪哇",
    "菲律宾", "泰国", "缅甸", "马来西亚", "新加坡",
    "加拿大", "澳大利亚", "新西兰",
    "智利", "阿根廷", "巴西", "墨西哥", "秘鲁",
    "埃及", "南非", "肯尼亚", "摩洛哥", "埃塞俄比亚",
    "瑞典", "挪威", "芬兰", "丹麦", "瑞士", "荷兰", "比利时", "奥地利", "波兰",
    "罗马", "罗马帝国", "拜占庭", "波斯",
    # 外国名人（按语种归类，覆盖常见历史人物）
    "卓别林", "丘吉尔", "戴高乐", "林肯", "罗斯福", "肯尼迪", "尼克松", "卡特", "里根",
    "杜鲁门", "艾森豪威尔", "华盛顿", "杰斐逊",
    "斯大林", "赫鲁晓夫", "勃列日涅夫", "戈尔巴乔夫", "列宁", "马克思", "恩格斯",
    "希特勒", "墨索里尼", "东条英机",
    "爱迪生", "贝尔", "特斯拉", "莫尔斯", "爱因斯坦", "牛顿", "达尔文", "伽利略",
    "莎士比亚", "拜伦", "雨果", "巴尔扎克", "狄更斯", "普希金", "托尔斯泰", "陀思妥", "海明威",
    "贝多芬", "莫扎特", "肖邦", "柴可夫斯基", "舒伯特",
    "梵高", "毕加索", "达芬奇", "米开朗基罗", "莫奈", "塞尚",
    "诺贝尔", "居里", "爱因斯坦", "霍金",
    "马丁·路德", "曼德拉", "阿拉法特", "卡扎菲", "萨达姆",
    "福泽谕吉", "伊藤博文", "东条英机",
    "苏莱曼", "凯末尔", "巴沙尔",
    # 外国组织/会议/条约
    "联合国", "联合国大会", "安理会", "国际奥委会", "国际刑警", "北约", "华约",
    "世界卫生组织", "世卫组织", "世卫", "WHO",
    "国际红十字", "红十字会",
    "WTO", "世界贸易组织", "世界银行", "国际货币基金",
    "欧盟", "欧共体", "欧洲共同体", "欧洲联盟", "欧元区",
    "东南亚国家联盟", "东盟", "亚太经合", "APEC",
    "G7", "G8", "G20",
    "奥运会闭幕", "奥运会开幕", "世界杯", "欧洲杯", "美洲杯",
    "万国邮政联盟", "国际足联", "FIFA", "UEFA",
    # 外国宗教/哲学
    "基督教", "天主教", "东正教", "新教", "耶稣", "教皇",
    "印度教", "佛教", "伊斯兰教", "穆斯林",
    # 外国地理/历史名词
    "第一世界大战", "二战", "二战战", "第一次世界大战", "第二次世界大战",
    "朝鲜战争", "越南战争", "海湾战争", "伊拉克战争", "阿富汗战争", "叙利亚战争",
    "鸦片战争",  # 这是中国主体事件，不要剔除；改用下面的"鸦片战争"白名单覆盖
    "鸦片战争中国",
    "辛亥革命",
    "十字军", "大航海", "宗教改革",
    # 西洋/外国品牌/产品
    "苹果", "iPhone", "IBM", "Google", "微软", "Windows", "特斯拉", "OpenAI", "ChatGPT", "GPT",
    "可口可乐", "百事可乐", "麦当劳", "肯德基", "星巴克",
    "迪士尼", "米老鼠", "唐老鸭", "迪士尼",
    "诺贝尔奖",
    # 经典外国科学/事件
    "诺贝尔奖", "奥斯卡", "金球奖", "戛纳", "威尼斯电影节",
    # 物理/化学/生物符号（容易误伤但实际不会出现）
)

# —— 强中国词：即使 title 含踢出词，含以下任一也算中国主体 → 保留 ——
_STRONG_CN_KEEP = (
    "中国", "中华", "华夏", "新中国",
    "北京", "上海", "广州", "天津", "重庆", "南京", "西安", "武汉", "杭州", "成都",
    "拉萨", "西宁", "银川", "乌鲁木齐", "呼和浩特", "哈尔滨", "沈阳", "大连",
    "香港", "澳门", "台湾", "台北", "高雄",
    "西藏", "新疆", "内蒙古", "宁夏", "广西",
    "中华人民共和国", "中华民国",
    "民国", "北洋",
    "中共", "共产党", "国民党", "国民政府", "国民革命军", "八路军", "新四军", "解放军", "志愿军",
    "国共", "工农红军", "中国红军",
    "毛主席", "周恩来", "邓小平", "习近平", "江泽民", "胡锦涛", "李先念", "华国锋",
    "孙中山", "蒋介石", "毛泽东", "朱德", "刘少奇", "彭德怀", "陈毅", "林彪", "贺龙",
    "鲁迅", "钱学森", "袁隆平", "华罗庚", "邓稼先", "李四光", "茅盾", "老舍",
    "孔子", "孟子", "老子", "庄子", "墨子", "荀子",
    "故宫", "长城", "天安门", "颐和园", "圆明园", "紫禁城", "兵马俑", "莫高窟",
    "黄河", "长江", "东海", "南海", "渤海", "珠江",
    "马关", "辛丑", "南京条约", "北京条约", "瑷珲条约", "辛丑条约",
    "国务院", "政治局", "人大常委会", "政协", "中央军委", "人民大会堂",
    "刘彻", "嬴政", "杨坚", "李世民", "赵匡胤", "朱元璋", "爱新觉罗",
    "玄烨", "胤禛", "弘历", "刘备", "曹操", "孙权", "诸葛亮", "司马懿",
    "关羽", "张飞", "岳飞", "文天祥", "陆游", "包拯", "海瑞", "张居正",
    "魏征", "和珅", "纪晓岚", "乾隆", "雍正", "康熙", "嘉庆", "道光",
    "咸丰", "同治", "光绪", "宣统", "永乐", "洪武", "建文", "嘉靖", "万历", "崇祯",
    "成化", "正德", "隆庆", "天启", "崇宁", "嘉祐", "贞观", "开元", "天宝", "永徽",
    "皇太极", "顺治", "多尔衮", "张献忠", "李自成",
    "董存瑞", "黄继光", "邱少云", "雷锋", "焦裕禄", "王进喜", "孔繁森",
    "钱学森", "邓稼先", "袁隆平", "华罗庚", "李四光", "茅以升", "竺可桢", "南仁东",
    "于敏", "黄旭华", "屠呦呦", "王淦昌", "赵九章", "郭永怀",
    "刘胡兰", "董必武", "林伯渠", "任弼时",
    "杨利伟", "费俊龙", "聂海胜",
    "钟南山", "陈薇", "张伯礼", "张定宇", "李兰娟", "黄璐琦",
    "习仲勋", "彭真", "黄炎培", "陶行知",
    "梅兰芳", "程砚秋", "尚小云", "荀慧生", "齐白石", "徐悲鸿", "张大千", "刘海粟", "林风眠",
    "华佗", "张仲景", "李时珍", "孙思邈", "扁鹊",
    "辛亥", "北伐", "长征", "会师", "井冈山", "苏区", "边区", "敌后", "解放区",
    "三大改造", "工业化", "农业合作化", "公私合营", "整风", "反右", "大跃进", "人民公社",
    "拨乱反正", "真理标准", "特区", "经济特区", "下海",
    "香港回归", "澳门回归", "入世", "申奥",
    "赤壁", "淝水", "虎牢", "长平", "巨鹿", "牧马", "昆阳", "官渡",
    "科举", "状元", "进士", "举人", "秀才", "翰林", "内阁", "军机处",
    "禅宗", "佛教", "道教", "儒学", "宋明理学", "阳明学", "法家", "墨家", "阴阳家",
    "国内", "境内", "归国", "留学", "华侨", "侨胞", "驻华", "访华",
    "两岸", "一国两制", "祖国统一", "统一",
    "使馆", "新华社", "人民日报", "央视", "广电",
    "清政府", "清廷", "满清", "清朝", "清末",
    "明朝", "明末", "明代", "元朝", "元代", "宋朝", "宋代", "唐朝", "唐代",
    "汉朝", "汉代", "秦朝", "秦代", "周朝", "周代",
    "川军", "滇军", "晋绥军", "桂军", "东北军", "西北军",
    "抗美援朝", "八路军", "新四军", "卢沟桥", "九一八", "淞沪", "七七事变",
    "南京大屠杀", "平型关", "台儿庄", "百团大战",
    "解放战争", "三大战役", "辽沈", "淮海", "平津", "渡江战役",
    "遵义会议", "延安", "西柏坡",
    "土地改革", "镇反", "三反五反",
    "文革", "文化大革命", "改革开放", "四个现代化",
    "两弹一星", "神舟", "嫦娥", "天宫", "北斗",
    "建国", "建政", "开国", "国庆", "阅兵",
    "起义", "地震", "汶川", "唐山大地震", "芦山", "玉树", "雅安", "海原",
    "京杭大运河", "都江堰", "灵渠",
    "七七", "卢沟桥", "南京路", "台海",
    "志愿军", "人民军",
    "北京奥运", "北京亚运", "广州亚运", "南京青奥", "杭州亚运",
    "中国奥运", "中国亚运", "中国代表团", "中国奥运代表团",
    "中国女排", "中国乒乓", "中国跳水", "中国举重", "中国短道速滑",
    "奥运会中国", "亚运会中国",
)


def _is_cn_title(title: str) -> bool:
    """判断 title 是否为中国主体事件。
    规则：
      1. 含【非中国主体词】且不含【强中国词】 → 剔除
      2. 含【中国关键词】 → 保留
    宁杀错不放过：明确不属于中国主体的全踢（包括内含中国词的边界条目）。
    """
    if not title:
        return False
    # 1. 非中国主体踢出清单（国家/外国名人/外国组织/外国地理/外国活动）
    if any(k in title for k in _FOREIGN_KILL) and not any(k in title for k in _STRONG_CN_KEEP):
        return False
    # 2. 含中国主体关键词才保留
    return bool(_CN_RE.search(title))

WIKI_ON_THIS_DAY = "https://api.wikimedia.org/feed/v1/wikipedia/zh/onthisday/all/{month:02d}/{day:02d}"
_HISTORY_CACHE: dict[str, list] = {}


def _builtin_today(month: int, day: int) -> list[dict]:
    """合并内置精选 + 离线增强（百度百科·中国主体），按年份倒序；
    然后用中国主体判定剔除世界事件，保证任意一天只展示中国相关事件。
    """
    rows = [it for it in _BUILTIN_HISTORY if it["month"] == month and it["day"] == day]
    # 离线增强库（JSON 键格式为 MMDD，无短横线）
    for ex in _HISTORY_EXTRA.get(f"{month:02d}{day:02d}", []):
        rows.append({
            "year": ex.get("year", 0),
            "month": month,
            "day": day,
            "title": ex.get("title", ""),
            "desc": ex.get("desc", ""),
        })
    # 按 title 去重（内置优先，去掉 Wiki 与精选重复项）
    seen: set[str] = set()
    uniq: list[dict] = []
    for r in rows:
        k = r.get("title") or ""
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    # 过滤：只保留中国主体事件（剔除内置精选中混入的世界事件）
    uniq = [r for r in uniq if _is_cn_title(r.get("title") or "")]
    # 排序按年份降序（近的在前）
    uniq.sort(key=lambda r: -r.get("year", 0))
    # 不足 2 条时用通用 fallback 兜底（标记 fallback=True 让前端区别）
    if len(uniq) < 2:
        uniq.append({
            "year": 0,
            "month": month,
            "day": day,
            "title": fallback_line_for(month, day),
            "desc": "",
            "fallback": True,
        })
    return uniq


def _wiki_on_this_day(month: int, day: int) -> list[dict]:
    """从 Wikimedia Feed API 拉取历史上的今天事件，转为与内置数据相同的结构。"""
    cache_key = f"{month}-{day}"
    if cache_key in _HISTORY_CACHE:
        return _HISTORY_CACHE[cache_key]
    rows: list[dict] = []
    url = WIKI_ON_THIS_DAY.format(month=month, day=day)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "xuanhuang/1.0 (contact: dev@xuanhuang.local)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        events = (data.get("events") or [])
        for ev in events[:6]:
            year = ev.get("year")
            text = (ev.get("text") or "").strip()
            if not text:
                continue
            title = text[:40].rstrip("，。；,.;") + ("…" if len(text) > 40 else "")
            rows.append({"year": year or 0, "month": month, "day": day, "title": title, "desc": text})
    except Exception as e:  # noqa: BLE001
        logger.info("[today-in-history] wiki fetch skipped for %s-%s: %s", month, day, e)
    _HISTORY_CACHE[cache_key] = rows
    return rows


@router.get("/today-in-history")
def today_in_history(
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD；默认今天"),
    refresh: bool = Query(default=False, description="用户主动刷新：强制重新拉 Wikipedia 补全"),
    current_user: dict = Depends(get_current_user),
):
    if date:
        try:
            today_obj = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise_http(400, "日期格式应为 YYYY-MM-DD", 400)
    else:
        today_obj = _date_cls.today()
    month, day = today_obj.month, today_obj.day
    items = _builtin_today(month, day)
    # 用户主动刷新时尝试拉 Wikipedia 增强；失败/超时静默跳过
    if refresh:
        wiki_items = _wiki_on_this_day(month, day)
        existing_titles = {it["title"] for it in items}
        for it in wiki_items:
            if it["title"] not in existing_titles:
                items.append(it)
                existing_titles.add(it["title"])
    # 强制按年份降序展示（最近事件在前），同一天顺序完全固定（不洗牌）
    items = sorted(items, key=lambda r: -r.get("year", 0))
    return ok({
        "date": today_obj.isoformat(),
        "month": month,
        "day": day,
        "items": items,
    })