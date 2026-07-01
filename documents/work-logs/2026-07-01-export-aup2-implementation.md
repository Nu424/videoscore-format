# 作業ログ: aup2 コンバータ（`videoscore.export.aup2`）の実装

- 日付: 2026-07-01
- 範囲: 解決済み VideoScore を AviUtl2 `.aup2` へ書き出す最初の形式コンバータ（計画→実装→ドキュメント反映）
- 関連コミット: `2d2a564`（設計）→ `43d10f9`（実装）→ 本ログ・README・CLAUDE 反映

## 背景

解決系の pivot（`VideoScore → 解決済み VideoScore → 各種形式`）で、コンバータは**解決の外**に置くと決めていた。
その第一弾として aup2 を実装。下流 `otio-to-aup2` はスキャフォルドのみで、`.aup2` の仕様・実物は
`C:\code\AviUtl2_API`（`docs/aup2_format_specification.md` ＋ `samples/*.aup2` ＋ 参照実装 `aviutl2-api`）にあった。
入力が VideoScore（意味情報を保つ）になったため、otio-to-aup2 の最大の未解決論点「OTIO のどこに style/text/role を
載せるか」は**消滅**した。

## 確定した方針（合意済み）

| 論点 | 決定 | 理由 |
|------|------|------|
| エミッタ | 自前の薄いエミッタ（ランタイム依存なし） | 型・解決系と同じく pydantic のみで通す。出力の細部（CRLF/桁/hex）を完全制御 |
| レシピ型 | `videoscore.export` 層の Python 型 | エディタ固有で汎用スキーマ化しない。schema/TS 生成に載せない＝ドリフト無影響 |
| シーン | 単一 `[scene.0]` に frame オフセットで連結 | AviUtl2 の `scene.N` は独立コンポジション。直線動画には単一連結が自然 |
| 秒→フレーム | `start_f=round(s·fps)` / `end_f=round(e·fps)-1`（inclusive） | 隣接要素が1フレームも重ならず隙間なく連なる |
| レイヤー | レーン別帯＋帯内 interval partitioning | 「同一レイヤー・同一時刻に複数不可」を機械的に満たす。単一 allocator で帯跨ぎ衝突も無し |
| レシピ | `text`/`draw`/`filters` の3パッチ口＋相対値 `%w`/`%h`＋`xxx.default` | 生 hex/px をレシピ層に閉じる（カタログ三層の実装層） |
| 失敗 | 例外でなく `Diagnostic`。error でも部分変換 | `resolve`・`validate_styles` と同流儀 |
| aviutl2-api | dev extra `[aup2-dev]` の往復オラクルに限定 | 低成熟度ライブラリをランタイム依存にしない |

## 実装した内容

`python/src/videoscore/export/`（型/スキーマは増やさない＝ドリフト無影響）:

- `common.py` — `sec_to_frame` / `span_to_frames`（inclusive・退化検出）/ `scene_offsets`（尺累積）/
  `LayerAllocator`（区間分割で衝突なく貪欲割当）/ `Diagnostic` 再利用（解決系と共通型）。
- `recipes.py` — `Recipe`（text/draw/filters）/ `RecipeBook`（id 握手）/ `load_recipes` / `default_recipes`（同梱）/
  `resolve_template`（`%w`/`%h` を px 化）。
- `recipes.aup2.json` — 代表印のレシピ実ファイル（`telop.default`/`tone.emphasis`/`position.corner`/`layout.split-*`）。
- `aup2/` — `model.py`（薄い dataclass）/ `emit.py`（CRLF・UTF-8・値整形）/ `defaults.py`（要素種の既定エフェクト、
  `aviutl2-api` CLI の最小構成に準拠）/ `convert.py`（scene連結・要素→オブジェクト・レシピ展開・レイヤー割当・診断）/
  `__init__.py`（公開 `render_aup2` / `dump_aup2`）。

## 検証結果

- pytest: `test_export_aup2.py` 21件追加、合計 **51件パス**。**aviutl2-api での往復パース**（生成 .aup2 を読み戻し
  オブジェクト数・frame・layer が一致）も緑（`[aup2-dev]` があるときのみ実行）。
- 通しサンプルがエラー0で完走（s1 音声ドライバ→全要素 frame 0,39／s2 分割画面→video 2本が layer 0,1 に退避／
  telop が telop.default＋tone.emphasis＋ドロップシャドウに展開／レシピ差し替えで見た目のみ変化）。
- `videoscore-gen-schema --check` 緑（型を増やしていないためドリフト無し）。

## ファイルマップ

```
documents/export-aup2-design.md           設計・計画（実装済み表示）
python/src/videoscore/export/             common / recipes(+json) / aup2/(model,emit,defaults,convert)
python/tests/test_export_aup2.py          コンバータのテスト（21件・往復含む）
python/examples/export_aup2.py            一連の流れの実行可能サンプル(.py)
```

## 次の候補

1. **フィルタ／アニメーション**（移動・ベジエ・回転）。`標準描画` の値を `開始,終了,移動タイプ,パラメータ` に。
2. **トランジション**（保留10.2）・複数 `scene.N` 分割・ミキシング（music の voice 下ダッキング）。
3. **OTIO コンバータ** `videoscore.export.otio`（`[otio]` extra）。`common`（scene連結・レイヤー割当）を共有。
