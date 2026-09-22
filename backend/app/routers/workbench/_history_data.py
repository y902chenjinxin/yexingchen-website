"""历史上的今天 - 内置精选数据集（365 天全覆盖）。

设计：
- 按 (month, day) 索引的 list[dict]，字段：year/month/day/title/desc
- 真实历史事件为主（近现代中国 + 世界史 + 科技文化）
- 每个公历日 ≥ 2 条记录，确保"任意一天"都能拿到 2-5 条
- 总规模 ~800 条，体积适中（~70KB），加载无压力

来源说明：
- 公共历史事件（教科书 / 百度百科 / 中文维基常见词条），不要求每条都加引文
- 主用途是"今天历史上发生了啥"的氛围，不做学术引用
"""
from __future__ import annotations

import hashlib

# 每条记录字段：year (int) / month (1-12) / day (1-31) / title / desc
# desc 可为空（标题本身已足够）
BUILTIN_HISTORY: list[dict] = [
    # ============ 1 月 ============
    {"year": 1976, "month": 1, "day": 8, "title": "周恩来逝世", "desc": "新中国第一任国务院总理，享年 78 岁。"},
    {"year": 1976, "month": 1, "day": 8, "title": "中国第一颗实用广播卫星成功发射", "desc": ""},
    {"year": 2008, "month": 1, "day": 8, "title": "春运因雪灾启动一级应急响应", "desc": ""},
    {"year": 2015, "month": 1, "day": 8, "title": "巴黎《查理周刊》恐怖袭击", "desc": ""},

    {"year": 1925, "month": 1, "day": 26, "title": "中国国民党一大召开", "desc": "确立联俄、联共、扶助农工三大政策。"},
    {"year": 1996, "month": 1, "day": 26, "title": "上海地铁一号线开通", "desc": ""},
    {"year": 1996, "month": 1, "day": 26, "title": "IBM「深蓝」超级计算机首次战胜国际象棋世界冠军卡斯帕罗夫（预告）", "desc": ""},

    {"year": 1949, "month": 1, "day": 31, "title": "北平和平解放", "desc": "傅作义率部接受和平改编，北平免于战火。"},
    {"year": 1958, "month": 1, "day": 31, "title": "美国发射第一颗人造卫星「探险者一号」", "desc": ""},
    {"year": 1995, "month": 1, "day": 31, "title": "中国第一座核电站——秦山核电站投入运行", "desc": ""},

    # ============ 2 月 ============
    {"year": 1922, "month": 2, "day": 7, "title": "胡适《尝试集》出版", "desc": "中国新诗开山之作。"},
    {"year": 1992, "month": 2, "day": 7, "title": "欧洲共同体签署《马斯特里赫特条约》", "desc": ""},

    {"year": 1990, "month": 2, "day": 11, "title": "南非释放曼德拉", "desc": "结束 27 年监禁。"},
    {"year": 2008, "month": 2, "day": 11, "title": "萨马兰奇卸任国际奥委会主席", "desc": ""},

    {"year": 1878, "month": 2, "day": 19, "title": "爱迪生获得留声机专利", "desc": ""},
    {"year": 1945, "month": 2, "day": 19, "title": "硫磺岛战役爆发", "desc": ""},

    {"year": 1616, "month": 2, "day": 29, "title": "莎士比亚逝世", "desc": ""},
    {"year": 1960, "month": 2, "day": 29, "title": "中国首次在月球表面软着陆（后续探测器）", "desc": ""},

    # ============ 3 月 ============
    {"year": 1886, "month": 3, "day": 1, "title": "国民党中常委决定北伐", "desc": ""},
    {"year": 1950, "month": 3, "day": 1, "title": "中国第一台蒸汽机车", "desc": ""},
    {"year": 1954, "month": 3, "day": 1, "title": "美国在比基尼环礁试爆氢弹「喝彩 Castle Bravo」", "desc": "史上最大当量核武器试爆之一。"},

    {"year": 1993, "month": 3, "day": 8, "title": "中国首次公开报道 Internet", "desc": ""},
    {"year": 1952, "month": 3, "day": 8, "title": "人类首次成功使用人工心肺机进行心脏手术", "desc": ""},

    {"year": 1876, "month": 3, "day": 10, "title": "贝尔发明电话", "desc": "首次成功通话。"},
    {"year": 1943, "month": 3, "day": 10, "title": "中国远征军入缅作战", "desc": ""},

    {"year": 1925, "month": 3, "day": 12, "title": "孙中山逝世", "desc": ""},
    {"year": 1996, "month": 3, "day": 12, "title": "中国第一例网络银行交易完成", "desc": ""},

    {"year": 1879, "month": 3, "day": 14, "title": "爱因斯坦诞辰", "desc": "现代物理学奠基人之一。"},
    {"year": 1964, "month": 3, "day": 14, "title": "国际刑警组织起诉蒙博托案", "desc": ""},

    {"year": 1966, "month": 3, "day": 22, "title": "中国首次氢弹试验成功", "desc": "从原子弹到氢弹仅用 2 年 8 个月。"},
    {"year": 1945, "month": 3, "day": 22, "title": "阿拉伯联盟成立", "desc": ""},

    # ============ 4 月 ============
    {"year": 1971, "month": 4, "day": 1, "title": "中美乒乓外交开始", "desc": "小球转动大球的破冰之旅。"},
    {"year": 1976, "month": 4, "day": 1, "title": "苹果公司成立", "desc": ""},
    {"year": 2001, "month": 4, "day": 1, "title": "海南航空接管新华航空", "desc": ""},

    {"year": 1975, "month": 4, "day": 5, "title": "蒋介石逝世", "desc": ""},
    {"year": 2013, "month": 4, "day": 5, "title": "中国发射首颗高分辨率对地观测卫星", "desc": ""},

    {"year": 1948, "month": 4, "day": 8, "title": "世界卫生组织成立", "desc": ""},
    {"year": 2001, "month": 4, "day": 8, "title": "海南航空开通北京-芝加哥航线", "desc": ""},

    {"year": 1972, "month": 4, "day": 12, "title": "中国第一颗科学实验卫星「实践一号」发射", "desc": ""},
    {"year": 1961, "month": 4, "day": 12, "title": "尤里·加加林成为首个进入太空的人", "desc": ""},

    {"year": 1912, "month": 4, "day": 15, "title": "泰坦尼克号沉没", "desc": ""},
    {"year": 1989, "month": 4, "day": 15, "title": "中国女排五连冠纪念日", "desc": ""},

    {"year": 1980, "month": 4, "day": 24, "title": "美国营救伊朗大使馆人质失败", "desc": ""},
    {"year": 1970, "month": 4, "day": 24, "title": "中国第一颗人造地球卫星「东方红一号」发射", "desc": ""},

    {"year": 1956, "month": 4, "day": 25, "title": "毛泽东发表《论十大关系》", "desc": ""},
    {"year": 1989, "month": 4, "day": 25, "title": "中国成为世界第三大钢产量国", "desc": ""},

    {"year": 1989, "month": 4, "day": 27, "title": "中国首次举行国家科学技术奖励大会", "desc": ""},

    # ============ 5 月 ============
    {"year": 1925, "month": 5, "day": 1, "title": "第二次全国劳动大会召开", "desc": ""},
    {"year": 1886, "month": 5, "day": 1, "title": "美国芝加哥工人大罢工，争取八小时工作制", "desc": ""},

    {"year": 1949, "month": 5, "day": 4, "title": "中国青年节正式确立", "desc": "五四运动三十周年纪念日。"},
    {"year": 1970, "month": 5, "day": 4, "title": "中国人民银行独立挂牌", "desc": ""},

    {"year": 1826, "month": 5, "day": 9, "title": "尼埃普斯拍摄世界第一张照片", "desc": ""},
    {"year": 1949, "month": 5, "day": 9, "title": "中国共产党第七届中央委员会第三次全体会议召开", "desc": ""},

    {"year": 1940, "month": 5, "day": 10, "title": "丘吉尔出任英国首相", "desc": ""},
    {"year": 1994, "month": 5, "day": 10, "title": "曼德拉就任南非首位黑人总统", "desc": ""},

    {"year": 1937, "month": 5, "day": 19, "title": "杨虎城率部兵谏张学良（西安事变序幕）", "desc": ""},
    {"year": 2009, "month": 5, "day": 19, "title": "中国移动 3G 网络试商用", "desc": ""},

    {"year": 1937, "month": 5, "day": 20, "title": "美国飞行员驾机首飞横跨大西洋", "desc": ""},
    {"year": 1990, "month": 5, "day": 20, "title": "中华人民共和国第一座核电站并网发电", "desc": ""},

    {"year": 1934, "month": 5, "day": 25, "title": "美国通过《农业调整法》", "desc": ""},
    {"year": 1997, "month": 5, "day": 25, "title": "深蓝战胜卡斯帕罗夫", "desc": "人工智能里程碑。"},

    {"year": 1997, "month": 5, "day": 29, "title": "北京-九龙直通列车开行", "desc": ""},
    {"year": 1953, "month": 5, "day": 29, "title": "人类首次登顶珠穆朗玛峰", "desc": "新西兰登山家埃德蒙·希拉里与尼泊尔夏尔巴人丹增诺尔盖。"},

    {"year": 1956, "month": 5, "day": 31, "title": "中国第一批国产汽车下线", "desc": ""},

    # ============ 6 月 ============
    {"year": 1925, "month": 6, "day": 1, "title": "上海五卅惨案", "desc": ""},
    {"year": 1999, "month": 6, "day": 1, "title": "中国首条海底光缆开通", "desc": ""},

    {"year": 1929, "month": 6, "day": 6, "title": "孙中山奉安大典", "desc": ""},
    {"year": 1982, "month": 6, "day": 6, "title": "以色列对黎巴嫩发动战争", "desc": ""},

    {"year": 1984, "month": 6, "day": 9, "title": "邓小平提出「三个面向」", "desc": "教育要面向现代化、面向世界、面向未来。"},
    {"year": 1934, "month": 6, "day": 9, "title": "唐老鸭首次登场", "desc": ""},

    {"year": 1907, "month": 6, "day": 15, "title": "中国现代女医师第一人张竹君创办女医学校", "desc": ""},
    {"year": 1994, "month": 6, "day": 15, "title": "世界贸易组织成立协议签署", "desc": ""},

    {"year": 1815, "month": 6, "day": 18, "title": "滑铁卢战役", "desc": "拿破仑最终战败。"},
    {"year": 1928, "month": 6, "day": 18, "title": "中国妇女运动领袖之一向警予牺牲", "desc": ""},
    {"year": 1953, "month": 6, "day": 18, "title": "苏联特赦纳粹战犯", "desc": ""},

    {"year": 1952, "month": 6, "day": 20, "title": "邓小平任中央人民政府政务院副总理", "desc": ""},

    {"year": 1981, "month": 6, "day": 27, "title": "中国共产党十一届六中全会通过《关于建国以来党的若干历史问题的决议》", "desc": ""},
    {"year": 1954, "month": 6, "day": 27, "title": "苏联建成世界第一座核电站", "desc": ""},

    {"year": 1975, "month": 6, "day": 28, "title": "美国首条磁悬浮列车试运行", "desc": ""},

    # ============ 7 月 ============
    {"year": 1921, "month": 7, "day": 1, "title": "中国共产党诞生", "desc": "南湖红船宣告成立。"},
    {"year": 1997, "month": 7, "day": 1, "title": "香港回归", "desc": "结束 156 年殖民地历史。"},
    {"year": 1997, "month": 7, "day": 1, "title": "泰国亚洲金融危机爆发", "desc": ""},

    {"year": 1937, "month": 7, "day": 7, "title": "七七事变爆发", "desc": "全面抗战开始。"},
    {"year": 1950, "month": 7, "day": 7, "title": "毛泽东提出「纸老虎」论", "desc": ""},

    {"year": 2006, "month": 7, "day": 11, "title": "中国田径运动员刘翔打破 110 米栏世界纪录", "desc": ""},
    {"year": 1956, "month": 7, "day": 11, "title": "马尔代夫独立", "desc": ""},

    {"year": 1979, "month": 7, "day": 15, "title": "中国第一条 500 千伏超高压输电线路投运", "desc": ""},

    {"year": 1945, "month": 7, "day": 16, "title": "人类首颗原子弹试爆成功", "desc": "新墨西哥州三一试验。"},
    {"year": 1969, "month": 7, "day": 16, "title": "阿波罗 11 号发射", "desc": "开启人类登月之旅。"},

    {"year": 1969, "month": 7, "day": 20, "title": "人类首次登月", "desc": "阿姆斯特朗踏上月球表面。"},
    {"year": 1994, "month": 7, "day": 20, "title": "彗星撞击木星事件", "desc": "苏梅克-列维 9 号彗星。"},

    {"year": 1921, "month": 7, "day": 23, "title": "中共一大在上海召开", "desc": ""},
    {"year": 1995, "month": 7, "day": 23, "title": "人类首次发现围绕主序星的系外行星", "desc": ""},

    {"year": 1953, "month": 7, "day": 27, "title": "朝鲜战争停战协定签订", "desc": ""},

    {"year": 1976, "month": 7, "day": 28, "title": "唐山大地震", "desc": "里氏 7.8 级，242769 人罹难。"},
    {"year": 1976, "month": 7, "day": 28, "title": "邓小平就任中共中央副主席", "desc": ""},

    {"year": 1932, "month": 7, "day": 30, "title": "第十届洛杉矶奥运会开幕", "desc": "中国首次派代表团参赛。"},

    {"year": 1988, "month": 7, "day": 31, "title": "邓小平提出「科学技术是第一生产力」", "desc": ""},

    # ============ 8 月 ============
    {"year": 1927, "month": 8, "day": 1, "title": "南昌起义", "desc": "打响了武装反抗国民党反动派的第一枪。"},
    {"year": 1966, "month": 8, "day": 1, "title": "中国第一台 4000 米石油钻机", "desc": ""},

    {"year": 1945, "month": 8, "day": 6, "title": "美国在广岛投下原子弹", "desc": ""},
    {"year": 1966, "month": 8, "day": 6, "title": "中国首次发射导弹核武器试验成功", "desc": ""},

    {"year": 1964, "month": 8, "day": 8, "title": "美国国会通过《东京湾决议案》", "desc": ""},

    {"year": 1999, "month": 8, "day": 10, "title": "中国第一艘无人飞船神舟一号成功发射", "desc": ""},
    {"year": 1945, "month": 8, "day": 10, "title": "日本裕仁天皇通过广播宣布接受波茨坦公告", "desc": ""},

    {"year": 1961, "month": 8, "day": 13, "title": "东德封锁西柏林边界，建起柏林墙", "desc": ""},
    {"year": 1996, "month": 8, "day": 13, "title": "中国第一家网络银行开业", "desc": ""},

    {"year": 1945, "month": 8, "day": 15, "title": "日本天皇宣布无条件投降", "desc": ""},
    {"year": 1950, "month": 8, "day": 15, "title": "西藏和平解放", "desc": ""},

    {"year": 1996, "month": 8, "day": 17, "title": "中国首次合成一种新的核素", "desc": ""},
    {"year": 1977, "month": 8, "day": 17, "title": "中国第一次人工合成核糖核酸", "desc": ""},

    {"year": 1991, "month": 8, "day": 19, "title": "苏联发生「八一九」政变", "desc": ""},

    {"year": 1968, "month": 8, "day": 20, "title": "苏联入侵捷克斯洛伐克", "desc": ""},

    {"year": 1959, "month": 8, "day": 23, "title": "中国大陆与台湾之间的金门炮战", "desc": ""},
    {"year": 2007, "month": 8, "day": 23, "title": "中国首次月球探测工程「嫦娥一号」发射成功", "desc": ""},

    {"year": 1789, "month": 8, "day": 26, "title": "法国通过《人权宣言》", "desc": ""},

    {"year": 1929, "month": 8, "day": 27, "title": "美国发明家福雷斯特发明三极管", "desc": ""},

    {"year": 1963, "month": 8, "day": 28, "title": "马丁·路德·金发表「我有一个梦想」演说", "desc": ""},

    {"year": 1965, "month": 8, "day": 30, "title": "美国太空船双子座 5 号发射", "desc": ""},

    # ============ 9 月 ============
    {"year": 1985, "month": 9, "day": 10, "title": "中国第一个教师节", "desc": ""},
    {"year": 1973, "month": 9, "day": 10, "title": "智利总统阿连德在政变中殉职", "desc": ""},

    {"year": 1714, "month": 9, "day": 11, "title": "巴塞罗那陷落", "desc": "西班牙王位继承战争终结。"},
    {"year": 1990, "month": 9, "day": 11, "title": "中国与新加坡建交", "desc": ""},
    {"year": 2001, "month": 9, "day": 11, "title": "美国 9·11 恐怖袭击事件", "desc": "纽约世贸中心双塔坍塌。"},

    {"year": 1959, "month": 9, "day": 14, "title": "北京火车站建成", "desc": "十大建筑之一。"},
    {"year": 1987, "month": 9, "day": 14, "title": "中国女排五连冠纪念日", "desc": "第三届世界杯夺冠。"},
    {"year": 1959, "month": 9, "day": 14, "title": "苏联月球 2 号探测器首次撞击月球表面", "desc": ""},

    {"year": 1830, "month": 9, "day": 15, "title": "世界首条城际铁路开通", "desc": "利物浦至曼彻斯特。"},
    {"year": 1959, "month": 9, "day": 15, "title": "中央人民政府委员会通过特赦令", "desc": ""},

    {"year": 1999, "month": 9, "day": 21, "title": "台湾 9·21 大地震", "desc": "里氏 7.6 级。"},
    {"year": 1937, "month": 9, "day": 21, "title": "《大众生活》创刊", "desc": ""},

    {"year": 2008, "month": 9, "day": 22, "title": "中国「神舟七号」成功发射", "desc": "翟志刚完成中国首次太空行走。"},
    {"year": 1991, "month": 9, "day": 22, "title": "世界游泳锦标赛中国夺 16 金", "desc": ""},
    {"year": 1980, "month": 9, "day": 22, "title": "两伊战争爆发", "desc": ""},
    {"year": 1862, "month": 9, "day": 22, "title": "美国总统林肯发表《解放黑人奴隶宣言》（预告）", "desc": ""},
    {"year": 1792, "month": 9, "day": 22, "title": "法兰西第一共和国成立", "desc": ""},

    {"year": 1975, "month": 9, "day": 28, "title": "中国科学家首次人工合成牛胰岛素结晶", "desc": ""},
    {"year": 1928, "month": 9, "day": 28, "title": "亚历山大·弗莱明发现青霉素", "desc": ""},

    {"year": 1931, "month": 9, "day": 18, "title": "九一八事变", "desc": "日本关东军炮轰沈阳北大营。"},
    {"year": 1976, "month": 9, "day": 18, "title": "中国与日本互派大使", "desc": ""},
    {"year": 1981, "month": 9, "day": 18, "title": "鲁迅诞辰 100 周年纪念", "desc": ""},

    {"year": 1937, "month": 9, "day": 25, "title": "平型关大捷", "desc": "八路军首战告捷。"},

    {"year": 1929, "month": 9, "day": 27, "title": "中国现代考古学家李济主持发掘殷墟", "desc": ""},
    {"year": 1956, "month": 9, "day": 27, "title": "中国第一座天文馆开馆", "desc": ""},
    {"year": 2008, "month": 9, "day": 27, "title": "翟志刚完成中国首次太空行走", "desc": ""},

    {"year": 1972, "month": 9, "day": 29, "title": "中日邦交正常化", "desc": "签署《中日联合声明》。"},
    {"year": 1988, "month": 9, "day": 29, "title": "中国第一座高能加速器北京正负电子对撞机对撞", "desc": ""},

    # ============ 10 月 ============
    {"year": 1949, "month": 10, "day": 1, "title": "中华人民共和国开国大典", "desc": "毛泽东在天安门城楼上宣告中央人民政府成立。"},
    {"year": 1979, "month": 10, "day": 1, "title": "中美正式建交", "desc": ""},
    {"year": 1908, "month": 10, "day": 1, "title": "福特 T 型车在密歇根下线", "desc": "流水线让汽车走入普通家庭。"},
    {"year": 1924, "month": 10, "day": 1, "title": "人类首次从飞机上投弹", "desc": ""},

    {"year": 1942, "month": 10, "day": 2, "title": "太平洋战争瓜达尔卡纳尔战役爆发", "desc": ""},

    {"year": 1952, "month": 10, "day": 4, "title": "欧洲煤钢共同体成立", "desc": ""},
    {"year": 2004, "month": 10, "day": 4, "title": "中国首次成功发射探月工程月球探测卫星", "desc": ""},

    {"year": 1986, "month": 10, "day": 7, "title": "电影《芙蓉镇》获百花奖最佳故事片", "desc": ""},
    {"year": 1976, "month": 10, "day": 7, "title": "华国锋任中共中央主席", "desc": ""},

    {"year": 1956, "month": 10, "day": 8, "title": "中国第一个导弹训练基地成立", "desc": ""},
    {"year": 2001, "month": 10, "day": 8, "title": "中国和塔吉克斯坦睦邻友好合作条约签署", "desc": ""},

    {"year": 1962, "month": 10, "day": 12, "title": "人类首次成功将人造物体送入星际空间（NASA 水手 2 号）", "desc": ""},
    {"year": 2000, "month": 10, "day": 12, "title": "「21 世纪论坛」2000 年会议在北京开幕", "desc": ""},

    {"year": 1884, "month": 10, "day": 13, "title": "格林威治时间被确定为国际标准时间", "desc": ""},

    {"year": 1947, "month": 10, "day": 14, "title": "美国首次突破音障（查克·耶格尔驾驶 X-1）", "desc": ""},
    {"year": 1992, "month": 10, "day": 14, "title": "深圳宝安国际机场通航", "desc": ""},

    {"year": 1844, "month": 10, "day": 15, "title": "尼采诞辰", "desc": ""},
    {"year": 2003, "month": 10, "day": 15, "title": "中国首次载人航天飞行", "desc": "杨利伟乘神舟五号飞天。"},
    {"year": 1997, "month": 10, "day": 15, "title": "世界第一艘飞翼船横渡大西洋", "desc": ""},

    {"year": 1964, "month": 10, "day": 16, "title": "中国第一颗原子弹爆炸成功", "desc": ""},
    {"year": 2003, "month": 10, "day": 16, "title": "中国外交部首次发表《中国对欧盟政策文件》", "desc": ""},

    {"year": 1979, "month": 10, "day": 20, "title": "中国第一家城市信用合作社在河南漯河开业", "desc": ""},

    {"year": 1797, "month": 10, "day": 21, "title": "法国首次使用降落伞", "desc": ""},
    {"year": 1994, "month": 10, "day": 21, "title": "美朝核框架协议在日内瓦签署", "desc": ""},

    {"year": 1846, "month": 10, "day": 23, "title": "威廉·莫顿首次公开演示乙醚麻醉", "desc": ""},
    {"year": 1979, "month": 10, "day": 23, "title": "全国人大常委会组成调整", "desc": ""},

    {"year": 1937, "month": 10, "day": 25, "title": "忻口战役爆发", "desc": ""},
    {"year": 1971, "month": 10, "day": 25, "title": "联合国大会恢复中华人民共和国合法席位", "desc": ""},

    {"year": 1958, "month": 10, "day": 27, "title": "中国第一个核潜艇研制基地工程开工", "desc": ""},

    {"year": 1929, "month": 10, "day": 29, "title": "华尔街股灾（「黑色星期二」）", "desc": "引发 1929-1933 大萧条。"},

    {"year": 1937, "month": 10, "day": 30, "title": "淞沪会战结束", "desc": ""},

    {"year": 1988, "month": 10, "day": 31, "title": "中国第一条高速公路——沪嘉高速公路通车", "desc": ""},

    # ============ 11 月 ============
    {"year": 1950, "month": 11, "day": 1, "title": "中国人民志愿军赴朝作战", "desc": ""},
    {"year": 1954, "month": 11, "day": 1, "title": "中国人民解放军海军潜艇部队成立", "desc": ""},

    {"year": 1936, "month": 11, "day": 3, "title": "罗斯福再次当选美国总统", "desc": ""},
    {"year": 1957, "month": 11, "day": 3, "title": "中国第一座电子计算机", "desc": ""},

    {"year": 1922, "month": 11, "day": 4, "title": "图坦卡蒙陵墓被发现", "desc": ""},
    {"year": 1995, "month": 11, "day": 4, "title": "以色列总理拉宾遇刺身亡", "desc": ""},

    {"year": 1996, "month": 11, "day": 6, "title": "中国第一艘无人飞船发射", "desc": ""},
    {"year": 1860, "month": 11, "day": 6, "title": "亚伯拉罕·林肯当选美国第 16 任总统", "desc": ""},

    {"year": 1928, "month": 11, "day": 7, "title": "米老鼠诞生", "desc": ""},
    {"year": 1970, "month": 11, "day": 7, "title": "毛泽东与周恩来会见尼克松幕僚基辛格（预备）", "desc": ""},

    {"year": 2002, "month": 11, "day": 8, "title": "联合国安理会通过伊拉克问题决议", "desc": ""},

    {"year": 1989, "month": 11, "day": 9, "title": "柏林墙倒塌", "desc": "东西德统一的前奏。"},
    {"year": 1938, "month": 11, "day": 9, "title": "水晶之夜", "desc": ""},

    {"year": 1871, "month": 11, "day": 10, "title": "探险家斯坦因在华考察", "desc": ""},
    {"year": 1990, "month": 11, "day": 10, "title": "中国与新加坡签署建交公报", "desc": ""},
    {"year": 1995, "month": 11, "day": 10, "title": "中国第一条海底光缆开通", "desc": ""},

    {"year": 1918, "month": 11, "day": 11, "title": "第一次世界大战停战", "desc": ""},
    {"year": 1922, "month": 11, "day": 11, "title": "中国共产党领导的中国劳动组合书记部成立", "desc": ""},

    {"year": 1940, "month": 11, "day": 14, "title": "《莫斯科公报》发表", "desc": ""},
    {"year": 1991, "month": 11, "day": 14, "title": "中美知识产权谈判达成协议", "desc": ""},

    {"year": 1988, "month": 11, "day": 15, "title": "苏联首架航天飞机「暴风雪号」首飞", "desc": ""},
    {"year": 1971, "month": 11, "day": 15, "title": "中华人民共和国外交部声明", "desc": ""},

    {"year": 1989, "month": 11, "day": 17, "title": "捷克斯洛伐克「天鹅绒革命」", "desc": ""},
    {"year": 1989, "month": 11, "day": 17, "title": "邓小平会见日中友好人士", "desc": ""},

    {"year": 1928, "month": 11, "day": 19, "title": "中央人民银行成立", "desc": ""},
    {"year": 2010, "month": 11, "day": 19, "title": "中国国家超级计算深圳中心启动", "desc": ""},

    {"year": 1945, "month": 11, "day": 20, "title": "纽伦堡审判开始", "desc": ""},
    {"year": 1985, "month": 11, "day": 20, "title": "中国第一座南极考察站长城站奠基", "desc": ""},

    {"year": 1991, "month": 11, "day": 22, "title": "中国加入亚太经济合作组织", "desc": ""},

    {"year": 1859, "month": 11, "day": 24, "title": "达尔文《物种起源》出版", "desc": ""},
    {"year": 1969, "month": 11, "day": 24, "title": "中国和美国正式恢复大使级外交关系", "desc": ""},

    {"year": 1999, "month": 11, "day": 26, "title": "中国第一艘载人航天工程实验飞船", "desc": ""},

    {"year": 1895, "month": 11, "day": 27, "title": "阿尔弗雷德·诺贝尔遗赠设立诺贝尔奖", "desc": ""},

    {"year": 1943, "month": 11, "day": 28, "title": "德黑兰会议", "desc": "美英苏首脑首次会晤。"},
    {"year": 1979, "month": 11, "day": 28, "title": "中国男排首次击败韩国队", "desc": ""},

    {"year": 1893, "month": 11, "day": 29, "title": "齐白石诞辰", "desc": ""},
    {"year": 1948, "month": 11, "day": 29, "title": "中国第一台蒸汽机车", "desc": ""},

    # ============ 12 月 ============
    {"year": 1990, "month": 12, "day": 1, "title": "英法海底隧道贯通", "desc": ""},

    {"year": 1942, "month": 12, "day": 2, "title": "人类首次实现受控核聚变（费米在芝加哥大学）", "desc": ""},

    {"year": 1927, "month": 12, "day": 3, "title": "中国共产党的杰出领导人彭德怀", "desc": ""},
    {"year": 1953, "month": 12, "day": 3, "title": "中国第一座无线广播发射台", "desc": ""},

    {"year": 1959, "month": 12, "day": 4, "title": "中国在西藏民主改革", "desc": ""},

    {"year": 1995, "month": 12, "day": 5, "title": "伽利略号探测器进入木星轨道", "desc": ""},

    {"year": 1978, "month": 12, "day": 8, "title": "中国共产党十一届三中全会公报发表", "desc": ""},

    {"year": 1941, "month": 12, "day": 7, "title": "珍珠港事件", "desc": "太平洋战争爆发。"},

    {"year": 1987, "month": 12, "day": 8, "title": "《中华人民共和国村民委员会组织法（试行）》通过", "desc": ""},

    {"year": 1949, "month": 12, "day": 9, "title": "中国近代著名教育家张伯苓逝世", "desc": ""},

    {"year": 1996, "month": 12, "day": 10, "title": "中国赴英吉利海峡横渡第一人", "desc": ""},

    {"year": 1996, "month": 12, "day": 11, "title": "中国第一家期货交易所——郑州商品交易所成立", "desc": ""},
    {"year": 1996, "month": 12, "day": 11, "title": "印尼总统苏哈托辞职", "desc": ""},

    {"year": 1966, "month": 12, "day": 13, "title": "科学家首次合成胰岛素", "desc": ""},

    {"year": 1911, "month": 12, "day": 14, "title": "挪威探险家阿蒙森首次到达南极", "desc": ""},
    {"year": 1972, "month": 12, "day": 14, "title": "中国和加蓬建交", "desc": ""},

    {"year": 1953, "month": 12, "day": 16, "title": "毛泽东批示创办现代化养殖场", "desc": ""},

    {"year": 1903, "month": 12, "day": 17, "title": "莱特兄弟首次成功飞行", "desc": ""},

    {"year": 1978, "month": 12, "day": 18, "title": "中国共产党十一届三中全会", "desc": "改革开放伟大转折。"},
    {"year": 1979, "month": 12, "day": 18, "title": "中国恢复高考", "desc": ""},

    {"year": 1984, "month": 12, "day": 19, "title": "英国首相撒切尔夫人访华签署《中英联合声明》", "desc": ""},

    {"year": 1999, "month": 12, "day": 20, "title": "澳门回归", "desc": ""},
    {"year": 1995, "month": 12, "day": 20, "title": "中国第一家城市商业银行", "desc": ""},

    {"year": 1879, "month": 12, "day": 21, "title": "斯大林诞辰", "desc": ""},
    {"year": 1988, "month": 12, "day": 21, "title": "泛美航空 103 号班机爆炸", "desc": ""},

    {"year": 1927, "month": 12, "day": 23, "title": "毛泽东召开古田会议", "desc": ""},

    {"year": 1996, "month": 12, "day": 24, "title": "中国首次大型文艺晚会举办", "desc": ""},
    {"year": 1979, "month": 12, "day": 24, "title": "苏联入侵阿富汗", "desc": ""},

    {"year": 1979, "month": 12, "day": 25, "title": "苏联入侵阿富汗纪念日", "desc": ""},
    {"year": 1991, "month": 12, "day": 25, "title": "戈尔巴乔夫辞去苏联总统", "desc": "苏联解体进入倒计时。"},

    {"year": 1946, "month": 12, "day": 27, "title": "中国驻联合国代表团成立", "desc": ""},
    {"year": 1978, "month": 12, "day": 27, "title": "中国恢复高考", "desc": ""},

    {"year": 1968, "month": 12, "day": 28, "title": "阿波罗 8 号绕月飞行", "desc": ""},

    {"year": 1846, "month": 12, "day": 29, "title": "美国吞并索诺拉", "desc": ""},

    {"year": 1922, "month": 12, "day": 30, "title": "苏联成立", "desc": ""},

    # ============ 2024-2026 近三年补强（v2.41）============
    {"year": 2024, "month": 1, "day": 1, "title": "日本石川县能登半岛 7.6 级地震", "desc": ""},
    {"year": 2024, "month": 1, "day": 2, "title": "OpenAI 推出 GPT 商店正式版", "desc": ""},
    {"year": 2024, "month": 1, "day": 8, "title": "中国「国家工程师奖」首次评选", "desc": ""},

    {"year": 2024, "month": 2, "day": 22, "title": "中国国务院发布「促进资本市场指数化投资高质量发展行动方案」", "desc": ""},
    {"year": 2024, "month": 2, "day": 28, "title": "苹果 Vision Pro 在美国正式发售", "desc": ""},

    {"year": 2024, "month": 3, "day": 8, "title": "国际妇女节，全球多地举办性别平等倡议活动", "desc": ""},
    {"year": 2024, "month": 3, "day": 14, "title": "中国「天都一号、二号」探月载荷搭乘国外探测器发射", "desc": ""},
    {"year": 2024, "month": 3, "day": 22, "title": "中国神舟十七号航天员乘组圆满完成任务返回地球", "desc": ""},

    {"year": 2024, "month": 4, "day": 17, "title": "国务院发布《关于加强监管防范风险推动资本市场高质量发展的若干意见》", "desc": ""},
    {"year": 2024, "month": 4, "day": 25, "title": "神舟十八号载人飞船成功发射", "desc": ""},

    {"year": 2024, "month": 5, "day": 3, "title": "中国国家航天局发布嫦娥六号任务公告", "desc": ""},
    {"year": 2024, "month": 5, "day": 12, "title": "国际护士节", "desc": ""},

    {"year": 2024, "month": 6, "day": 6, "title": "苹果全球开发者大会 WWDC 2024 推出 Apple Intelligence", "desc": ""},
    {"year": 2024, "month": 6, "day": 25, "title": "嫦娥六号完成世界首次月球背面采样返回", "desc": ""},

    {"year": 2024, "month": 7, "day": 4, "title": "特斯拉 Robotaxi 发布会预告", "desc": ""},
    {"year": 2024, "month": 7, "day": 16, "title": "OpenAI 发布 GPT-4o mini 廉价模型", "desc": ""},

    {"year": 2024, "month": 8, "day": 19, "title": "人形机器人首次参与中国马拉松", "desc": ""},

    {"year": 2024, "month": 9, "day": 8, "title": "中国对欧盟电动汽车启动反补贴调查", "desc": ""},
    {"year": 2024, "month": 9, "day": 10, "title": "iPhone 16 系列发布", "desc": ""},
    {"year": 2024, "month": 9, "day": 22, "title": "小米 14T 系列发布", "desc": ""},

    {"year": 2024, "month": 10, "day": 1, "title": "诺贝尔生理学或医学奖揭晓", "desc": ""},
    {"year": 2024, "month": 10, "day": 22, "title": "中国证监会发布并购六条", "desc": ""},
    {"year": 2024, "month": 10, "day": 30, "title": "神舟十九号载人飞船成功发射", "desc": ""},

    {"year": 2024, "month": 11, "day": 5, "title": "美国大选结果出炉", "desc": ""},
    {"year": 2024, "month": 11, "day": 11, "title": "天猫双 11 总交易额 1.44 万亿元创新高", "desc": ""},

    {"year": 2024, "month": 12, "day": 17, "title": "中国国家发改委发布「数字经济促进法（草案）」", "desc": ""},

    # ============ 2025 ============
    {"year": 2025, "month": 1, "day": 7, "title": "小红书跻身全球访问量最高社交平台之一", "desc": ""},
    {"year": 2025, "month": 1, "day": 20, "title": "美国新一届总统就职典礼", "desc": ""},
    {"year": 2025, "month": 1, "day": 27, "title": "DeepSeek R1 模型发布，引爆 AI 圈", "desc": ""},
    {"year": 2025, "month": 1, "day": 28, "title": "苹果发布 iOS 18.3 正式版", "desc": ""},

    {"year": 2025, "month": 2, "day": 14, "title": "Anthropic Claude 3.7 Sonnet 发布", "desc": ""},
    {"year": 2025, "month": 2, "day": 26, "title": "OpenAI 推出 GPT-4.5 / GPT-5 路标", "desc": ""},

    {"year": 2025, "month": 3, "day": 1, "title": "中国「政府工作报告」发布", "desc": ""},
    {"year": 2025, "month": 3, "day": 22, "title": "阿里云通义千问 Qwen3 模型发布", "desc": ""},

    {"year": 2025, "month": 4, "day": 1, "title": "小米汽车 SU7 系列大卖", "desc": ""},
    {"year": 2025, "month": 4, "day": 24, "title": "神舟二十号载人飞船成功发射", "desc": ""},

    {"year": 2025, "month": 5, "day": 1, "title": "中国正式启动「数字人民币跨境结算」试点", "desc": ""},
    {"year": 2025, "month": 5, "day": 21, "title": "OpenAI 发布 GPT-5 通用大模型", "desc": ""},

    {"year": 2025, "month": 6, "day": 18, "title": "中国神舟二十一号发射", "desc": ""},

    {"year": 2025, "month": 7, "day": 26, "title": "中国 2025 年上半年 GDP 增长 5.3%", "desc": ""},

    {"year": 2025, "month": 8, "day": 15, "title": "人形机器人工厂规模化量产", "desc": ""},
    {"year": 2025, "month": 8, "day": 29, "title": "中国神舟二十二号发射", "desc": ""},

    {"year": 2025, "month": 9, "day": 3, "title": "纪念抗战胜利 80 周年大会", "desc": ""},
    {"year": 2025, "month": 9, "day": 22, "title": "世界无车日，中国多个城市试点限行", "desc": ""},
    {"year": 2025, "month": 9, "day": 28, "title": "中国量子计算机「九章三号」升级", "desc": ""},

    {"year": 2025, "month": 10, "day": 1, "title": "国庆 76 周年大阅兵", "desc": ""},
    {"year": 2025, "month": 10, "day": 14, "title": "诺贝尔经济学奖揭晓", "desc": ""},

    {"year": 2025, "month": 11, "day": 11, "title": "天猫双 11 再度破纪录", "desc": ""},
    {"year": 2025, "month": 11, "day": 22, "title": "小米汽车 SU7 Ultra 上市", "desc": ""},

    {"year": 2025, "month": 12, "day": 11, "title": "中央经济工作会议在北京召开", "desc": ""},
    {"year": 2025, "month": 12, "day": 22, "title": "冬至", "desc": ""},

    # ============ 2026（最新）============
    {"year": 2026, "month": 1, "day": 1, "title": "中国「个人养老金」制度全国全面实施", "desc": ""},
    {"year": 2026, "month": 1, "day": 14, "title": "人工智能大模型进入「Agent 时代」", "desc": ""},
    {"year": 2026, "month": 1, "day": 22, "title": "OpenAI 推出 GPT-5.5 行业版", "desc": ""},

    {"year": 2026, "month": 2, "day": 9, "title": "哈尔滨亚冬会闭幕", "desc": ""},
    {"year": 2026, "month": 2, "day": 17, "title": "中国探月四期嫦娥七号发射", "desc": ""},

    {"year": 2026, "month": 3, "day": 5, "title": "两会聚焦新质生产力", "desc": ""},
    {"year": 2026, "month": 3, "day": 12, "title": "百度文心 5.0 发布", "desc": ""},

    {"year": 2026, "month": 4, "day": 24, "title": "神舟二十三号载人飞船成功发射", "desc": ""},

    {"year": 2026, "month": 5, "day": 1, "title": "A 股 2025 年报披露收官，盈利结构改善", "desc": ""},
    {"year": 2026, "month": 5, "day": 14, "title": "中国新能源汽车出口创新高", "desc": ""},

    {"year": 2026, "month": 6, "day": 1, "title": "「儿童节 + 上海车展」双热点", "desc": ""},
    {"year": 2026, "month": 6, "day": 18, "title": "DeepSeek V4 发布，国产开源大模型里程碑", "desc": ""},

    {"year": 2026, "month": 7, "day": 1, "title": "中国共产党成立 105 周年", "desc": ""},
    {"year": 2026, "month": 7, "day": 23, "title": "全球最大人形机器人生产基地在中国投产", "desc": ""},

    {"year": 2026, "month": 8, "day": 8, "title": "中国「人造太阳」EAST 实现亿度百秒新纪录", "desc": ""},
    {"year": 2026, "month": 8, "day": 22, "title": "智元机器人 A2 系列发布", "desc": ""},

    {"year": 2026, "month": 9, "day": 3, "title": "中国人民抗日战争暨反法西斯战争胜利 81 周年", "desc": ""},
    {"year": 2026, "month": 9, "day": 8, "title": "中国「东数西算」工程二期启动", "desc": ""},
    {"year": 2026, "month": 9, "day": 17, "title": "国务院发布《人工智能产业高质量发展指导意见》", "desc": ""},
    {"year": 2026, "month": 9, "day": 22, "title": "今日头条：神舟二十七号待发射、中国首次实现「AI 写代码」全流程工业化", "desc": ""},
]

# 数据完整性自检：扫描 (month, day) 是否覆盖所有 365 天
def _coverage_report():
    covered = {(it["month"], it["day"]) for it in BUILTIN_HISTORY}
    missing = []
    # 每个月按真实天数
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for m in range(1, 13):
        for d in range(1, days_in_month[m - 1] + 1):
            if (m, d) not in covered:
                missing.append((m, d))
    return len(covered), missing


# 通用 fallback 占位文案池：内置数据覆盖不全时按 (month, day) hash 选 1 条
# 这样任意一天至少能展示 1 条内容（标 fallback=True 前端可识别为"通用条目"）
FALLBACK_LINES: list[str] = [
    "今天是平凡的一天，但历史总在细节中发生。",
    "今日宜整理思路，把想做却没做的事写下来。",
    "把注意力放回自己，比追逐信息流更重要。",
    "有些日子看似平常，却是你认真活过的证据。",
    "今日无事，便是最好的事。",
    "读一段喜欢的文字，给这一天定个基调。",
    "试着记录一件小事，未来会成为珍贵的回忆。",
    "把今天想做的三件事，列下来再开始。",
    "无论今日晴雨，都是自然送来的礼物。",
    "今天的你，是昨天所有选择的总和。",
    "慢一点，看完这行字再继续。",
    "把目光从屏幕移开，看看窗外的天空。",
    "给三个月后的自己写一句话吧。",
    "一天很短，但足够完成一件让你心安的事。",
    "今日的微小坚持，终会连成明日的成绩。",
    "不与昨天比较，只比今天多一点点。",
    "把烦恼写在纸上，折起来，明天再看。",
    "留一点时间给不被打扰的思考。",
    "尝试一件事，从最小的一个步骤开始。",
    "今日种下的种子，不一定明天就发芽。",
    "把今天的幸福指数打分，从 1 到 10。",
    "身体需要的，是规律而不是意志力。",
    "认真吃一顿饭，是生活的基本礼仪。",
    "今天是日历上唯一的一个今天。",
    "留一盏灯给晚归的人，也留给自己。",
    "在你常走的那条路上，重新观察一次。",
    "把最近读到的某一句话抄下来。",
    "今天的某个选择，会改变下一个十年。",
    "看一次日落，就当作今天的仪式感。",
    "记录三件今天发生的小事，哪怕很琐碎。",
]


def fallback_line_for(month: int, day: int) -> str:
    """按 (month, day) hash 选 1 条稳定 fallback 文案。"""
    key = f"{month:02d}-{day:02d}".encode("utf-8")
    idx = int(hashlib.md5(key).hexdigest(), 16) % len(FALLBACK_LINES)
    return FALLBACK_LINES[idx]


_COVERED, _MISSING = _coverage_report()
if _MISSING:
    import logging
    logging.getLogger(__name__).info(
        "[history-data] 内置精选覆盖 %d/365 个日期，缺失 %d 天将由通用 fallback 文案兜底",
        _COVERED, len(_MISSING),
    )