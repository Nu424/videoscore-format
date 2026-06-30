"""解決の共有状態（診断・素材実体・コンテキスト）。

`Diagnostic` は解決中に見つかった問題や注記。例外を投げる代わりにこれを積む
（`videoscore.model.validate_styles` と同じ流儀）。解けない `auto` 等は「エラー」ではなく
「部分解決＋フラグ」として扱える（仕様書 §7「尺確定フェーズ要」）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .providers import ProviderRegistry

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Diagnostic:
    """解決中の問題・注記。location は人間が辿れる経路文字列。"""

    kind: str  # 例: "cycle" / "unresolved-auto" / "dangling-ref" / "mock-estimate"
    location: str
    detail: str
    severity: Severity = "error"

    def __str__(self) -> str:
        return f"[{self.severity}:{self.kind}] {self.location}: {self.detail}"


@dataclass(frozen=True)
class MaterializedAsset:
    """プロバイダが返す実体素材。

    intrinsic_seconds は素材本来の長さ（音声/動画の尺、画像の既定表示秒）。
    分からなければ None（その場合 `auto` は解けず診断が立つ）。
    """

    path: str
    intrinsic_seconds: float | None = None
    kind: str | None = None  # "audio" / "video" / "image" など（任意）


@dataclass
class ResolveContext:
    """解決パイプライン全体で共有する状態とサービス。

    providers   : URI スキーム別の素材プロバイダ登録簿
    asset_dir   : 生成素材の置き場（プロバイダが使う。未指定可）
    diagnostics : 各パスが積む診断
    image_seconds : 画像など本来尺を持たない素材の既定表示秒
    """

    providers: "ProviderRegistry"
    asset_dir: str | None = None
    image_seconds: float = 5.0
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def add(self, diags: list[Diagnostic]) -> None:
        self.diagnostics.extend(diags)


def default_context(**kwargs) -> ResolveContext:
    """MockProvider を入れた既定コンテキストを返す（実プロバイダ未設定でも回る）。"""
    from .providers import MockProvider, ProviderRegistry

    registry = ProviderRegistry()
    registry.set_fallback(MockProvider())
    return ResolveContext(providers=registry, **kwargs)
