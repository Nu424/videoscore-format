"""スタイルカタログ（意味の層）（仕様書 §5）。

`style-catalog.json` は AI と検証器が読む「意味の層」。実装（recipes.<editor>.json）は
別ファイルなのでここでは扱わない。三層は id（結合キー）だけで握手する。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# 印を適用できるレーン
LaneName = Literal["video", "audio", "telop", "overlay"]


class StyleEntry(BaseModel):
    """カタログ1エントリ（意味の層）。`intent`/`feeling` は「いつ・どんな気分で使うか」。"""

    model_config = ConfigDict(extra="forbid")

    intent: str
    feeling: str
    appliesTo: list[LaneName]
    # params の型宣言（例: {"target": {"type": "string", "desc": "..."}}）。未使用なら null。
    params: dict[str, Any] | None = None
    example: str | None = None


class StyleCatalog(BaseModel):
    """`style-catalog.json` ルート（§5）。印 id → StyleEntry。"""

    model_config = ConfigDict(extra="forbid")

    styles: dict[str, StyleEntry]
