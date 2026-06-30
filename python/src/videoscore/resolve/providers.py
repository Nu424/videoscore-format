"""素材プロバイダ（実体解決の拡張点）。

`materialize` パスは source の **URI スキーム**でプロバイダへ委譲する。
`tts://…` `t2i://…` `t2v://…` はすべて「記号 spec → 素材生成」という同じ形なので、
スキーム別プロバイダを足すだけで実体解決の種類を拡張できる（パス本体は無改造）。

本モジュールには開発・テスト用の `MockProvider` のみを置く。実 TTS / t2i / t2v /
実ファイル長プローブは将来別パッケージのプロバイダとして register する。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from .context import MaterializedAsset, ResolveContext


def parse_scheme(source: str) -> str:
    """`"tts://今日は"` → `"tts"`。スキームが無い素のパスは `""` を返す。"""
    if "://" in source:
        return source.split("://", 1)[0]
    return ""


def scheme_body(source: str) -> str:
    """スキームを除いた本体。`"tts://今日は"` → `"今日は"`、素のパスはそのまま。"""
    if "://" in source:
        return source.split("://", 1)[1]
    return source


@runtime_checkable
class AssetProvider(Protocol):
    """記号 source を実体素材へ解決するプロバイダ。"""

    schemes: tuple[str, ...]

    def materialize(self, source: str, ctx: ResolveContext) -> MaterializedAsset: ...


class ProviderRegistry:
    """スキーム → プロバイダの登録簿。未登録スキームは fallback が拾う。"""

    def __init__(self) -> None:
        self._by_scheme: dict[str, AssetProvider] = {}
        self._fallback: AssetProvider | None = None

    def register(self, provider: AssetProvider) -> "ProviderRegistry":
        for s in provider.schemes:
            self._by_scheme[s] = provider
        return self

    def set_fallback(self, provider: AssetProvider) -> "ProviderRegistry":
        self._fallback = provider
        return self

    def provider_for(self, source: str) -> AssetProvider | None:
        return self._by_scheme.get(parse_scheme(source)) or self._fallback

    def materialize(self, source: str, ctx: ResolveContext) -> MaterializedAsset | None:
        provider = self.provider_for(source)
        if provider is None:
            return None
        return provider.materialize(source, ctx)


# 記号スキーム（実体ファイルではなく生成 spec）。これらは source 自体も実体パスへ書き換える。
SYMBOLIC_SCHEMES = ("tts", "t2i", "t2v")


@dataclass
class MockProvider:
    """開発・テスト用のスタブ。実生成はせず、決定的な長さと擬似パスを返す。

    - `tts://…` … テキスト長 × `tts_seconds_per_char`（最低 `min_seconds`）。kind="audio"。
    - 画像系（拡張子で判定）… `ctx.image_seconds`。kind="image"。
    - その他（se/動画/素のパス）… `default_seconds`。kind="audio"/"video"。

    擬似パスは source の安定ハッシュから作る（毎回同じ＝べき等）。
    """

    schemes: tuple[str, ...] = ("tts", "t2i", "t2v", "file", "")
    tts_seconds_per_char: float = 0.12
    min_seconds: float = 0.5
    default_seconds: float = 3.0
    image_exts: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")

    def materialize(self, source: str, ctx: ResolveContext) -> MaterializedAsset:
        scheme = parse_scheme(source)
        body = scheme_body(source)
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]

        if scheme == "tts":
            secs = max(self.min_seconds, len(body) * self.tts_seconds_per_char)
            return MaterializedAsset(
                path=self._path(ctx, "audio", digest, ".wav"),
                intrinsic_seconds=round(secs, 3),
                kind="audio",
            )
        if scheme == "t2i" or self._looks_image(body):
            return MaterializedAsset(
                path=self._path(ctx, "image", digest, ".png"),
                intrinsic_seconds=ctx.image_seconds,
                kind="image",
            )
        if scheme == "t2v":
            return MaterializedAsset(
                path=self._path(ctx, "video", digest, ".mp4"),
                intrinsic_seconds=self.default_seconds,
                kind="video",
            )
        # 素のパス（既存ファイル想定）・se 等: パスは保持し、長さだけ既定で埋める。
        return MaterializedAsset(path=source, intrinsic_seconds=self.default_seconds)

    def _looks_image(self, body: str) -> bool:
        lower = body.lower()
        return any(lower.endswith(ext) for ext in self.image_exts)

    def _path(self, ctx: ResolveContext, kind: str, digest: str, ext: str) -> str:
        base = ctx.asset_dir.rstrip("/\\") if ctx.asset_dir else "mock://assets"
        sep = "/" if "://" in base or "/" in base else "\\"
        return f"{base}{sep}{kind}_{digest}{ext}"
