"""`.aup2` テキストのシリアライズ（自前エミッタ）。

出力は **UTF-8 BOMなし・CRLF**。構造は `[project]` → `[scene.0]` → 各オブジェクト
`[K]`（`layer`/`frame`）→ 各エフェクト `[K.j]`（`effect.name` ＋ プロパティ）。
プロパティ値は bool→`1/0`、数値→2桁小数、文字列→素（6桁 hex 色・フォント名・
既に整形済みのアニメ値文字列などをそのまま通す）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .model import Aup2Project

__all__ = ["to_text", "write_file", "format_value"]

_LINE_ENDING = "\r\n"

# [scene.0] のうち、全体設定以外の固定行（EmptyProject.aup2 準拠）。
_SCENE_TAIL = [
    "cursor.frame=0",
    "cursor.layer=0",
    "display.frame=0",
    "display.layer=0",
    "display.zoom=10000",
    "display.order=0",
    "display.camera=",
    "display.grid.x=16,-16",
    "display.grid.y=16,-16",
    "display.grid.width=200",
    "display.grid.height=200",
    "display.grid.step=200.000000",
    "display.grid.range=10000.000000",
    "display.tempo.bpm=120.000000",
    "display.tempo.beat=4",
    "display.tempo.offset=0.000000",
]


def format_value(value: Any) -> str:
    """プロパティ値を .aup2 の1トークンへ整形する。"""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return f"{float(value):.2f}"
    return str(value)


def _int_if_whole(v: float) -> int | float:
    return int(v) if float(v).is_integer() else v


def to_text(project: "Aup2Project") -> str:
    sc = project.scene
    lines: list[str] = []

    lines.append("[project]")
    lines.append(f"version={project.version}")
    lines.append(f"file={project.file_path}")
    lines.append("display.scene=0")

    lines.append("[scene.0]")
    lines.append("scene=0")
    lines.append(f"name={sc.name}")
    lines.append(f"video.width={int(sc.width)}")
    lines.append(f"video.height={int(sc.height)}")
    lines.append(f"video.rate={_int_if_whole(sc.fps)}")
    lines.append("video.scale=1")
    lines.append(f"audio.rate={int(sc.audio_rate)}")
    lines.extend(_SCENE_TAIL)

    for i, obj in enumerate(sc.objects):
        lines.append(f"[{i}]")
        lines.append(f"layer={obj.layer}")
        lines.append(f"frame={obj.frame_start},{obj.frame_end}")
        for j, eff in enumerate(obj.effects):
            lines.append(f"[{i}.{j}]")
            lines.append(f"effect.name={eff.name}")
            for key, val in eff.props.items():
                lines.append(f"{key}={format_value(val)}")

    return _LINE_ENDING.join(lines) + _LINE_ENDING


def write_file(project: "Aup2Project", path: str) -> None:
    """UTF-8 BOMなし・CRLF で書き出す（改行変換を無効化して CRLF を維持）。"""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(to_text(project))
