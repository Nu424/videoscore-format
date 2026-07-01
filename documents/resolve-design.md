# VideoScore 解決スクリプト設計（`videoscore.resolve`）

絵コンテ的な VideoScore（過少指定）を、段階的に清書方向へ具体化する **解決パイプライン**の設計。
仕様の一次ソースは [`intermediate-structure-guideline.md`](intermediate-structure-guideline.md)。本書はその解決系の設計を定める。

> 状況（2026-07-01）: 本設計は **実装済み**（`python/src/videoscore/resolve/`、テスト `python/tests/test_resolve.py`、
> サンプル `python/examples/resolve_pipeline.py`）。本スコープ（収束4パス＋mock プロバイダ）を満たす。
> 補完パス・実プロバイダは未着手（§6・§1）。各形式コンバータは第一弾 aup2 を実装済み
> （`videoscore.export.aup2`、設計は [`export-aup2-design.md`](export-aup2-design.md)）。

## 0. 方針（合意済み）

- **出力は VideoScore（OTIO ではない）。** VideoScore はスタイル等の意味情報を持つため、一度 OTIO に落とすと
  その情報を潰す。流れを `VideoScore → 解決済み VideoScore → 各種形式（OTIO/aup2…）` に変える。
  各種形式へのコンバータ（スタイルのレシピ展開を含む）は**解決の外**＝将来の別モジュール。
- **型は案A。** 解決の入出力は一貫して `VideoScore`。「解決済み」は新しい型ではなく
  **VideoScore の部分集合（＝時間が全部具体・スタイルは意味のまま）という不変条件**で表す（§7「完全具体スナップショット」）。
- **解決＝VideoScore→VideoScore のパスの列。** 各「解決」を、ドキュメントを一段だけ具体化する独立した
  **パス**として実装し、依存順（トポロジカルソート）で回す。時間 ref の DAG と相似の構造。

## 1. スコープ

| | 含む | 含まない（将来 / 別モジュール） |
|---|---|---|
| パス | normalize / materialize / resolve-time / validate-resolved | 補完パス（音声→テロップ生成、B-roll 自動充填、多言語清書…） |
| プロバイダ | mock（実体化のスタブ）1種 | 実 TTS・t2i・t2v・ストック検索・実ファイル長プローブ |
| 出力 | 解決済み VideoScore（JSON） | OTIO / aup2 等への変換（コンバータ＝L4） |

「解決」のレベルは番号より**名前付きパスの順序**で考える。実体解決（materialize）が時間解決（resolve-time）の前提
（実測長がないと `auto` が解けない）。

```
authored
  → normalize        after→ref 脱糖 / 先頭after=0 / gap 畳み込み
  → materialize      記号 source（tts://…）→ 実体。素材長を採取し out を補完
  → resolve-time     auto/ref を DAG で具体秒へ。scene.duration も確定
  → validate-resolved  完全具体・参照健全・時間範囲（§7）を表明
  = 解決済み VideoScore（スタイルは意味のまま）
```

## 2. アーキテクチャ

### 2.1 パス（コンポーネントの単位）

各パスは `VideoScore → (VideoScore, [Diagnostic])`。並行の拡張点はこの単位。

```python
class Pass(Protocol):
    name: str
    after: tuple[str, ...]                  # 先行すべきパス名（順序制約）
    def applicable(self, doc) -> bool       # まだ仕事が残っているか（べき等・部分解決の鍵）
    def run(self, doc, ctx) -> tuple[VideoScore, list[Diagnostic]]
```

- **順序**: 各パスが `after` で依存宣言 → トポロジカルソート。`DEFAULT_PASSES` は既定の収束パイプライン。
- **べき等・部分解決**: `applicable()` が「やることが残っているか」を返すので `resolve(resolve(x)) == resolve(x)`。
  途中で止める（`until=`）・一部だけ流す・再開、が同じ仕組みで成立。どの段階の出力も妥当な VideoScore。
- **失敗の流儀**: 例外でなく `Diagnostic` を返す（`validate_styles` と同じ）。解けない `auto` 等は
  「エラー」でなく「部分解決＋フラグ」（§7「尺確定フェーズ要」）。

### 2.2 素材プロバイダ（実体解決の拡張点）

`materialize` パスは source の **URI スキームでプロバイダへ委譲**するディスパッチャ。
`tts://` `t2i://` `t2v://` … はすべて「記号 spec → 素材生成」という同じ形。

```python
class AssetProvider(Protocol):
    schemes: tuple[str, ...]                # "tts" / "t2i" / "t2v" / …
    def materialize(self, source, ctx) -> MaterializedAsset   # {path, intrinsic_seconds, kind}
```

- **拡張 = プロバイダを1個 register するだけ**。materialize 本体も resolve-time も無改造。
- **実測長は materialize の副産物**として採取し、`out` が未指定の media 要素に **`out = intrinsic_seconds` を補完**する。
  これで素材長がドキュメント内に残り（案A・往復可能）、resolve-time は `auto = start + (out - in)` の算術で済む。
- 本スコープは `MockProvider` のみ（tts はテキスト長から秒を概算、その他は既定秒）。実プロバイダは将来。

### 2.3 コンテキスト

`ResolveContext` が共有サービスを持つ: プロバイダ登録簿 / 生成素材の置き場 `asset_dir` /
診断リスト / 設定（画像の既定表示秒など）。`default_context()` は MockProvider を入れて返す。

## 3. 時間解決アルゴリズム（resolve-time）

シーンは独立（ローカル時計）。`ref` は同一シーン内に限る（§3 可視範囲）。

- **スロット**: 各要素の `start` / `end`、各レーンの `lane.end`（＝そのレーン要素 end の最大）、`scene.duration`。
- **依存**:
  - `start`: 数値（確定）/ `RefObject`（`X.start|X.end|lane.end` ＋ offset を参照）。
  - `end`: 数値 / `"auto"`（＝ `start + 固有尺`、固有尺は materialize 後の `out - in`）/ `RefObject`。
  - `lane.end`: そのレーン全要素の `end` に依存。
  - `scene.duration`: 数値、または `lane.end` 参照。
- **解法**: メモ化 DFS でスロットを評価。訪問中スタックに戻ったら**循環**（§7）として診断。
- **トップレベルレーン（§10.1）**: 全シーン確定後に `scenes.end = Σ scene.duration` を与え、同じ機構で解く。
- 解決後、各要素の `t` を `(start, end)` の数値タプルへ書き戻す。`normalize` が振った合成 id は除去。

## 4. 検証（validate-resolved）

解決済み形で初めて完全に効く（§7）:
- `t` の start/end・`duration` がすべて数値（auto/after/ref/symbolic source の残存を検出＝部分解決フラグ）。
- `ref` がすべて解決済み（dangling 検出）。
- `0 ≤ start < end ≤ scene.duration`、`lane.end ≤ duration` の範囲。

## 5. モジュール構成

`videoscore.resolve` は `videoscore.model` にのみ依存（**OTIO 非依存**）。OTIO は将来のコンバータ側の extra に移す。

```
python/src/videoscore/resolve/
    __init__.py        公開 API: resolve / ResolveContext / default_context / Diagnostic
                                 / DEFAULT_PASSES / AssetProvider / MockProvider / MaterializedAsset
    context.py         Diagnostic, MaterializedAsset, ResolveContext, default_context
    pipeline.py        Pass, topo_order, resolve()
    providers.py       AssetProvider, ProviderRegistry, MockProvider, parse_scheme
    passes/
        __init__.py    DEFAULT_PASSES
        normalize.py
        materialize.py
        time_resolve.py
        validate.py
```

CLI は当面付けない（`resolve()` 関数 API のみ）。スキーマ生成物（schema/・TS）には影響しない
（解決系は型を増やさず、既存 VideoScore 型の上で動く）。

## 6. 収束パスと補完パス（将来の一般化）

`Pass = VideoScore → VideoScore` なので、値を具体化する**収束パス**（normalize/materialize/resolve-time）と、
要素を増やす**補完パス**（音声→テロップ、空フィラー自動充填、多言語清書、A/B 清書…）を同じ型で扱える。
**既定パイプラインは収束のみ**、補完はオプトイン（生成的で副作用が大きいため）。本スコープでは収束4パスのみ。

## 7. テスト方針

- §8 通しサンプルを normalize→materialize（mock）→resolve-time に通し、`t`・`duration` が全部数値になることを確認。
- 鉄則・循環: ref の循環で循環診断、未解決 auto で部分解決診断。
- べき等: `resolve(resolve(x)) == resolve(x)`。
- `until=` で段階出力（normalize 後に after が消えている等）。
- 既存テスト（型・スキーマ・ドリフト）に影響を与えない。

## 8. 確定事項

| 論点 | 決定 |
|------|------|
| 出力 | 解決済み VideoScore（OTIO 直行はしない） |
| 型 | 案A（VideoScore の部分集合＋不変条件）。新型を作らない |
| 解決単位 | パス（VideoScore→VideoScore）。`after` 依存＋トポロジカルソート |
| 実体解決 | URI スキーム別の AssetProvider。実測長を out に補完して採取 |
| 失敗 | 例外でなく Diagnostic。部分解決を一級市民とする |
| 本スコープ | normalize / materialize（mock）/ resolve-time / validate-resolved の4パス＋実行器 |
| コンバータ | 将来このリポジトリ内（`videoscore.export.*`、OTIO は extra）。今回は未実装 |
