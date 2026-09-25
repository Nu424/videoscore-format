"""VideoScore 中間構造の型定義（pydantic を正＝Single Source of Truth）。

仕様の一次ソースは documents/intermediate-structure-guideline.md。
このパッケージはその仕様を pydantic v2 のモデルとして表現し、JSON Schema /
TypeScript 型の生成元になる。脱糖・時間解決・OTIO 出力は別モジュール
（videoscore.resolve、将来）に分離する。
"""

from __future__ import annotations

from .catalog import LaneName, StyleCatalog, StyleEntry
from .document import SCHEMA_VERSION, Meta, Scene, VideoScore
from .elements import (
    AudioElement,
    AudioRole,
    BaseElement,
    Crop,
    OverlayElement,
    TelopElement,
    VideoElement,
)
from .timing import (
    DurationValue,
    EndValue,
    Gap,
    RefObject,
    StartValue,
    TimeSpan,
)
from .validate import StyleIssue, validate_styles

__all__ = [
    # document
    "SCHEMA_VERSION",
    "VideoScore",
    "Scene",
    "Meta",
    # elements
    "BaseElement",
    "VideoElement",
    "AudioElement",
    "TelopElement",
    "OverlayElement",
    "AudioRole",
    "Crop",
    # timing
    "RefObject",
    "Gap",
    "TimeSpan",
    "StartValue",
    "EndValue",
    "DurationValue",
    # catalog
    "StyleCatalog",
    "StyleEntry",
    "LaneName",
    # validation
    "validate_styles",
    "StyleIssue",
]
