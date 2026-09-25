"""カタログ横断の検証（仕様書 §7 のうち、文書単体では書けないもの）。

pydantic の型・バリデータで静的に担保できるもの（時間範囲の具体ケース、start≠auto、
レーン別の必須フィールド等）は model 側で済ませる。ここはカタログという別文書を
必要とする検証（enum / appliesTo）を担う。

時間解決を要する検証（循環＝DAG、auto/ref の確定、`end <= シーン尺` 等）は
解決スクリプト（videoscore.resolve）の責務であり、ここには置かない。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .catalog import StyleCatalog
from .document import VideoScore

# どのレーン名の要素がどの属性に入っているか（要素自身はレーンを知らないため外から渡す）
_LANES = ("video", "audio", "telop", "overlay")


@dataclass(frozen=True)
class StyleIssue:
    """検証で見つかった問題。location は人間が辿れる経路文字列。"""

    kind: str  # "unknown-style" | "applies-to" | "coverage"
    location: str
    style: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.location}: {self.detail}"


def validate_styles(doc: VideoScore, catalog: StyleCatalog) -> list[StyleIssue]:
    """doc 内の全 `style` をカタログと突き合わせる（§7 enum / appliesTo）。

    返り値は問題のリスト（空なら OK）。例外は投げない＝呼び側が件数で判断できる。
    """
    issues: list[StyleIssue] = []

    def check(lane: str, style: str | None, where: str) -> None:
        if style is None:
            return
        entry = catalog.styles.get(style)
        if entry is None:
            issues.append(
                StyleIssue("unknown-style", where, style, f"印 '{style}' はカタログに無い")
            )
            return
        if lane not in entry.appliesTo:
            issues.append(
                StyleIssue(
                    "applies-to",
                    where,
                    style,
                    f"印 '{style}' は {entry.appliesTo} 専用で、{lane} には付けられない",
                )
            )

    # トップレベルレーン（§10.1）
    for lane in _LANES:
        for i, el in enumerate(getattr(doc, lane) or []):
            check(lane, el.style, f"$.{lane}[{i}]")

    # 各シーン
    for si, scene in enumerate(doc.scenes):
        for lane in _LANES:
            for i, el in enumerate(getattr(scene, lane)):
                check(lane, el.style, f"$.scenes[{si}({scene.id})].{lane}[{i}]")

    return issues


def validate_coverage(
    catalog: StyleCatalog, recipe_ids: Iterable[str], *, editor: str = "editor"
) -> list[StyleIssue]:
    """§7 網羅: カタログ（意味）の全 id がレシピ（実装）に揃っているかを検査する。

    recipe_ids は `recipes.<editor>.*` が持つ id の集合（エディタ非依存に id だけ受け取る）。
    レシピ側にだけある id（カタログに無い拡張）は問題にしない。
    """
    have = set(recipe_ids)
    return [
        StyleIssue("coverage", f"recipes.{editor}", sid, f"印 '{sid}' のレシピが recipes.{editor} に無い")
        for sid in catalog.styles
        if sid not in have
    ]
