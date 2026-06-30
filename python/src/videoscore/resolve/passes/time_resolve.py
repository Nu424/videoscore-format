"""time_resolve パス: `auto`/`ref` を具体秒へ（仕様書 §3 の時間モデル）。

シーンは独立（ローカル時計）。`ref` は同一シーン内に限る（可視範囲）。各要素の start/end、
各レーンの `lane.end`（要素 end の最大）、`scene.duration` をスロットとし、メモ化 DFS で評価する。
訪問中スタックに戻ったら循環（§7）。

- start: 数値 / RefObject（`X.start|X.end|lane.end` ＋ offset）
- end  : 数値 / "auto"（= start + 固有尺。固有尺 = materialize 後の out - in）/ RefObject
- duration: 数値 / `lane.end` 参照
- トップレベルレーン（§10.1）は全シーン確定後、`scenes.end = Σ duration` を与えて同じ機構で解く

normalize が振った合成 id（SYN_PREFIX）は、解決後に除去する。
"""

from __future__ import annotations

from typing import Any

from ...model import RefObject, Scene, VideoScore
from ..context import Diagnostic, ResolveContext
from .normalize import SYN_PREFIX

_LANES = ("video", "audio", "telop", "overlay")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _intrinsic(el) -> float | None:
    """`auto` 用の固有尺。media は out - in（materialize で out 補完済み前提）。"""
    out = getattr(el, "out", None)
    if out is None:
        return None
    in_ = getattr(el, "in_", None) or 0.0
    return float(out) - float(in_)


def _is_unresolved_time(v) -> bool:
    return isinstance(v, RefObject) or v == "auto" or v == "after"


class TimeResolvePass:
    name = "resolve-time"
    after = ("materialize",)

    def applicable(self, doc: VideoScore) -> bool:
        def scope_has(get_lane, duration) -> bool:
            for lane in _LANES:
                for el in get_lane(lane):
                    if _is_unresolved_time(el.t[0]) or _is_unresolved_time(el.t[1]):
                        return True
                    if el.id and el.id.startswith(SYN_PREFIX):
                        return True
            return isinstance(duration, RefObject)

        if scope_has(lambda lane: getattr(doc, lane) or [], None):
            return True
        for scene in doc.scenes:
            if scope_has(lambda lane: getattr(scene, lane), scene.duration):
                return True
        return False

    def run(self, doc: VideoScore, ctx: ResolveContext) -> tuple[VideoScore, list[Diagnostic]]:
        diags: list[Diagnostic] = []

        scene_updates: list[dict] = []
        durations: list[float | None] = []
        for si, scene in enumerate(doc.scenes):
            label = f"$.scenes[{si}({scene.id})]"
            lanes = {lane: list(getattr(scene, lane)) for lane in _LANES}
            r = _ScopeResolver(lanes, externals={}, label=label, diags=diags)
            updates = _rewrite_scope(r, lanes)
            rd = _resolve_duration(r, scene.duration, label)
            if rd is not None:
                updates["duration"] = rd
            durations.append(rd)
            scene_updates.append(updates)

        scenes_end = sum(durations) if all(d is not None for d in durations) else None

        # トップレベルレーン（§10.1）
        top_updates: dict = {}
        if any(getattr(doc, lane) for lane in _LANES):
            lanes = {lane: list(getattr(doc, lane) or []) for lane in _LANES}
            externals = {"scenes": scenes_end} if scenes_end is not None else {}
            r = _ScopeResolver(lanes, externals=externals, label="$", diags=diags)
            top_updates = _rewrite_scope(r, lanes)

        new_scenes = [
            scene.model_copy(update=upd) if upd else scene
            for scene, upd in zip(doc.scenes, scene_updates)
        ]
        new_doc = doc.model_copy(update={**top_updates, "scenes": new_scenes})
        return new_doc, diags


def _resolve_duration(r: "_ScopeResolver", duration, label) -> float | None:
    if _is_number(duration):
        return float(duration)
    if isinstance(duration, RefObject):
        target = r.parse_ref(duration.ref, ("duration",))
        if target is None:
            return None
        base = r.value(target)
        if base is None:
            return None
        return base + (duration.offset or 0.0)
    return None


def _rewrite_scope(r: "_ScopeResolver", lanes: dict) -> dict:
    """各レーン要素の t を数値へ書き戻し、合成 id を除去した updates を返す。"""
    updates: dict = {}
    for lane, elements in lanes.items():
        new_list = []
        changed = False
        for idx, el in enumerate(elements):
            ns = r.value(("el", lane, idx, "start"))
            ne = r.value(("el", lane, idx, "end"))
            el_update: dict = {}
            if ns is not None and ne is not None and (ns, ne) != (el.t[0], el.t[1]):
                el_update["t"] = (ns, ne)
            if el.id and el.id.startswith(SYN_PREFIX):
                el_update["id"] = None
            if el_update:
                changed = True
                new_list.append(el.model_copy(update=el_update))
            else:
                new_list.append(el)
        if changed:
            updates[lane] = new_list
    return updates


class _ScopeResolver:
    """1スコープ（シーン or トップレベル）の時間スロットを解決する。"""

    def __init__(self, lanes: dict, externals: dict, label: str, diags: list):
        self.lanes = lanes
        self.externals = externals  # name -> 値（suffix "end" 扱い。例 {"scenes": 12.0}）
        self.label = label
        self.diags = diags
        self.memo: dict = {}
        self.visiting: set = set()
        self.id_map: dict = {}
        for lane, els in lanes.items():
            for i, el in enumerate(els):
                if el.id is not None:
                    self.id_map[el.id] = (lane, i)

    def _loc(self, slot) -> str:
        tag = slot[0]
        if tag == "el":
            return f"{self.label}.{slot[1]}[{slot[2]}].{slot[3]}"
        if tag in ("lane", "ext"):
            return f"{self.label}.{slot[1]}.end"
        return self.label

    def value(self, slot):
        if slot in self.memo:
            return self.memo[slot]
        if slot in self.visiting:
            self.diags.append(
                Diagnostic("cycle", self._loc(slot), "時間依存に循環がある（DAG が解けない）", "error")
            )
            return None
        self.visiting.add(slot)
        result = self._compute(slot)
        self.visiting.discard(slot)
        self.memo[slot] = result
        return result

    def _compute(self, slot):
        tag = slot[0]
        if tag == "ext":
            return self.externals.get(slot[1])
        if tag == "lane":
            name = slot[1]
            els = self.lanes.get(name, [])
            if not els:
                self.diags.append(
                    Diagnostic("empty-lane-ref", self.label, f"レーン '{name}' は空で end を持たない", "error")
                )
                return None
            ends = [self.value(("el", name, i, "end")) for i in range(len(els))]
            ends = [e for e in ends if e is not None]
            return max(ends) if ends else None

        _, lane, idx, which = slot
        el = self.lanes[lane][idx]
        if which == "start":
            return self._resolve_value(el.t[0], slot)
        # end
        v = el.t[1]
        if v == "auto":
            s = self.value(("el", lane, idx, "start"))
            if s is None:
                return None
            intr = _intrinsic(el)
            if intr is None:
                self.diags.append(
                    Diagnostic(
                        "unresolved-auto",
                        self._loc(slot),
                        "auto の固有尺が決まらない（out/in 不明・materialize 未到達）",
                        "warning",
                    )
                )
                return None
            return s + intr
        return self._resolve_value(v, slot)

    def _resolve_value(self, v, slot):
        if _is_number(v):
            return float(v)
        if isinstance(v, RefObject):
            target = self.parse_ref(v.ref, slot)
            if target is None:
                return None
            base = self.value(target)
            if base is None:
                return None
            return base + (v.offset or 0.0)
        self.diags.append(
            Diagnostic("unexpected-time", self._loc(slot), f"start に解決不能な値: {v!r}", "error")
        )
        return None

    def parse_ref(self, ref: str, slot):
        if "." not in ref:
            self.diags.append(
                Diagnostic("invalid-ref", self._loc(slot), f"参照 '{ref}' が '<id>.start|end' 形式でない", "error")
            )
            return None
        name, suffix = ref.rsplit(".", 1)
        if suffix not in ("start", "end"):
            self.diags.append(
                Diagnostic("invalid-ref", self._loc(slot), f"参照サフィックス '{suffix}' は start|end のみ", "error")
            )
            return None
        if name in self.externals:
            if suffix != "end":
                self.diags.append(
                    Diagnostic("invalid-ref", self._loc(slot), f"'{name}' は end のみ参照可", "error")
                )
                return None
            return ("ext", name)
        if name in self.lanes:
            if suffix != "end":
                self.diags.append(
                    Diagnostic("invalid-ref", self._loc(slot), f"レーン '{name}' は end のみ参照可", "error")
                )
                return None
            return ("lane", name)
        if name in self.id_map:
            lane, idx = self.id_map[name]
            return ("el", lane, idx, suffix)
        self.diags.append(
            Diagnostic("dangling-ref", self._loc(slot), f"参照先 '{ref}' が同一スコープに無い", "error")
        )
        return None
