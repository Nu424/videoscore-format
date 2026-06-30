"""videoscore.resolve — VideoScore を段階的に清書方向へ具体化する解決パイプライン。

出力は **VideoScore**（OTIO ではない）。「解決済み VideoScore」は新しい型ではなく、
時間が全部具体・スタイルは意味のまま、という VideoScore の部分集合（不変条件）。
各種形式（OTIO/aup2…）へのコンバータは解決の外＝将来の別モジュール。

各「解決」は VideoScore→VideoScore のパス。`after` 依存でトポロジカルソートして回す。
依存は `videoscore.model` のみ（OTIO 非依存）。設計は documents/resolve-design.md。

    from videoscore.resolve import resolve
    resolved, diagnostics = resolve(doc)        # 既定: mock プロバイダ入り
    resolved, diagnostics = resolve(doc, until="normalize")  # 途中段階で止める
"""

from __future__ import annotations

from .context import (
    Diagnostic,
    MaterializedAsset,
    ResolveContext,
    default_context,
)
from .passes import (
    DEFAULT_PASSES,
    MaterializePass,
    NormalizePass,
    TimeResolvePass,
    ValidateResolvedPass,
)
from .pipeline import Pass, resolve, topo_order
from .providers import (
    AssetProvider,
    MockProvider,
    ProviderRegistry,
    parse_scheme,
)

__all__ = [
    # 実行
    "resolve",
    "topo_order",
    "Pass",
    "DEFAULT_PASSES",
    # コンテキスト・診断
    "ResolveContext",
    "default_context",
    "Diagnostic",
    "MaterializedAsset",
    # プロバイダ
    "AssetProvider",
    "ProviderRegistry",
    "MockProvider",
    "parse_scheme",
    # パス
    "NormalizePass",
    "MaterializePass",
    "TimeResolvePass",
    "ValidateResolvedPass",
]
