"""AviUtl2 `.aup2` コンバータ（解決済み VideoScore → .aup2）。

公開 API:

    render_aup2(doc, ...) -> (Aup2Project, [Diagnostic])   # メモリ上のモデルと診断
    dump_aup2(doc, path, ...) -> [Diagnostic]              # .aup2 ファイルへ書き出し

いずれも `resolve` と同じく診断を例外でなくリストで返す。入力が未解決でも診断を出しつつ
可能な範囲で変換する（部分変換）。`resolve_first=True` で解決を前段に噛ませられる。
"""

from __future__ import annotations

from ...model import StyleCatalog, VideoScore
from ..common import Diagnostic
from ..recipes import RecipeBook
from .convert import SourceSizes, convert
from .model import Aup2Effect, Aup2Object, Aup2Project, Aup2Scene

__all__ = [
    "render_aup2",
    "dump_aup2",
    "Aup2Project",
    "Aup2Scene",
    "Aup2Object",
    "Aup2Effect",
    "SourceSizes",
]


def render_aup2(
    doc: VideoScore,
    *,
    recipes: RecipeBook | None = None,
    catalog: StyleCatalog | None = None,
    project_file: str = "",
    asset_base: str | None = None,
    source_sizes: SourceSizes | None = None,
    resolve_first: bool = False,
) -> tuple[Aup2Project, list[Diagnostic]]:
    """解決済み VideoScore を Aup2Project へ変換する。

    source_sizes（source → (幅, 高さ) px の dict か関数）を渡すと、video/overlay の `crop` を
    `クリッピング` フィルタへ展開する。無い場合 crop は warning `unsupported-crop` を出して無視する。

    resolve_first=True なら `videoscore.resolve.resolve` を先に通してから変換する
    （その診断も返り値に合流する）。既定は解決済み前提（False）。
    """
    diags: list[Diagnostic] = []
    if resolve_first:
        from ...resolve import resolve

        doc, rdiags = resolve(doc)
        diags.extend(rdiags)

    project, cdiags = convert(
        doc,
        recipes=recipes,
        catalog=catalog,
        project_file=project_file,
        asset_base=asset_base,
        source_sizes=source_sizes,
    )
    diags.extend(cdiags)
    return project, diags


def dump_aup2(doc: VideoScore, path: str, **kwargs) -> list[Diagnostic]:
    """render_aup2 して `.aup2` ファイルへ書き出す。診断リストを返す。

    project_file を明示しなければ、書き出し先パスを `[project]` の file= に採る。
    """
    kwargs.setdefault("project_file", path)
    project, diags = render_aup2(doc, **kwargs)
    project.dump(path)
    return diags
