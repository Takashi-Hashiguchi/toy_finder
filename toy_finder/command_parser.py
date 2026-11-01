"""文章の指示（例：「青いボールを探して」）を、探す色に変換する。

LLM（Claude）で意味を読み取り、決まった形（JSON）で返させる。
APIキーがない・通信できないなどでLLMが使えないときは、キーワードで判定する。
ROSに依存しないので、単体でテストできる。
"""
import json
from dataclasses import dataclass
from typing import Optional

from toy_finder.detector import COLOR_RANGES

MODEL = "claude-opus-5-5"

# LLMに選ばせる答え。色のほかに「止まって」と「わからない」を用意する
CHOICES = list(COLOR_RANGES) + ["stop", "unknown"]

SYSTEM_PROMPT = (
    "あなたは家庭用のお手伝いロボットの指示係です。"
    "ロボットはカメラで色の付いたボール（おもちゃ）を探して近づくことができます。"
    f"探せる色は {', '.join(COLOR_RANGES)} です。"
    "人からの文章を読み、ロボットが探すべき色を1つ選んでください。"
    "止まってほしい・やめてほしいという意味なら stop を選びます。"
    "探せる色が読み取れない、または頼まれた内容がボール探しでない場合は unknown を選びます。"
    "reply には、ロボットが人に返す短い日本語の一言（20文字程度）を書いてください。"
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "color": {"type": "string", "enum": CHOICES},
        "reply": {"type": "string"},
    },
    "required": ["color", "reply"],
    "additionalProperties": False,
}

# LLMが使えないときのためのキーワード
KEYWORDS = {
    "stop": ["止ま", "とま", "やめ", "ストップ", "stop"],
    "red": ["赤", "あか", "アカ", "レッド", "red"],
    "blue": ["青", "あお", "アオ", "ブルー", "blue"],
    "green": ["緑", "みどり", "ミドリ", "グリーン", "green"],
    "yellow": ["黄", "きいろ", "キイロ", "イエロー", "yellow"],
}

REPLIES = {
    "stop": "止まります",
    "red": "赤いボールを探します",
    "blue": "青いボールを探します",
    "green": "緑のボールを探します",
    "yellow": "黄色いボールを探します",
    "unknown": "探す色がわかりませんでした",
}


@dataclass
class ParsedCommand:
    color: str  # COLOR_RANGES のどれか、"stop"、"unknown"
    reply: str  # ロボットが返す一言
    source: str  # "llm" か "keyword"（どちらで判定したか）


def parse_by_keyword(text: str) -> ParsedCommand:
    """キーワードで判定する（LLMが使えないときの予備）。"""
    lowered = text.lower()
    for color, words in KEYWORDS.items():
        if any(word.lower() in lowered for word in words):
            return ParsedCommand(color, REPLIES[color], "keyword")
    return ParsedCommand("unknown", REPLIES["unknown"], "keyword")


def parse_by_llm(text: str, client) -> ParsedCommand:
    """Claudeで判定する。失敗したら例外を投げる。"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        # 単純な分類なので考える量は少なくてよい
        output_config={
            "effort": "low",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        # 安全判定で断られた場合に、別のモデルで自動的にやり直す
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("LLMが回答を断りました")
    answer = next(block.text for block in response.content if block.type == "text")
    data = json.loads(answer)
    if data["color"] not in CHOICES:
        raise ValueError(f"想定外の答え: {data['color']}")
    return ParsedCommand(data["color"], data["reply"], "llm")


def parse_command(text: str, client=None, logger=None) -> ParsedCommand:
    """文章を色に変換する。client があればLLM、なければ・失敗したらキーワードで判定する。"""
    if client is not None:
        try:
            return parse_by_llm(text, client)
        except Exception as error:  # 通信エラーなどでも止まらないようにする
            if logger is not None:
                logger(f"LLMが使えなかったのでキーワードで判定します: {error}")
    return parse_by_keyword(text)


def make_client(logger=None) -> Optional[object]:
    """Claudeのクライアントを作る。ライブラリやAPIキーがなければ None を返す。"""
    try:
        import anthropic
    except ImportError:
        if logger is not None:
            logger("anthropic ライブラリがないので、キーワードで判定します（pip install anthropic）")
        return None
    try:
        # Ubuntu 22.04 に入っている古い brotli だと、圧縮された応答の展開で失敗する。
        # brotli 圧縮を使わないよう、受け取る圧縮形式を gzip / deflate に限定する。
        return anthropic.Anthropic(default_headers={"Accept-Encoding": "gzip, deflate"})
    except Exception as error:
        if logger is not None:
            logger(f"APIキーが見つからないので、キーワードで判定します: {error}")
        return None
