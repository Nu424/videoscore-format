"""normalize パス: `after` 脱糖・gap 畳み込み（仕様書 §3）。

- `start == "after"` … 先頭は 0（＋gap）、それ以外は直前の同レーン要素への `{ref:"<prev>.end"}`。
- 3スロット `["after","auto",{gap}]` … gap を offset に畳み込み、2スロットへ。
- 直前要素に id が無ければ合成 id を振る（参照のため）。合成 id は時間解決後に除去する
  （`time_resolve` 側で SYN_PREFIX のものを落とす）。

脱糖だけ。`auto`/`ref` の数値化は time_resolve の責務。
"""

from __future__ import annotations

from ...model import RefObject, Scene, VideoScore
from ..context import Diagnostic, ResolveContext

SYN_PREFIX = "__vsafter_"

_LANES = ("video", "audio", "telop", "overlay")


def _syn_id(lane: str, idx: int) -> str:
    return f"{SYN_PREFIX}{lane}_{idx}"


def _has_sugar(t) -> bool:
    return t[0] == "after" or t[1] == "after" or len(t) == 3


class NormalizePass:
    name = "normalize"
    after: tuple[str, ...] = ()

    def applicable(self, doc: VideoScore) -> bool:
        for lane in _LANES:
            for el in getattr(doc, lane) or []:
                if _has_sugar(el.t):
                    return True
        for scene in doc.scenes:
            for lane in _LANES:
                for el in getattr(scene, lane):
                    if _has_sugar(el.t):
                        return True
        return False

    def run(self, doc: VideoScore, ctx: ResolveContext) -> tuple[VideoScore, list[Diagnostic]]:
        diags: list[Diagnostic] = []

        def do_scope(get_lane, set_updates: dict, label: str) -> dict:
            updates: dict = {}
            for lane in _LANES:
                elements = get_lane(lane)
                if elements:
                    updates[lane] = _desugar_lane(elements, lane, label, diags)
            return updates

        # トップレベルレーン（§10.1）
        top_updates = do_scope(lambda lane: getattr(doc, lane) or [], {}, "$")

        # 各シーン
        new_scenes: list[Scene] = []
        for si, scene in enumerate(doc.scenes):
            label = f"$.scenes[{si}({scene.id})]"
            s_updates = do_scope(lambda lane: getattr(scene, lane), {}, label)
            new_scenes.append(scene.model_copy(update=s_updates) if s_updates else scene)

        new_doc = doc.model_copy(update={**top_updates, "scenes": new_scenes})
        return new_doc, diags


def _desugar_lane(elements, lane, label, diags) -> list:
    new: list = []
    for idx, el in enumerate(elements):
        t = el.t
        start, end = t[0], t[1]
        gap = t[2].gap if len(t) == 3 else None
        new_start, new_end = start, end

        if start == "after":
            if idx == 0:
                new_start = float(gap or 0.0)
            else:
                prev = new[idx - 1]
                if prev.id is None:
                    prev.id = _syn_id(lane, idx - 1)
                new_start = RefObject(ref=f"{prev.id}.end", offset=(gap or None))
        elif gap is not None:
            diags.append(
                Diagnostic(
                    "gap-without-after",
                    f"{label}.{lane}[{idx}]",
                    "gap は start='after' のときのみ有効。無視した。",
                    "warning",
                )
            )

        if end == "after":
            if idx == 0:
                diags.append(
                    Diagnostic(
                        "after-first-end",
                        f"{label}.{lane}[{idx}]",
                        "先頭要素の end='after' は参照先が無く解決できない。",
                        "error",
                    )
                )
            else:
                prev = new[idx - 1]
                if prev.id is None:
                    prev.id = _syn_id(lane, idx - 1)
                new_end = RefObject(ref=f"{prev.id}.end")

        new.append(el.model_copy(update={"t": (new_start, new_end)}))
    return new
