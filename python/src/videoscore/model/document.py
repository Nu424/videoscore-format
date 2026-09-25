"""ドキュメント全体（仕様書 §1, §8, §10.1）。

VideoScore = meta + （任意の）トップレベルレーン + scenes（シーンの直列リスト）。

トップレベルレーン（§10.1）はシーンを跨ぐ要素（全体BGM等）の置き場。仕様上は
「保留（推奨案）」だが、SKILL.md が実際に生成するため optional で型化しておく。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .elements import AudioElement, OverlayElement, TelopElement, VideoElement
from .timing import DurationValue

# 現行の VideoScore 形式のバージョン（semver 風の文字列）。`meta.schemaVersion` に書く値。
# 形式（pydantic モデル）を変えたらここも上げる。0.x の間は minor を互換の区切りとする。
#   0.1.0 … 初版（scenes + 4レーン + 時間語彙 + トップレベルレーン）
#   0.2.0 … crop（video/overlay）・annotations（全要素と scene）・meta.schemaVersion を追加
SCHEMA_VERSION = "0.2.0"


class Meta(BaseModel):
    """ドキュメントのメタ情報（§8）。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    fps: float | None = None
    size: tuple[int, int] | None = None
    styleCatalog: str | None = None
    schemaVersion: str | None = Field(
        default=None,
        description=(
            "この文書が準拠する VideoScore 形式のバージョン（例 \"0.2.0\"）。"
            "部品間（生成・解決・書き出し・プレイヤー）の互換確認に使う。省略可。"
        ),
    )


class Scene(BaseModel):
    """1シーン＝1つのローカル時計（§1）。4レーンを持つ唯一の器。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    duration: DurationValue
    video: list[VideoElement] = []
    audio: list[AudioElement] = []
    telop: list[TelopElement] = []
    overlay: list[OverlayElement] = []
    annotations: dict[str, Any] | None = Field(
        default=None,
        description="自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。",
    )


class VideoScore(BaseModel):
    """VideoScore ドキュメントのルート（§1, §8）。"""

    model_config = ConfigDict(extra="forbid")

    meta: Meta | None = None

    # トップレベル（シーン跨ぎ）レーン（§10.1）。原点は動画先頭、`scenes.end` を参照可能。
    video: list[VideoElement] | None = None
    audio: list[AudioElement] | None = None
    telop: list[TelopElement] | None = None
    overlay: list[OverlayElement] | None = None

    scenes: list[Scene]

    def to_json_dict(self, *, minimal: bool = True) -> dict:
        """JSON 出力用の dict を返す。

        minimal=True では None フィールドと空レーンを省き、`in` 等のエイリアスで出す
        （入力に近い素の形を保つ）。
        """
        data = self.model_dump(by_alias=True, exclude_none=True)
        if minimal:
            data = _drop_empty_lanes(data)
        return data


_LANE_KEYS = ("video", "audio", "telop", "overlay")


def _drop_empty_lanes(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _LANE_KEYS and isinstance(v, list) and not v:
                continue
            out[k] = _drop_empty_lanes(v)
        return out
    if isinstance(obj, list):
        return [_drop_empty_lanes(x) for x in obj]
    return obj
