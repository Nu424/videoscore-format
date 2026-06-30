"""ドキュメント全体（仕様書 §1, §8, §10.1）。

VideoScore = meta + （任意の）トップレベルレーン + scenes（シーンの直列リスト）。

トップレベルレーン（§10.1）はシーンを跨ぐ要素（全体BGM等）の置き場。仕様上は
「保留（推奨案）」だが、SKILL.md が実際に生成するため optional で型化しておく。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .elements import AudioElement, OverlayElement, TelopElement, VideoElement
from .timing import DurationValue


class Meta(BaseModel):
    """ドキュメントのメタ情報（§8）。"""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    fps: float | None = None
    size: tuple[int, int] | None = None
    styleCatalog: str | None = None


class Scene(BaseModel):
    """1シーン＝1つのローカル時計（§1）。4レーンを持つ唯一の器。"""

    model_config = ConfigDict(extra="forbid")

    id: str
    duration: DurationValue
    video: list[VideoElement] = []
    audio: list[AudioElement] = []
    telop: list[TelopElement] = []
    overlay: list[OverlayElement] = []


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
