"""形式コンバータ共通の部品（時間換算・シーン連結・レイヤー割当）。

各エディタ形式に依存しない汎用ロジックを置く。`videoscore.export.aup2` が使うほか、
将来の OTIO 等コンバータでも共有する。診断は解決系と同じ `Diagnostic` 型で統一する
（例外でなくリストで返す流儀）。
"""

from __future__ import annotations

from ..model import Scene, VideoScore
from ..resolve.context import Diagnostic  # 診断型は解決系と共通化（re-export）

__all__ = ["Diagnostic", "sec_to_frame", "scene_offsets", "span_to_frames", "LayerAllocator"]


def sec_to_frame(sec: float, fps: float) -> int:
    """秒を最も近いフレーム番号へ丸める（換算の唯一の入口）。"""
    return round(sec * fps)


def span_to_frames(
    start_sec: float, end_sec: float, fps: float
) -> tuple[tuple[int, int], bool]:
    """[start, end) 秒を inclusive なフレーム範囲 ((start_f, end_f), degenerate) にする。

    end 側は `round(end·fps) - 1`。隣接要素（シーン連結・モンタージュ）が 1 フレームも
    重ならず隙間なく連なる。尺が 0 以下に潰れる退化ケースは end_f = start_f（最短1フレーム）。
    退化したかどうかは第2返り値で知らせる（呼び側が診断にする）。
    """
    start_f = sec_to_frame(start_sec, fps)
    end_f = sec_to_frame(end_sec, fps) - 1
    if end_f < start_f:
        return (start_f, start_f), True
    return (start_f, end_f), False


def scene_offsets(scenes: list[Scene]) -> list[float]:
    """各シーンの開始秒（直前までのシーン尺の累積）を返す。

    解決済み VideoScore を前提とし、`duration` は数値であるべき。数値でなければ
    0 とみなして続行する（呼び側が別途 not-resolved 診断を出す）。
    """
    offsets: list[float] = []
    acc = 0.0
    for scene in scenes:
        offsets.append(acc)
        dur = scene.duration
        acc += float(dur) if _is_number(dur) else 0.0
    return offsets


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class LayerAllocator:
    """フレーム区間を衝突しないレイヤーへ貪欲割当する（区間分割）。

    AviUtl2 の「同一レイヤー・同一時刻に複数オブジェクト不可」を機械的に満たす。
    `floor` はレーンごとの下限レイヤー（描画順＝奥/手前の制御に使う）。要求区間が
    floor 以上で時間の重ならない最小レイヤーへ入る。時間が重ならなければ同一レイヤーを
    再利用し、重なれば上のレイヤーへ自動退避する。全レーンで同じインスタンスを共有すれば
    帯を跨ぐ衝突も起きない。
    """

    def __init__(self) -> None:
        self._by_layer: dict[int, list[tuple[int, int]]] = {}

    def allocate(self, start_f: int, end_f: int, floor: int = 0) -> int:
        layer = floor
        while True:
            occ = self._by_layer.setdefault(layer, [])
            if all(not (start_f <= oe and os <= end_f) for os, oe in occ):
                occ.append((start_f, end_f))
                return layer
            layer += 1
