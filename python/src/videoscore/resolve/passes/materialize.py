"""materialize パス: 記号 source を実体へ、素材長を採取（仕様書 §3 の `auto` 前提）。

各 media 要素（video/audio/overlay）の source をプロバイダで実体化する。

- 記号スキーム（tts:// 等）は source を実体パスへ書き換える。
- `out` 未指定なら、素材本来の長さ（プロバイダの intrinsic_seconds）で **out を補完**する。
  これで「素材長」がドキュメント内に残り（案A・往復可能）、time_resolve は
  `auto = start + (out - in)` の算術だけで済む。

実測長が要るのに得られない（プロバイダ無し）場合は診断を立て、その要素はそのまま残す
（後段で未解決 auto として扱われる）。telop は source を持たないので対象外。
"""

from __future__ import annotations

from ...model import Scene, VideoScore
from ..context import Diagnostic, ResolveContext
from ..providers import SYMBOLIC_SCHEMES, parse_scheme

# source を持つ（実体化対象の）レーン
_MEDIA_LANES = ("video", "audio", "overlay")


def _needs(el) -> bool:
    """この要素に materialize の仕事が残っているか。"""
    if not getattr(el, "source", None):
        return False
    return parse_scheme(el.source) in SYMBOLIC_SCHEMES or el.out is None


class MaterializePass:
    name = "materialize"
    after = ("normalize",)

    def applicable(self, doc: VideoScore) -> bool:
        for lane in _MEDIA_LANES:
            for el in getattr(doc, lane) or []:
                if _needs(el):
                    return True
        for scene in doc.scenes:
            for lane in _MEDIA_LANES:
                for el in getattr(scene, lane):
                    if _needs(el):
                        return True
        return False

    def run(self, doc: VideoScore, ctx: ResolveContext) -> tuple[VideoScore, list[Diagnostic]]:
        diags: list[Diagnostic] = []

        def lane_updates(get_lane, label: str) -> dict:
            updates: dict = {}
            for lane in _MEDIA_LANES:
                elements = get_lane(lane)
                if elements:
                    updates[lane] = _materialize_lane(elements, lane, label, ctx, diags)
            return updates

        top_updates = lane_updates(lambda lane: getattr(doc, lane) or [], "$")

        new_scenes: list[Scene] = []
        for si, scene in enumerate(doc.scenes):
            label = f"$.scenes[{si}({scene.id})]"
            s_updates = lane_updates(lambda lane: getattr(scene, lane), label)
            new_scenes.append(scene.model_copy(update=s_updates) if s_updates else scene)

        new_doc = doc.model_copy(update={**top_updates, "scenes": new_scenes})
        return new_doc, diags


def _materialize_lane(elements, lane, label, ctx: ResolveContext, diags) -> list:
    new: list = []
    for idx, el in enumerate(elements):
        if not _needs(el):
            new.append(el)
            continue

        asset = ctx.providers.materialize(el.source, ctx)
        if asset is None:
            diags.append(
                Diagnostic(
                    "no-provider",
                    f"{label}.{lane}[{idx}]",
                    f"source '{el.source}' を実体化できるプロバイダが無い。",
                    "warning",
                )
            )
            new.append(el)
            continue

        updates: dict = {}
        if parse_scheme(el.source) in SYMBOLIC_SCHEMES:
            updates["source"] = asset.path
        if el.out is None and asset.intrinsic_seconds is not None:
            updates["out"] = float(asset.intrinsic_seconds)

        new.append(el.model_copy(update=updates) if updates else el)
    return new
