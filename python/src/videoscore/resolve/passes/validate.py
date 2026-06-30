"""validate-resolved パス: 解決済み形の不変条件を表明（仕様書 §7）。

解決済み VideoScore で初めて完全に効く検査をここで行う。doc は変更しない（診断のみ返す）。

- 完全具体: 全 t の start/end・全 duration が数値（auto/ref/after の残存＝部分解決）。
- 実体化済み: 記号スキーム source（tts:// 等）が残っていない。
- 時間範囲: `0 ≤ start < end`、`end ≤ duration`（フィラー超過は warning）。
"""

from __future__ import annotations

from typing import Any

from ...model import RefObject, VideoScore
from ..context import Diagnostic, ResolveContext
from ..providers import SYMBOLIC_SCHEMES, parse_scheme

_LANES = ("video", "audio", "telop", "overlay")


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _unresolved_reason(v) -> str | None:
    if isinstance(v, RefObject):
        return f"未解決の参照 {{ref:{v.ref!r}}}"
    if v == "auto":
        return "未解決の auto"
    if v == "after":
        return "未解決の after"
    if not _is_number(v):
        return f"非数値 {v!r}"
    return None


class ValidateResolvedPass:
    name = "validate-resolved"
    after = ("resolve-time",)

    def applicable(self, doc: VideoScore) -> bool:
        return True  # 検査は常に走らせてよい（doc を変えない）

    def run(self, doc: VideoScore, ctx: ResolveContext) -> tuple[VideoScore, list[Diagnostic]]:
        diags: list[Diagnostic] = []

        def check_scope(get_lane, duration, label: str) -> None:
            dur = float(duration) if _is_number(duration) else None
            if duration is not None and dur is None:
                diags.append(
                    Diagnostic("not-resolved", f"{label}.duration", "duration が数値に解決されていない", "error")
                )
            for lane in _LANES:
                for i, el in enumerate(get_lane(lane)):
                    where = f"{label}.{lane}[{i}]"
                    start, end = el.t[0], el.t[1]
                    rs, re = _unresolved_reason(start), _unresolved_reason(end)
                    if rs:
                        diags.append(Diagnostic("not-resolved", f"{where}.start", rs, "error"))
                    if re:
                        diags.append(Diagnostic("not-resolved", f"{where}.end", re, "error"))
                    if rs is None and re is None:
                        if start < 0:
                            diags.append(Diagnostic("range", where, f"start < 0 ({start})", "error"))
                        if not start < end:
                            diags.append(
                                Diagnostic("range", where, f"start < end を満たさない [{start}, {end}]", "error")
                            )
                        if dur is not None and end > dur:
                            diags.append(
                                Diagnostic(
                                    "overrun",
                                    where,
                                    f"end {end} がシーン尺 {dur} を超過（フィラー超過＝レシピ領域）",
                                    "warning",
                                )
                            )
                    src = getattr(el, "source", None)
                    if src and parse_scheme(src) in SYMBOLIC_SCHEMES:
                        diags.append(
                            Diagnostic("not-materialized", where, f"記号 source が残存: '{src}'", "warning")
                        )

        check_scope(lambda lane: getattr(doc, lane) or [], None, "$")
        for si, scene in enumerate(doc.scenes):
            check_scope(lambda lane: getattr(scene, lane), scene.duration, f"$.scenes[{si}({scene.id})]")

        return doc, diags
