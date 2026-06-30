"""解決パイプラインの実行器。

各「解決」は VideoScore → (VideoScore, [Diagnostic]) のパス。パスは `after` で先行依存を
宣言し、実行器がトポロジカルソートして順に回す（時間 ref の DAG と相似）。

`applicable()` が「まだ仕事が残っているか」を返すので、`resolve(resolve(x)) == resolve(x)`
（べき等）。`until=` で途中段階の出力も取れる。どの段階の出力も妥当な VideoScore。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..model import VideoScore
from .context import Diagnostic, ResolveContext, default_context


@runtime_checkable
class Pass(Protocol):
    """解決の単位。ドキュメントを一段だけ清書方向へ進める。"""

    name: str
    after: tuple[str, ...]

    def applicable(self, doc: VideoScore) -> bool: ...

    def run(self, doc: VideoScore, ctx: ResolveContext) -> tuple[VideoScore, list[Diagnostic]]: ...


def topo_order(passes: list[Pass]) -> list[Pass]:
    """`after` 依存に従ってパスを並べる。循環依存はエラー。"""
    by_name = {p.name: p for p in passes}
    ordered: list[Pass] = []
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(p: Pass) -> None:
        if p.name in done:
            return
        if p.name in visiting:
            raise ValueError(f"パス依存に循環があります: {p.name}")
        visiting.add(p.name)
        for dep in p.after:
            if dep in by_name:  # 未登録の依存は無視（部分パイプラインを許す）
                visit(by_name[dep])
        visiting.discard(p.name)
        done.add(p.name)
        ordered.append(p)

    for p in passes:
        visit(p)
    return ordered


def resolve(
    doc: VideoScore,
    ctx: ResolveContext | None = None,
    *,
    passes: list[Pass] | None = None,
    until: str | None = None,
) -> tuple[VideoScore, list[Diagnostic]]:
    """doc を解決し、(解決後 doc, 診断リスト) を返す。

    ctx 省略時は MockProvider 入りの既定コンテキスト。passes 省略時は DEFAULT_PASSES。
    until にパス名を渡すと、そのパスまで実行して止める（途中段階の確認用）。
    """
    if ctx is None:
        ctx = default_context()
    if passes is None:
        from .passes import DEFAULT_PASSES

        passes = list(DEFAULT_PASSES)

    for p in topo_order(passes):
        if p.applicable(doc):
            doc, diags = p.run(doc, ctx)
            ctx.add(diags)
        if p.name == until:
            break
    return doc, ctx.diagnostics
