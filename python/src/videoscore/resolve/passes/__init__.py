"""解決パス群と既定パイプライン。

DEFAULT_PASSES は収束のみの最小パイプライン（値を具体化するパスだけ）。
要素を増やす補完パス（音声→テロップ、空フィラー充填、多言語清書…）はオプトインで
別途 register する想定で、ここには含めない。
"""

from __future__ import annotations

from .materialize import MaterializePass
from .normalize import NormalizePass
from .time_resolve import TimeResolvePass
from .validate import ValidateResolvedPass

# 既定の収束パイプライン（after 依存で並ぶので順序は実行器がトポロジカルソートする）
DEFAULT_PASSES = [
    NormalizePass(),
    MaterializePass(),
    TimeResolvePass(),
    ValidateResolvedPass(),
]

__all__ = [
    "DEFAULT_PASSES",
    "NormalizePass",
    "MaterializePass",
    "TimeResolvePass",
    "ValidateResolvedPass",
]
