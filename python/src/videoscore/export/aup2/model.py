"""`.aup2` の薄い中間モデル（自前エミッタ用）。

AviUtl2 のプロジェクト構造を最小限の dataclass で表す。`aviutl2-api` に依存せず、
`emit.to_text` でそのまま `.aup2` テキスト（CRLF/UTF-8）へ落とす。プロパティ値は
数値（2桁小数で整形）／文字列（フォント名・6桁 hex 色・合成モード名など）を素で持つ。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Aup2Effect", "Aup2Object", "Aup2Scene", "Aup2Project"]


@dataclass
class Aup2Effect:
    """1つのエフェクト（`[K.j]`）。props は挿入順で出力される。"""

    name: str
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class Aup2Object:
    """タイムライン上の1オブジェクト（`[K]` ＋ そのエフェクト群）。"""

    layer: int
    frame_start: int
    frame_end: int
    effects: list[Aup2Effect] = field(default_factory=list)


@dataclass
class Aup2Scene:
    """単一シーン（`[scene.0]`）。v1 は全要素をここへ連結する。"""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    audio_rate: int = 44100
    name: str = "Root"
    objects: list[Aup2Object] = field(default_factory=list)


@dataclass
class Aup2Project:
    """`.aup2` プロジェクト全体。"""

    scene: Aup2Scene = field(default_factory=Aup2Scene)
    file_path: str = ""
    version: int = 2001901

    def to_text(self) -> str:
        from .emit import to_text

        return to_text(self)

    def dump(self, path: str) -> None:
        from .emit import write_file

        write_file(self, path)
