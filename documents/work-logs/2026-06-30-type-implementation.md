# 作業ログ: VideoScore形式の型実装（Python / TypeScript）

- 日付: 2026-06-30
- 範囲: VideoScore 中間構造を Python・TypeScript のデータ構造として扱う型基盤の実装（フェーズ1〜4）
- 関連コミット: `86cea67`（CLAUDE.md）→ `e4790bb` → `5dcf01f` → `60cbbd1` → `f7c1efd`

## ゴール

最終的に「VideoScore 形式 → 各種記述を解決 → OTIO 生成」スクリプトを作る。その前段として、
VideoScore 形式を **Python / TypeScript の型**として管理できる基盤を用意する。型定義と、
将来の OTIO 解決スクリプトがぶつからない構成にする。

## 確定した方針

| 論点 | 決定 | 理由 |
|------|------|------|
| 型の Single Source of Truth | **Python（pydantic v2）** | OTIO は Python ファースト（PyPI `OpenTimelineIO` 0.18系 / py3.10-3.13）。解決スクリプトが Python になるため重心を Python に置く。§7 検証にランタイム検証が要る |
| TS 型 | pydantic → JSON Schema → **json2ts で生成** | 二重管理を避け、CI でドリフト検知 |
| 検証 | pydantic のランタイム検証（dataclass 不採用） | §7 のenum/appliesTo/時間範囲などを型と一体で担保 |
| Python 構成 | 単一 `videoscore` パッケージ。`model`（型）＋将来 `resolve`（OTIO）。OTIO 依存は optional extra `[otio]` | 型だけ欲しい利用者に `opentimelineio` を引かせない |
| TS 構成 | 型のみ。`typescript/` に配置、pnpm 前提 | 解決は Python に閉じる。npm 素の git-subdir 制約を pnpm `#path:` で回避 |
| 配布 | git 経由（pip `#subdirectory=python` / pnpm `#path:/typescript`） | パッケージレジストリ未公開でも使える |
| `after` 等の時間語彙 | **脱糖せず素のまま型化** | 脱糖・時間解決は解決スクリプトの責務。中間構造の「過少指定を保持」思想に合致 |

## フェーズ別の成果

### フェーズ1: Python 型本体（`e4790bb`）
- `videoscore.model` に meta / scenes / 4レーン / 時間語彙 / style を pydantic v2 で実装。
- 時間語彙（`timing.py`）: `start` は `"auto"` を**型レベルで除外**（循環防止の鉄則）、`end` のみ `auto` 可。
  `after` / `ref` / `gap` 形は素のまま保持。
- レーン要素（`elements.py`）: メディア系（video/audio/overlay）と telop を分離。`in` はエイリアス。
  両端が具体数値のときだけ `0 <= start < end` を検査（尺未確定なら検査しない）。
- ドキュメント（`document.py`）: トップレベルレーン（§10.1、skill が使う全体BGM等）も optional 化。
  `to_json_dict()` で None・空レーンを省いた最小 JSON 出力。
- カタログ（`catalog.py`）＋ `validate_styles`（`validate.py`）: §7 の enum / appliesTo を横断検証。
- テスト: 仕様書 §8 サンプルをフィクスチャに pytest。

### フェーズ2: JSON Schema 書き出し（`5dcf01f`）
- `videoscore.jsonschema`: `build_schemas` / `render` と CLI `videoscore-gen-schema`。
- `$schema`（draft 2020-12）を明示、決定的整形（indent=2 / 非ASCII保持 / 末尾改行）。
- `--check` で書き込まずドリフト検知（CI の土台）。
- `schema/videoscore.schema.json`・`schema/style-catalog.schema.json` を生成・コミット。

### フェーズ3: TypeScript 型生成（`60cbbd1`）
- **json2ts は draft 2020-12 の `prefixItems`（タプル）未サポート**で、時間語彙 `t` が `unknown` に劣化。
- 対策: `typescript/scripts/gen-types.mjs` の前処理シムで
  (1) `prefixItems` → draft-07 `items:[...]` にダウンレベル、
  (2) `title` アノテーション（文字列）除去で別名爆発を抑制（フィールド名 "title" は値がオブジェクトなので保持）。
- 結果: `t` が `[number | "after" | RefObject, number | ("auto"|"after") | RefObject, Gap] | [...]` の正しいタプル型に。
  `start` に `"auto"` を渡すと **TS 型でもエラー**（鉄則が両言語で効く）。
- `typescript/`: package.json（pnpm 前提 / `prepare` で tsc）、tsconfig、生成物 `src/*.gen.ts` をコミット。

### フェーズ4: パッケージング・CI（`f7c1efd`）
- README（ルート / python / typescript）: git 経由インストール、再生成手順、設計要点。
- `.github/workflows/ci.yml`:
  - Python（3.10 / 3.13）: `pytest` と `videoscore-gen-schema --check`。
  - TypeScript: `pnpm gen:check` と `pnpm build`。
  - → モデル → JSON Schema → TS 型の三者一致を保証。

## 検証結果

- Python: pytest 全パス（モデル / §3鉄則 / §7検証 / JSON Schema ドリフト）。
- TypeScript: `gen:check` 最新、`tsc` ビルド成功、consumer 型チェックで妥当オブジェクトが通り `start:"auto"` は型エラー。

## ファイルマップ

```
python/        pyproject.toml, src/videoscore/{model,jsonschema}, tests/, examples/quickstart.ipynb
schema/        videoscore.schema.json, style-catalog.schema.json   （生成物）
typescript/    package.json, tsconfig.json, scripts/gen-types.mjs, src/{index,*.gen}.ts （*.gen.ts は生成物）
.github/workflows/ci.yml
```

## 再生成の手順（モデル変更時）

```bash
cd python && videoscore-gen-schema --out-dir ../schema   # ① pydantic → JSON Schema
cd ../typescript && pnpm gen                              # ② JSON Schema → TS 型
```

CI は `--check` / `gen:check` で「生成物がモデルと一致しているか」を検証する。

## 次の候補

1. **`videoscore.resolve`（VideoScore → OTIO 解決）** — 本命。`after` 脱糖、`auto`/`ref` の時間解決
   （DAG トポロジカルソート）、スタイルレシピ展開、OTIO 出力。
2. `recipes.<editor>.json` の型と「網羅」検証（§7）。
3. 別環境での pip / pnpm git インストール実地確認。
