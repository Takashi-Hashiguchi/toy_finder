"""command_parser.py の単体テスト。ROSもネットワークも使わない。  実行: python3 -m pytest test/"""
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from toy_finder.command_parser import parse_by_keyword, parse_command  # noqa: E402


class FakeMessages:
    """Claude の代わりに決まった答えを返す。"""

    def __init__(self, answer=None, stop_reason="end_turn", error=None):
        self.answer = answer
        self.stop_reason = stop_reason
        self.error = error
        self.last_request = None

    def create(self, **kwargs):
        self.last_request = kwargs
        if self.error is not None:
            raise self.error
        block = SimpleNamespace(type="text", text=json.dumps(self.answer, ensure_ascii=False))
        return SimpleNamespace(stop_reason=self.stop_reason, content=[block])


def fake_client(**kwargs):
    return SimpleNamespace(messages=FakeMessages(**kwargs))


def test_keyword_finds_each_color():
    assert parse_by_keyword("赤いボールを探して").color == "red"
    assert parse_by_keyword("あおいの持ってきて").color == "blue"
    assert parse_by_keyword("グリーンのおもちゃ").color == "green"
    assert parse_by_keyword("黄色いのどこ？").color == "yellow"


def test_keyword_stop_and_unknown():
    assert parse_by_keyword("止まって").color == "stop"
    assert parse_by_keyword("こんにちは").color == "unknown"


def test_uses_llm_answer_when_available():
    client = fake_client(answer={"color": "blue", "reply": "青いボールを探します"})
    result = parse_command("空みたいな色のボールを探して", client)
    assert result.color == "blue"
    assert result.source == "llm"
    request = client.messages.last_request
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["format"]["type"] == "json_schema"


def test_falls_back_to_keyword_when_llm_fails():
    client = fake_client(error=ConnectionError("ネットワークなし"))
    result = parse_command("赤いボールを探して", client)
    assert result.color == "red"
    assert result.source == "keyword"


def test_falls_back_on_refusal():
    client = fake_client(answer={"color": "red", "reply": ""}, stop_reason="refusal")
    assert parse_command("緑を探して", client).source == "keyword"


def test_rejects_unexpected_llm_answer():
    client = fake_client(answer={"color": "purple", "reply": "?"})
    result = parse_command("赤を探して", client)
    assert result.source == "keyword" and result.color == "red"


def test_without_client_uses_keyword():
    assert parse_command("青を探して", None).source == "keyword"
