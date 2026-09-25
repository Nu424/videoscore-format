"""VideoScore → `.aup2` 変換の本体。

解決済み VideoScore（時間は数値・source は実ファイル・スタイルは意味のまま）を受け取り、
AviUtl2 の `.aup2` モデル（`Aup2Project`）へ落とす。時間解決やスタイルの意味付けは行わない
（それは解決系・カタログの責務）。ここがやるのは:

    * シーンを frame オフセットで単一 [scene.0] に連結
    * 各要素を AviUtl2 オブジェクト（メインエフェクト＋標準描画/音声再生）へ
    * `crop`（映す領域）を `クリッピング` フィルタへ（素材の解像度が分かるときだけ）
    * スタイルの印を recipes.aup2.json でエフェクトへ展開
    * レーン別帯＋区間分割でレイヤーを衝突なく割当
    * 解けていない/未対応のものは例外でなく Diagnostic で報告（部分変換）
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any, Union

from ...model import StyleCatalog, VideoScore
from ..common import Diagnostic, LayerAllocator, scene_offsets, span_to_frames
from ..recipes import Recipe, RecipeBook, default_recipes, resolve_template
from .defaults import (
    audio_effects,
    clipping_effect,
    image_effects,
    text_effects,
    video_effects,
)
from .model import Aup2Effect, Aup2Object, Aup2Project, Aup2Scene

__all__ = ["convert", "SourceSizes"]

# 素材の画素サイズ（幅, 高さ）の引き方。source 文字列 → (w, h)。dict か関数で渡す。
# crop（比率）を AviUtl2 の `クリッピング`（px）へ換算するのに使う。
SourceSizes = Union[Mapping[str, tuple[int, int]], Callable[[str], "tuple[int, int] | None"]]

_LANES = ("video", "overlay", "telop", "audio")  # 処理順（描画は floor で担保）
_LANE_FLOOR = {"video": 0, "overlay": 10, "telop": 20, "audio": 30}
_ROLE_OFFSET = {"voice": 0, "se": 2, "music": 4, "ambient": 6}
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff")
_SYMBOLIC_SCHEMES = ("tts", "t2i", "t2v")
_UNSUPPORTED = {"highlight"}
_TELOP_DEFAULT = "telop.default"


def convert(
    doc: VideoScore,
    *,
    recipes: RecipeBook | None = None,
    catalog: StyleCatalog | None = None,
    project_file: str = "",
    asset_base: str | None = None,
    source_sizes: SourceSizes | None = None,
) -> tuple[Aup2Project, list[Diagnostic]]:
    """解決済み VideoScore を Aup2Project へ変換する。

    source_sizes は crop を px へ換算するための素材解像度（無ければ crop は警告して無視）。
    """
    book = recipes if recipes is not None else default_recipes()
    diags: list[Diagnostic] = []

    meta = doc.meta
    width, height = meta.size if (meta and meta.size) else (1920, 1080)
    fps = meta.fps if (meta and meta.fps) else 30
    scene = Aup2Scene(width=int(width), height=int(height), fps=fps)

    alloc = LayerAllocator()
    ctx = _Ctx(book, catalog, width, height, fps, asset_base, alloc, source_sizes)

    # トップレベル（シーン跨ぎ）レーン（§10.1）はオフセット 0 の全体トラック。
    _process(doc, 0.0, "$", ctx, scene.objects, diags)
    # 各シーンを尺の累積オフセットで連結。
    for si, (sc, off) in enumerate(zip(doc.scenes, scene_offsets(doc.scenes))):
        _process(sc, off, f"$.scenes[{si}({sc.id})]", ctx, scene.objects, diags)

    return Aup2Project(scene=scene, file_path=project_file), diags


class _Ctx:
    """変換中に持ち回る共有状態。"""

    def __init__(self, book, catalog, width, height, fps, asset_base, alloc, source_sizes=None):
        self.book: RecipeBook = book
        self.catalog: StyleCatalog | None = catalog
        self.width: int = int(width)
        self.height: int = int(height)
        self.fps = fps
        self.asset_base = asset_base
        self.alloc: LayerAllocator = alloc
        self.source_sizes = source_sizes

    def source_size(self, source: str, path: str) -> tuple[int, int] | None:
        """素材の画素サイズを引く（source 文字列 → 解決後パスの順）。分からなければ None。"""
        sizes = self.source_sizes
        if sizes is None:
            return None
        for key in (source, path):
            size = sizes(key) if callable(sizes) else sizes.get(key)
            if size is not None:
                return int(size[0]), int(size[1])
        return None


def _process(container, offset, prefix, ctx, objects, diags):
    for lane in _LANES:
        for i, el in enumerate(getattr(container, lane) or []):
            label = f"{prefix}.{lane}[{i}]"
            obj, ediags = _convert_element(lane, el, offset, ctx, label)
            diags.extend(ediags)
            if obj is not None:
                objects.append(obj)


def _convert_element(lane, el, offset, ctx, label):
    diags: list[Diagnostic] = []
    start, end = el.t[0], el.t[1]
    if not (_is_number(start) and _is_number(end)):
        diags.append(
            Diagnostic("not-resolved", label, f"t={tuple(el.t)!r} が数値でない（未解決の VideoScore）", "error")
        )
        return None, diags

    (start_f, end_f), degenerate = span_to_frames(offset + start, offset + end, ctx.fps)
    if degenerate:
        diags.append(
            Diagnostic("degenerate-span", label, f"尺がフレーム換算で 0 以下 → 最短1フレームに丸めた", "warning")
        )

    # メインエフェクト＋標準描画/音声再生（素の器）
    effects = _base_effects(lane, el, ctx, diags, label)

    # 映す領域（crop）→ クリッピング。収め方（拡大・位置）は後段のスタイル（layout 印）が決める。
    _apply_crop(el, effects, ctx, diags, label)

    # スタイルの印をレシピ展開
    _apply_style(lane, el, effects, ctx, diags, label)

    floor = _LANE_FLOOR[lane]
    if lane == "audio":
        floor += _ROLE_OFFSET.get(getattr(el, "role", None), 0)
    layer = ctx.alloc.allocate(start_f, end_f, floor)

    return Aup2Object(layer=layer, frame_start=start_f, frame_end=end_f, effects=effects), diags


def _base_effects(lane, el, ctx, diags, label):
    if lane == "telop":
        return text_effects(el.text)

    # media レーン（video/audio/overlay）は source を持つ
    source = el.source
    _check_symbolic(source, diags, label)
    path = _resolve_path(source, ctx.asset_base)
    play_pos = float(el.in_ or 0.0)

    if lane == "audio":
        return audio_effects(path, play_pos=play_pos)
    if lane == "video":
        return video_effects(path, play_pos=play_pos)
    # overlay: 拡張子で画像/動画を判定
    if source.lower().endswith(_IMAGE_EXTS):
        return image_effects(path)
    return video_effects(path, play_pos=play_pos)


def _apply_style(lane, el, effects, ctx, diags, label):
    # telop は既定 telop.default をまず当てる（カタログの既定値思想）
    if lane == "telop":
        base = ctx.book.get(_TELOP_DEFAULT)
        if base is not None:
            _patch(effects, base, ctx)

    style = el.style
    if style is None or style == _TELOP_DEFAULT:
        return

    if style in _UNSUPPORTED:
        diags.append(Diagnostic("unsupported-style", label, f"印 '{style}' は v1 未対応（素の既定で描画）", "warning"))
        return

    if ctx.catalog is not None:
        entry = ctx.catalog.styles.get(style)
        if entry is not None and lane not in entry.appliesTo:
            diags.append(
                Diagnostic("appliesTo", label, f"印 '{style}' は {entry.appliesTo} 専用で {lane} に付かない", "warning")
            )

    recipe = ctx.book.get(style)
    if recipe is None:
        diags.append(Diagnostic("unknown-style", label, f"印 '{style}' は aup2 レシピに無い（素の既定で描画）", "warning"))
        return

    _patch(effects, recipe, ctx)


def _apply_crop(el, effects, ctx, diags, label):
    crop = getattr(el, "crop", None)
    if crop is None:
        return
    x, y, w, h = (float(v) for v in crop)
    if (x, y, w, h) == (0.0, 0.0, 1.0, 1.0):
        return  # 全面＝切り抜きなし
    size = ctx.source_size(el.source, _resolve_path(el.source, ctx.asset_base))
    if size is None:
        diags.append(
            Diagnostic(
                "unsupported-crop",
                label,
                "crop unsupported in aup2: 素材の解像度が不明なため crop を無視した"
                "（render_aup2(source_sizes=...) で解像度を渡すとクリッピングに展開する）",
                "warning",
            )
        )
        return
    sw, sh = size
    top = round(y * sh)
    bottom = round((1.0 - y - h) * sh)
    left = round(x * sw)
    right = round((1.0 - x - w) * sw)
    effects.append(clipping_effect(top=top, bottom=bottom, left=left, right=right))


def _patch(effects: list[Aup2Effect], recipe: Recipe, ctx: "_Ctx") -> None:
    """レシピの text/draw パッチを対応エフェクトへ適用し、filters を追記する。"""
    for eff in effects:
        if eff.name == "テキスト" and recipe.text:
            for k, v in recipe.text.items():
                eff.props[k] = resolve_template(v, width=ctx.width, height=ctx.height)
        elif eff.name == "標準描画" and recipe.draw:
            for k, v in recipe.draw.items():
                eff.props[k] = resolve_template(v, width=ctx.width, height=ctx.height)
    for flt in recipe.filters:
        props = {
            k: resolve_template(v, width=ctx.width, height=ctx.height)
            for k, v in flt.get("props", {}).items()
        }
        effects.append(Aup2Effect(flt["name"], props))


def _check_symbolic(source: str, diags: list[Diagnostic], label: str) -> None:
    scheme = source.split("://", 1)[0] if "://" in source else ""
    if scheme in _SYMBOLIC_SCHEMES:
        diags.append(
            Diagnostic("symbolic-source", label, f"記号 source '{source}' が未実体化（materialize 未実行）", "error")
        )


def _resolve_path(source: str, asset_base: str | None) -> str:
    """相対パスは asset_base を前置して正規化。URI（scheme://）や絶対パスはそのまま。"""
    if "://" in source or os.path.isabs(source):
        return source
    if asset_base:
        return os.path.normpath(os.path.join(asset_base, source))
    return source


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)
