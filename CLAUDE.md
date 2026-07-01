# CLAUDE.md

このリポジトリで作業するときに参照するガイド。

## このプロジェクトは何か

動画編集の**中間構造（VideoScore 形式）**を設計・仕様化するリポジトリ。
台本やアウトラインと、実タイムライン（Premiere 等の各エディタ形式）の間に置く、
絵コンテ的で過少指定な中間表現を定義する。

```
台本 / アウトライン  →  構成（★この中間構造）  →  タイムライン  →  レンダ
```

現状は**仕様＋型実装＋解決系の段階**。VideoScore 形式を Python / TypeScript の型として扱う基盤に加え、
解決パイプライン `videoscore.resolve` まで実装済み。

**重要な方針（2026-07-01）**: 最終目標は「VideoScore → 各記述を解決 → 各種形式（OTIO 等）生成」だが、
**解決の出力は OTIO ではなく VideoScore**。VideoScore はスタイル等の意味情報を持ち、OTIO に落とすと潰れるため、
フローを `VideoScore → 解決済み VideoScore → 各種形式（OTIO/aup2…）` にした。解決系は時間を具体化し
スタイルは意味のまま残す（＝解決済みは VideoScore の部分集合）。各形式コンバータ（レシピ展開含む）は解決の外で今後実装。

## リポジトリ構成

| パス | 役割 |
|------|------|
| `documents/intermediate-structure-guideline.md` | 中間構造の**正式仕様書**。設計判断・時間モデル・検証ルールの一次ソース |
| `documents/work-logs/` | 作業ログ（実装の経緯・決定事項） |
| `.claude/videoscore-format-skill/SKILL.md` | 台本→中間構造JSONを**組み立てる手順書**（Agent Skill） |
| `.claude/videoscore-format-skill/references/spec.md` | スキルから参照する仕様。現状 guideline と同一内容 |
| `documents/resolve-design.md` | 解決系（`videoscore.resolve`）の設計・計画書（実装済み） |
| `python/` | **型本体（pydantic）と検証**（型の SoT）＋**解決系 `videoscore.resolve`** |
| `schema/` | pydantic から生成した JSON Schema（**生成物**・コミット済み） |
| `typescript/` | JSON Schema から生成した TypeScript 型（**生成物**・コミット済み） |
| `.github/workflows/ci.yml` | CI（pytest ＋ 生成物のドリフト検知） |

> 注意：`guideline.md` と `spec.md` は今は同じ内容。仕様を直すときは**両方の同期**を意識する
> （将来どちらを SoT にするか決めるまでは二重管理になっている点に留意）。

## 中間構造の核となる設計（要点のみ。詳細は仕様書）

3つの方針：
1. **時間は具体的に書く** — 「素材の何秒〜」「テロップを何秒表示」を実体値で持つ。
2. **見た目（スタイル）は抽象に保つ** — 具体レシピ（青2px縁取り等）は書かず、**意味的な印**だけ置く。
3. **構造は薄く** — 再帰を持たず、固定された浅い階層で表現する。

覚えておくべき主要概念：
- **scenes + 4レーン**（`video` / `audio` / `telop` / `overlay`）。1シーン＝1つのローカル時計。
- **ドライバ／フィラー** — `duration: {ref:"audio.end"}` でどのレーンが尺を決めるか宣言。
- **時間語彙4つ** — 数値 / `auto` / `after` / `ref`。`start` は常に具体or参照、派生してよいのは `end` だけ（循環防止）。
- **`t`（配置）と `in`/`out`（トリム）の分離** — 取り違え厳禁。
- **スタイルは意味で名付ける** — `tone.emphasis` ◯ / `blue-outline-2px` ✗。生の px/hex は禁止。
- **カタログ三層** — `style-catalog.json`（意味・AIと検証器が読む）と `recipes.<editor>.json`（実装・コンパイラが読む）を id で握手。

仕様を変更・拡張するときは、仕様書 §9（設計判断の早見表）と §10（保留事項）に必ず目を通し、
既存の設計意図と矛盾しないか確認する。新しい決定をしたら早見表・保留事項を更新する。

## 型実装と生成パイプライン

**型は Python（pydantic v2）が Single Source of Truth。** ここから JSON Schema → TypeScript 型を生成する。

```
pydantic models (python/src/videoscore/model)   ← 唯一の正
   └─ schema/*.json        （videoscore-gen-schema で生成）
        └─ typescript/src/*.gen.ts   （pnpm gen で生成）
```

- **型を変えるときは必ず pydantic を直す。** `schema/*.json` と `typescript/src/*.gen.ts` は生成物なので手編集しない。
  変更後は `videoscore-gen-schema` → `pnpm gen` の順で再生成し、生成物も一緒にコミットする。
- **型では時間語彙を脱糖しない。** `after`/`auto`/`ref`/`gap` 形は素のまま保持。脱糖・時間解決は `videoscore.resolve` の責務。
  循環防止の鉄則（`start` に `auto` 不可）は Python・TS の**両方の型**に焼き込んである。
- **OTIO 依存は optional extra `[otio]`。** 型・解決系はどちらも pydantic のみ依存。extra は将来の各形式コンバータ用。
- **json2ts の落とし穴**: draft 2020-12 の `prefixItems`（タプル）未サポートで `t` が `unknown` に劣化する。
  `typescript/scripts/gen-types.mjs` の前処理シム（prefixItems→draft-07 items、title アノテーション除去）で回避済み。
  生成器を差し替えるときはこの制約に注意。

開発コマンド（詳細は各 README）:

```bash
cd python && pip install -e ".[dev]" && pytest          # 型・検証・ドリフトのテスト
videoscore-gen-schema --out-dir ../schema               # ① pydantic → JSON Schema
cd ../typescript && pnpm install && pnpm gen && pnpm build   # ② JSON Schema → TS 型
```

CI は `videoscore-gen-schema --check` と `pnpm gen:check` で「生成物がモデルと一致しているか」を検証する。
モデルを変えて再生成し忘れると CI が落ちる。

## 解決系（`videoscore.resolve`）

絵コンテ的 VideoScore を段階的に清書方向へ具体化する。**出力は解決済み VideoScore**（時間は具体・スタイルは意味のまま）。
設計・計画は `documents/resolve-design.md`。核となる約束事：

- **すべては `Pass = VideoScore→(VideoScore, [Diagnostic])`。** 各「解決」を独立パスにし、`after` 依存で
  トポロジカルソートして回す。`applicable()` で**べき等・部分解決**、`resolve(doc, until="...")` で段階出力。
- **既定パイプライン `DEFAULT_PASSES`**（収束のみ）: normalize（after 脱糖）→ materialize（実体化＋実測長を out に補完）
  → resolve-time（auto/ref を DAG で具体秒へ・循環検出）→ validate-resolved（§7 不変条件）。
- **実体解決は URI スキーム別 `AssetProvider` で拡張**。`tts://`/`t2i://`/`t2v://` はプロバイダを1個 register するだけで足せる
  （materialize 本体は無改造）。`MockProvider` は開発用スタブ。実プロバイダは未実装。
- **診断は例外でなくリスト返し**（`validate_styles` と同じ流儀）。解けない `auto` は error でなく部分解決の警告。
- **型・スキーマは増やさない**（既存 VideoScore 型の上で動く）。よって schema/TS のドリフト検査には無影響。
- 要素を増やす**補完パス**（音声→テロップ生成、B-roll 充填、多言語清書 等）は同じ `Pass` 型で後付けできるが、
  既定には入れない（オプトイン）。詳細は resolve-design.md §6。

サンプル `python/examples/resolve_pipeline.py`、テスト `python/tests/test_resolve.py`。

## 開発の進め方（このリポジトリの作業フロー）

ユーザーは次のサイクルで開発を進める。各段階を飛ばさないこと。

1. **構想** — ユーザーが構想・やりたいことを述べる。
2. **計画・方針** — それを受けて計画や方針を**一緒に練り、洗練させる**。
   既存仕様との整合・トレードオフ・代替案を示し、合意してから先に進む。設計の議論はここで尽くす。
3. **作業** — 合意した方針に沿って具体的な作業（ドキュメント編集・実装等）を進める。
4. **確認** — 結果をユーザーと確認する。
5. **コミット** — **実装の段階ごとに**コミットする。1コミット＝1つのまとまった変更。

### 進め方の指針
- いきなり大きく書き換えない。まず方針合意（ステップ2）を取る。大きな台本ならシーン分割案だけ先に見せる等、
  小さく合意してから進めると手戻りが少ない。
- コミットは段階ごとに分けて細かく。コミットメッセージは日本語、`docs:` / `feat:` などの prefix を踏襲する
  （既存履歴に倣う）。コミットはユーザーの確認後、または明示の指示で行う。
- ドキュメントの語り口・表記（です/だ調、記号の使い方、表組み）は既存ファイルに合わせる。

## 言語

ユーザー対応・ドキュメント・コミットメッセージはすべて**日本語**。
