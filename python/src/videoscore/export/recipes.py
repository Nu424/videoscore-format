"""スタイルのレシピ層（意味的な印 → 各エディタの具体エフェクト）。

カタログ三層（仕様書 §5）の**実装層**をコンバータ側で扱う。`style-catalog.json`（意味）が
AI と検証器のためのものであるのに対し、`recipes.<editor>.json`（実装）は**コンパイラ＝この
コンバータだけが読む**。両者は印の id（結合キー）だけで握手する。生の hex/px はこのレシピ層に
閉じ込め、中間構造にも AI にも出さない。

レシピ1件は「3つのパッチ口」で表す:

    text    : `テキスト` エフェクトのプロパティ上書き（フォント・文字色・文字装飾…）
    draw    : `標準描画` のプロパティ上書き（X/Y・拡大率・透明度…）
    filters : `[K.2]+` へ追記する追加フィルタ（縁取り・ドロップシャドウ…）

プロパティ値には相対テンプレート（`"-25%w"` = 幅の -25%、`"40%h"` = 高さの 40%）を書ける。
AviUtl2 の座標系（画面中央原点・Y 上が正・拡大率 %）の意味で解釈し、px 実数へ解決する。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from importlib import resources
from typing import Any

__all__ = ["Recipe", "RecipeBook", "load_recipes", "default_recipes", "resolve_template"]

# 既定レシピ（パッケージ同梱）。呼び出し側は load_recipes で差し替え・拡張できる。
_BUNDLED = "recipes.aup2.json"

_PCT = re.compile(r"^(-?\d+(?:\.\d+)?)%([wh]?)$")


@dataclass(frozen=True)
class Recipe:
    """1つの印の AviUtl2 展開規則。空のパッチ口は無視される。"""

    text: dict[str, Any] = field(default_factory=dict)
    draw: dict[str, Any] = field(default_factory=dict)
    filters: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Recipe":
        return cls(
            text=dict(data.get("text", {})),
            draw=dict(data.get("draw", {})),
            filters=[dict(f) for f in data.get("filters", [])],
        )


@dataclass(frozen=True)
class RecipeBook:
    """印 id → Recipe。カタログ意味層とは id だけで握手する（意味は持たない）。"""

    recipes: dict[str, Recipe]

    def get(self, style_id: str | None) -> Recipe | None:
        if style_id is None:
            return None
        return self.recipes.get(style_id)

    def __contains__(self, style_id: object) -> bool:
        return style_id in self.recipes

    def ids(self) -> set[str]:
        """レシピを持つ印 id の集合（網羅検証 `validate_coverage` に渡す）。"""
        return set(self.recipes)


def load_recipes(source: str | dict[str, Any]) -> RecipeBook:
    """recipes.<editor>.json（パス）または dict からレシピ集を読む。"""
    if isinstance(source, str):
        with open(source, encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        data = source
    return RecipeBook({sid: Recipe.from_dict(rule) for sid, rule in data.items()})


def default_recipes() -> RecipeBook:
    """パッケージ同梱の既定 aup2 レシピを返す。"""
    text = resources.files(__package__).joinpath(_BUNDLED).read_text(encoding="utf-8")
    return load_recipes(json.loads(text))


def resolve_template(value: Any, *, width: int, height: int) -> Any:
    """相対テンプレート（`"-25%w"`/`"40%h"`/`"50%"`）を px 実数へ解決する。

    `%w` は幅、`%h` は高さ基準。単位無し `%` は幅基準。数値・その他文字列（hex 色・
    フォント名・合成モード名）はそのまま返す。AviUtl2 の意味（中央原点・Y 上正）で
    書かれている前提で、符号反転などはしない（レシピ作者がその座標系で書く）。
    """
    if not isinstance(value, str):
        return value
    m = _PCT.match(value.strip())
    if not m:
        return value
    frac = float(m.group(1)) / 100.0
    basis = height if m.group(2) == "h" else width
    return frac * basis
