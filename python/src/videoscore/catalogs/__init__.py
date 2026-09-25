"""標準スタイルカタログ（意味の層の既定セット）。

`style-catalog.json`（仕様書 §5）のうち、どのプロジェクトでもまず使える最小セットを
パッケージに同梱する。プロジェクトは独自の `style-catalog.json` で上書き・追加できる
（`merge_catalogs(standard_catalog(), project_catalog)`）。

    from videoscore.catalogs import standard_catalog
    catalog = standard_catalog()
    issues = validate_styles(doc, catalog)

実装（見た目）は各エディタのレシピ（`recipes.<editor>.*`）に置き、ここは意味だけを持つ。
同じ JSON から TypeScript 側の `STANDARD_STYLE_CATALOG` も生成される（typescript/ の `pnpm gen`）。
"""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from ..model import StyleCatalog

__all__ = [
    "STANDARD_CATALOG_RESOURCE",
    "standard_catalog",
    "standard_catalog_path",
    "load_catalog",
    "merge_catalogs",
]

# パッケージ内での相対位置（importlib.resources 用）
STANDARD_CATALOG_RESOURCE = "standard/style-catalog.json"


def standard_catalog() -> StyleCatalog:
    """同梱の標準スタイルカタログを読み込んで返す。"""
    text = resources.files(__package__).joinpath(STANDARD_CATALOG_RESOURCE).read_text(encoding="utf-8")
    return StyleCatalog.model_validate(json.loads(text))


def standard_catalog_path() -> Path:
    """同梱の標準カタログ JSON のファイルパス（`meta.styleCatalog` に書く等の用途）。"""
    return Path(str(resources.files(__package__).joinpath(STANDARD_CATALOG_RESOURCE)))


def load_catalog(path: str | Path) -> StyleCatalog:
    """任意の `style-catalog.json` を読み込む。"""
    return StyleCatalog.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def merge_catalogs(base: StyleCatalog, *overrides: StyleCatalog) -> StyleCatalog:
    """カタログを id 単位で上書き合成する（後ろほど優先）。プロジェクト固有の印の追加・差し替え用。"""
    styles = dict(base.styles)
    for over in overrides:
        styles.update(over.styles)
    return StyleCatalog(styles=styles)
