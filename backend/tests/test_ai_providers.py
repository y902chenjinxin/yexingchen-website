from app.services.ai_providers import (
    AiRequest,
    HttpProvider,
    _extract_json_object,
    _polish_readable,
    _remove_embedded_json,
    _strip_reasoning,
)

import sys
import types


def _provider():
    return HttpProvider(
        base_url="http://unused.example/v1",
        model="m",
        api_key="k",
        timeout=5,
    )


# ---------- _strip_reasoning ----------
def test_strip_reasoning_removes_thinking_blocks():
    raw = (
        '用户要求仅返回JSON。<thinking>先分析键名…</thinking>'
        '<thought>这是思考过程</thought>'
        "```think\ninternal reasoning\n```"
        '{"a":1}'
    )
    out = _strip_reasoning(raw)
    assert "thinking" not in out
    assert "思考" not in out
    assert "internal" not in out
    assert "{" in out  # JSON 仍在；strip 只删思考标记，不删前置文字

    # thinking 用英文标签
    out2 = _strip_reasoning('<thinking>hmm</thinking>{"b":2}')
    assert out2 == '{"b":2}'


# ---------- _extract_json_object ----------
def test_extract_json_from_clean_object():
    assert _extract_json_object('{"summary":"x","reply":"y"}') == {"summary": "x", "reply": "y"}


def test_extract_json_from_fenced_block():
    raw = "```json\n{\"summary\":\"ok\",\"new_key\":\"v\"}\n```"
    assert _extract_json_object(raw) == {"summary": "ok", "new_key": "v"}


def test_extract_json_ignores_surrounding_reasoning_text():
    raw = (
        "我先思考一下。<thinking>This looks reasonable.</thinking>"
        "结论如下：\n"
        '{"reply":"摘要","summary":"这是摘要","keywords":["a","b"]}\n'
        "（完毕）"
    )
    obj = _extract_json_object(raw)
    assert obj and obj["reply"] == "摘要"
    assert obj["summary"] == "这是摘要"


def test_extract_json_returns_none_on_garbage():
    assert _extract_json_object("完全不是 JSON") is None
    assert _extract_json_object("") is None
    assert _extract_json_object("   ") is None
    assert _extract_json_object("```json\nnot json at all\n```") is None


# ---------- _build_prompt ----------
def test_build_prompt_request_json_only_with_schema():
    prompt = _provider()._build_prompt(AiRequest(ability="summarize", content="你好"))
    assert "只输出一个有效的 JSON 对象" in prompt
    assert '"reply"' in prompt  # schema 里有面向用户字段
    assert "能力：summarize" in prompt
    assert "你好" in prompt


# ---------- invoke（用假 HTTP 响应）
class _FakeResp:
    def __init__(self, body, status=200):
        self._body = body
        self.status_code = status

    def json(self):
        return self._body


class _FakeClient:
    def __init__(self, resp):
        self._resp = resp

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json=None, headers=None):
        self.called_url = url
        self.called_payload = json
        return self._resp


def _invoke_with(content, monkeypatch):
    raw = {"choices": [{"message": {"content": content}}]}
    mod = types.ModuleType("httpx")
    mod.Client = lambda *a, **k: _FakeClient(_FakeResp(raw))
    monkeypatch.setitem(sys.modules, "httpx", mod)
    return _provider().invoke(AiRequest(ability="summarize", content="笔记正文"))


def test_invoke_returns_clean_reply_text(monkeypatch):
    raw = '{"reply":"这篇笔记讲的是项目排期，重点是把上线时间提前两周。","summary":"项目排期摘要","keywords":["排期","上线"]}'
    resp = _invoke_with(raw, monkeypatch)
    assert resp.text == "这篇笔记讲的是项目排期，重点是把上线时间提前两周。"
    assert resp.data["summary"] == "项目排期摘要"


def test_invoke_falls_back_to_other_string_field_when_no_reply(monkeypatch):
    raw = '{"summary":"这是兜底摘要文本，不含 JSON 结构。","keywords":["a"]}'
    resp = _invoke_with(raw, monkeypatch)
    assert "兜底摘要文本" in resp.text
    assert "{" not in resp.text  # 不允许把 JSON 结构漏给用户


def test_invoke_strips_inline_reasoning_from_content(monkeypatch):
    raw = '<thinking>先看结构</thinking>{"reply":"整理好了，核心就两点。","content":"正文"}'
    resp = _invoke_with(raw, monkeypatch)
    assert resp.text == "整理好了，核心就两点。"
    assert "思考" not in resp.text


def test_invoke_polishes_leftover_json_when_reply_absent(monkeypatch):
    # 模型只回了 JSON、且无 reply：兜底摘要不应再暴露 JSON 结构
    raw = '{"summary":"内容很散，归成三类差不多。","keywords":["a","b","c"]}'
    resp = _invoke_with(raw, monkeypatch)
    assert "{" not in resp.text
    assert "内容很散" in resp.text


# ---------- _polish_readable ----------
def test_polish_readable_plain_text_passes_through():
    assert _polish_readable("你好，这是普通文本。", "") == "你好，这是普通文本。"


def test_polish_readable_flattens_leftover_json():
    out = _polish_readable('{"summary":"一句话摘要。","keywords":["a","b"]}', "")
    assert "一句话摘要" in out
    assert "{" not in out


# ---------- _remove_embedded_json ----------
def test_remove_embedded_json_strips_trailing_json_block():
    text = '这只是一条测试哦，看起来没实际内容～ {"summary":"xxx","keywords":["a"]}'
    assert _remove_embedded_json(text) == "这只是一条测试哦，看起来没实际内容～"


def test_remove_embedded_json_passes_plain_text():
    assert _remove_embedded_json("普通中文回复，没有 JSON。") == "普通中文回复，没有 JSON。"


def test_invoke_strips_json_squashed_into_reply_field(monkeypatch):
    # MiniMax 会把整段 JSON 塞进 reply 字段，必须剥掉，只留自然句
    raw = (
        '{"reply":"这只是一条测试用的文本哦，内容是\\u201c气运加身测试文本\\u201d，'
        '看起来没什么实际内容需要整理～ {\\"summary\\":\\"这是一条测试性文本\\",'
        '\\"keywords\\":[\\"测试\\"]}","summary":"这是一条测试性文本"}'
    )
    resp = _invoke_with(raw, monkeypatch)
    assert "{" not in resp.text
    assert "看起来没什么实际内容" in resp.text
    assert "keywords" not in resp.text