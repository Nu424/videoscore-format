"""レーン要素（仕様書 §2）。

全レーンは「共通の骨 + レーン固有の差分」で表す。

    共通の骨: { id?, t, style?, params?, marks?, annotations? }
    video   : + source, in?, out?, crop?
    audio   : + source, in?, out?, role
    overlay : + source, in?, out?, crop?
    telop   : + text

`annotations` は根拠の参照・候補 ID・メモ等を置く自由な object。解決（resolve）と
書き出し（export）はこれを**解釈しない**（素通しで保持するだけ）。時間アンカーの
`marks` とは役割が違うので流用しない。

`crop` は元フレームのうち「どこを映すか」を 0〜1 の比率 `[x, y, w, h]` で持つ（静的のみ）。
内容に依存するデータなので style/params ではなく要素の項目にする。切り出した領域を
フレームへどう収めるか（拡大・余白・位置）はスタイル（layout 系の印）とレシピが決める。
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

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
    annotations: dict[str, Any] | None = Field(
        default=None,
        description=(
            "自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。"
            "時間アンカーには marks を使い、ここには置かない。"
        ),
    )

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


# crop の各成分: 位置 x/y は 0〜1、大きさ w/h は (0, 1]。
_Frac = Annotated[float, Field(ge=0, le=1)]
_PosFrac = Annotated[float, Field(gt=0, le=1)]

# `crop`: 元フレームに対する比率 [x, y, w, h]（左上原点）。
Crop = tuple[_Frac, _Frac, _PosFrac, _PosFrac]


class _VisualMediaElement(_MediaElement):
    """画を持つ media レーン（video/overlay）の共通部分。`crop` を持てる。"""

    crop: Crop | None = Field(
        default=None,
        description=(
            "元フレームのうち映す領域 [x, y, w, h]（左上原点・0〜1 の比率、静的）。"
            "x+w<=1, y+h<=1。領域をフレームへどう収めるかは style（layout 系）が決める。"
        ),
    )

    @model_validator(mode="after")
    def _check_crop(self) -> "_VisualMediaElement":
        """`crop` が元フレームの内側に収まっているか（x+w<=1, y+h<=1）を検査する。"""
        if self.crop is not None:
            x, y, w, h = self.crop
            eps = 1e-9  # 0.1+0.9 等の浮動小数誤差を許す
            if x + w > 1 + eps:
                raise ValueError(f"crop must satisfy x + w <= 1, got x={x!r}, w={w!r}")
            if y + h > 1 + eps:
                raise ValueError(f"crop must satisfy y + h <= 1, got y={y!r}, h={h!r}")
        return self


class VideoElement(_VisualMediaElement):
    """映像クリップ（§2）。"""


class OverlayElement(_VisualMediaElement):
    """画像/動画オーバーレイ（PiP）（§2）。"""


class AudioElement(_MediaElement):
    """音声（§2, §6）。role で voice/se/music/ambient を区別する。"""

    role: AudioRole


class TelopElement(BaseElement):
    """テロップ（§2）。表示文字 text を持ち、source/in/out は持たない。"""

    text: str
