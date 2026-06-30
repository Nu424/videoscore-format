"""レーン要素（仕様書 §2）。

全レーンは「共通の骨 + レーン固有の差分」で表す。

    共通の骨: { id?, t, style?, params?, marks? }
    video   : + source, in?, out?
    audio   : + source, in?, out?, role
    overlay : + source, in?, out?
    telop   : + text
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .timing import TimeSpan

# audio の role（§6）
AudioRole = Literal["voice", "se", "music", "ambient"]


class BaseElement(BaseModel):
    """全レーン共通の骨。`id` は他から参照される要素にのみ振る。"""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str | None = None
    t: TimeSpan
    style: str | None = None
    params: dict[str, Any] | None = None
    marks: list[str] | None = None

    @model_validator(mode="after")
    def _check_concrete_span(self) -> "BaseElement":
        """両端が具体数値のときだけ `0 <= start < end` を検査する（§7 時間範囲）。

        start/end が auto・after・ref のときは尺が未確定なので検査しない
        （それらの解決・範囲検査は解決スクリプトの責務）。
        シーン尺 `end <= duration` も同様にシーン文脈が要るのでここでは見ない。
        """
        start, end = self.t[0], self.t[1]
        if _is_number(start) and start < 0:
            raise ValueError(f"start must be >= 0, got {start!r}")
        if _is_number(start) and _is_number(end) and not start < end:
            raise ValueError(f"t must satisfy start < end, got [{start!r}, {end!r}]")
        return self


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class _MediaElement(BaseElement):
    """素材（source）を持つレーンの共通部分。`in`/`out` は素材内トリム。"""

    source: str
    # `in` は Python 予約語のため、フィールド名は in_ / 入出力エイリアスは "in"。
    in_: float | None = Field(default=None, alias="in")
    out: float | None = None


class VideoElement(_MediaElement):
    """映像クリップ（§2）。"""


class OverlayElement(_MediaElement):
    """画像/動画オーバーレイ（PiP）（§2）。"""


class AudioElement(_MediaElement):
    """音声（§2, §6）。role で voice/se/music/ambient を区別する。"""

    role: AudioRole


class TelopElement(BaseElement):
    """テロップ（§2）。表示文字 text を持ち、source/in/out は持たない。"""

    text: str
