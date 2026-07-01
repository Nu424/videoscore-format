"""形式コンバータ（解決済み VideoScore → 各エディタ形式）。

解決系（`videoscore.resolve`）が時間を具体化した**解決済み VideoScore**を、各種タイムライン
形式へ書き出す層。スタイルの意味的な印（`tone.emphasis` 等）を各エディタの具体エフェクトへ
展開する「レシピ展開」もここが担う（＝解決の外。設計は `documents/resolve-design.md` §6）。

第一弾は AviUtl2 の `.aup2`（`videoscore.export.aup2`）。共通部品（秒→フレーム変換・シーン連結・
レイヤー割当）は `common` に置き、将来の OTIO 等のコンバータと共有する。
"""

from __future__ import annotations

from .aup2 import dump_aup2, render_aup2

__all__ = ["render_aup2", "dump_aup2"]
