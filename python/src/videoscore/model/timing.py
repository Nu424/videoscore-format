"""時間語彙（仕様書 §3）。

VideoScore の時間スロット（`t` の start / end、`duration`）に書ける値を型化する。
脱糖（`after` → `{ref}`）も時間解決（`auto`・`ref` の確定）も**行わない**。
それらは解決スクリプト（videoscore.resolve）の責務であり、ここでは
「入力に書かれた素の形」をそのまま忠実に保持する。

仕様の鉄則（§3「循環を防ぐ鉄則」）だけは型に焼き込む:

    start は常に「具体 or 参照」。派生してよいのは end（＝尺）だけ。

→ start には `"auto"` を許さない（型レベルで除外）。end のみ `"auto"` 可。
"""

from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, ConfigDict


class RefObject(BaseModel):
    """他要素のマーク参照、またはレーン参照（§3）。

    例: `{ "ref": "v1.end", "offset": 0.2 }` / `{ "ref": "audio.end" }`
    参照先 id は同一シーン内に限る（可視範囲ルール）が、その検証は解決側で行う。
    """

    model_config = ConfigDict(extra="forbid")

    ref: str
    offset: float | None = None


class Gap(BaseModel):
    """`t` の第3要素として置くギャップ指定（§3「`["after", "auto", { "gap": 0.3 }]`」）。"""

    model_config = ConfigDict(extra="forbid")

    gap: float


# start に書ける値: 具体時刻 / "after"（直前要素の end ＝参照扱い）/ ref 参照。
# "auto"（自分の固有尺）は派生値なので start には許さない。
StartValue = Union[float, Literal["after"], RefObject]

# end に書ける値: 具体時刻 / "auto"（固有尺）/ "after" / ref 参照。
EndValue = Union[float, Literal["auto", "after"], RefObject]

# `duration`（シーン尺）に書ける値: 具体秒、または `audio.end` 等のレーン参照。
DurationValue = Union[float, RefObject]

# `t`（配置）: [start, end] か、ギャップ付き [start, end, gap]。
TwoSlot = tuple[StartValue, EndValue]
ThreeSlot = tuple[StartValue, EndValue, Gap]
TimeSpan = Union[ThreeSlot, TwoSlot]
