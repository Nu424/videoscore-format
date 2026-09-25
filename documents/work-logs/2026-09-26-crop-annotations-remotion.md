# 作業ログ: crop / annotations / schemaVersion・標準カタログ・Remotion プレイヤー

- 日付: 2026-09-26
- 範囲: 自動動画編集の計画（段階 1 の 1-B: B1〜B4）のうち、videoscore-format 側の形式拡張・aup2 対応・
  標準スタイルカタログ・Remotion プレイヤー
- ブランチ: `feature/crop-annotations-remotion`（未 push）
- 関連コミット: `ebc7f32`（形式）→ `33c5dc8`（仕様書）→ `22a3ebf`（aup2 crop）→ `d5a658c`（標準カタログ）→
  `8e6655a`（Remotion）→ 本ログ・README・CLAUDE 反映

## 背景

縦型ショートを「実動画の切り抜き＋発話字幕＋冒頭タイトル」で作るために、VideoScore に次が要る:
どこを映すか（`crop`）、構成判断の根拠を運ぶ場所（`annotations`）、部品間の版確認（`meta.schemaVersion`）、
意味の印の既定セット（標準カタログ）、そして解決済み VideoScore をそのまま再生・書き出すプレイヤー。

## 決定事項

| 論点 | 決定 | 理由 |
|------|------|------|
| `crop` の形 | video/overlay の項目 `[x, y, w, h]`（元フレームに対する 0〜1 比率・左上原点・静的） | 映す場所は内容依存のデータ。style の params ではない。収め方は layout 印に任せる |
| `crop` の検査 | `0≤x,y`、`0<w,h≤1`、`x+w≤1`、`y+h≤1`（浮動小数誤差 1e-9 を許容）を pydantic で | 型で弾ける範囲は型で |
| `annotations` | 全レーン要素と Scene に自由な object。resolve/export は解釈しない | 根拠参照・候補 ID・メモ用。`marks`（時間アンカー）と分ける |
| 形式の版 | `SCHEMA_VERSION = "0.2.0"`（python）。JSON Schema に `x-videoscore-version` として載せ、TS 生成で `SCHEMA_VERSION` 定数に | SoT を 1 か所に保ち、TS へは生成で流す |
| aup2 の crop | `render_aup2(source_sizes=...)` で素材解像度が分かれば `クリッピング`（px、`中心の位置を変更=1`）。分からなければ warning `unsupported-crop` で無視 | AviUtl2 のクリッピングは px 指定で解像度が要る。プローブ（ffprobe）はランタイム依存を増やすので持たず、呼び側が渡す |
| 標準カタログの置き場 | `python/src/videoscore/catalogs/standard/style-catalog.json`（パッケージ同梱） | `pip install …#subdirectory=python` でも入る。TS へは `pnpm gen` で `standard-catalog.gen.ts`（`STANDARD_STYLE_CATALOG` / `StandardStyleId`）を生成しドリフト検知に載せる |
| 網羅（§7） | Python: `validate_coverage(catalog, recipe_ids)`＋テスト。Remotion: `Record<StandardStyleId, RemotionRecipe>` の型 | 仕様書 §7「網羅」を実際に検査できる形に |
| aup2 の縦型レシピ | `layout.vertical-fit` 拡大率 56.25、`layout.vertical-crop` 177.78 の近似 | 標準描画の拡大率は素材画素基準。1080p 素材→1080×1920 出力を前提にした近似（設計書に明記、実機未確認） |
| Remotion 配布 | TS ソースのまま配布（ビルドなし）。`videoscore` は `import type` のみの peer 依存 | Remotion のバンドラは node_modules 内の .ts/.tsx もトランスパイルする（bundler の webpack 設定で確認）。git サブディレクトリ install で prepare ビルドが隣の typescript/ に依存する問題を避ける |
| 開発時の型解決 | `devDependencies.videoscore = link:../typescript`＋tsconfig `paths` で `../typescript/src` | CI で typescript/ をビルドせずに typecheck できる |
| props の形 | `{ score, mediaBase?, sourceSizes? }` か、解決済み VideoScore そのもの（`scenes` があれば優先） | `--props=videoscore.resolved.json` をそのまま渡せるように |
| 映像の音 | `OffthreadVideo` は `muted` | VideoScore は音を audio レーンに分けて持つ。二重再生を避ける |
| crop の描画 | overflow:hidden の箱 → 切り出し領域 → 素材全体（object-fit: fill）の 3 段。素材サイズは calculateMetadata が実測（失敗時 16:9 仮定） | 素材の縦横比が分からないと crop 領域の縦横比が決まらない |
| 時間換算 | `from = round(s·fps)`、尺 = `round(e·fps) - from`（最短 1） | aup2（`common.span_to_frames`）と同じ規則 |
| Remotion の版 | `remotion` / `@remotion/cli` を 4.0.529（2026-09 時点の latest）に固定 | 部品として再現性を優先 |
| サンプル素材 | ffmpeg の `testsrc2`＋`sine` とロゴ画像を `scripts/make-sample-media.mjs` で生成し、コミットしない | 実素材を入れない（計画 §8）。バイナリをリポジトリに置かない |

## 実装した内容

- 形式（B1）: `model/elements.py`（`crop`・`annotations`・検査）、`model/document.py`（`Meta.schemaVersion`・
  `Scene.annotations`・`SCHEMA_VERSION`）、`jsonschema.py`（`x-videoscore-version`）、`typescript/scripts/gen-types.mjs`
  （`SCHEMA_VERSION` 定数）。schema/・TS 型を再生成。仕様書 §1・§2・§7・§9 と spec.md を更新。
- aup2（B2）: `export/aup2/convert.py`（`_apply_crop`・`source_sizes`）、`defaults.clipping_effect`、設計書 §7・§8。
- 標準カタログ（B3）: `catalogs/`（`standard_catalog` / `standard_catalog_path` / `load_catalog` / `merge_catalogs`）、
  `model.validate_coverage`、`RecipeBook.ids()`、`recipes.aup2.json` に新 id、TS `standard-catalog.gen.ts`、仕様書 §5。
- Remotion（B4）: `remotion/src/lib/`（`VideoScoreComposition` / `calculateMetadata` / `recipes.remotion.tsx` /
  `resolveSrc` / `layout` / `time` / `validate`）、サンプル Root とエントリ、`samples/*.resolved.json`（16:9・9:16）、
  README、CI の typecheck ジョブ。Python 側に samples の妥当性テスト。

## 検証結果

- pytest: **81 件パス**（追加: crop/annotations/schemaVersion、resolve での素通し、aup2 crop、標準カタログ、
  Remotion サンプルの妥当性）。
- `videoscore-gen-schema --check` 相当（pytest の `test_schema.py`）緑、`pnpm gen:check` 緑、`pnpm build`（typescript）緑。
- remotion: `pnpm typecheck` 緑。`npx remotion compositions` で `VideoScore`（1920×1080・150f）と
  `VideoScoreVertical`（1080×1920・150f）が出る。`npx remotion still` を両方で実行し、静止画を目視:
  - 16:9: 上のタイトル（座布団つき）、下の通常テロップ、中央の強調、下の字幕、右上のロゴがそれぞれ想定位置。
    素材のタイムコード表示で `in`/`out` トリムが正しいこと（シーン 2 の 3.667 秒）を確認。
  - 9:16: `layout.vertical-fit` で素材が幅合わせ・中央、上の帯にタイトル、下の帯に字幕。
    `crop`＋`layout.vertical-crop` で素材中央の縦長領域が全面に。
  - `--props=samples/vertical.resolved.json`（VideoScore 直渡し）で 16:9 コンポジションが 9:16 に切り替わり、
    専用コンポジションと同一の画像になることを確認。未解決の VideoScore を渡すとエラー画面が出ることを確認。

## 未確認・保留

- aup2 の縦型レシピ（拡大率・字幕位置）とクリッピングは AviUtl2 実機では未確認（近似）。
- Remotion パッケージを別プロジェクトへ git サブディレクトリ指定で入れる流れは未検証（未 push のため）。
  TS ソース配布が Remotion のバンドラで通ることはバンドラ設定の確認と、このリポジトリ内での still で見ている。
- 動画の書き出し（`remotion render`）と音声は確認していない（静止画のみ）。
- フォントはシステムの日本語フォント（Noto Sans JP / Hiragino / Yu Gothic / Meiryo）頼み。Linux で書き出す場合は要導入。
- Studio の props 編集（zod スキーマ）は未対応（計画 §7 の検証項目）。
- `crop` の時間変化（パン）は将来。

## 次の候補

1. B5: videoscore-format-skill に実動画の切り抜き・字幕・縦型のパターンを追記。
2. プレビュー用プロキシ（計画 §6.4）と `sourceSizes` の受け渡しを本体スクリプト側で。
3. Studio の props 編集を試し、`videoscore.json` へ書き戻せるか確認。
