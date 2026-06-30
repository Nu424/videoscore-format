"""videoscore — VideoScore 中間構造の型定義と検証。

型は `videoscore.model` に集約する。将来の VideoScore→OTIO 解決は
`videoscore.resolve` に分離し（optional extra `[otio]`）、ここから型を import する。
"""

from __future__ import annotations

from . import model
from .model import (
    Meta,
    Scene,
    StyleCatalog,
    VideoScore,
    validate_styles,
)

__all__ = [
    "model",
    "VideoScore",
    "Scene",
    "Meta",
    "StyleCatalog",
    "validate_styles",
]
