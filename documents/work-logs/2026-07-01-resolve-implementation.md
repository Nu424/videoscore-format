# 作業ログ: 解決パイプライン（`videoscore.resolve`）の実装

- 日付: 2026-07-01
- 範囲: VideoScore を段階的に具体化する解決系の設計と実装（計画→実装→ドキュメント反映）
- 関連コミット: `820bef2`（設計）→ `e6ad631`（実装）→ 本ログ・README・CLAUDE 反映

## 背景と方針転換

当初は `VideoScore → OTIO → 各種形式` を想定していたが、**VideoScore はスタイル等の意味情報を持つため、
一度 OTIO に落とすとその情報を潰す**（metadata 押し込みは煩雑）。下流 `otio-to-aup2` の未解決論点
（telop 文字列・style・role を OTIO のどこに載せるか／スタイル展開の所在）も同じ問題を抱えていた。

→ フローを **`VideoScore → 解決済み VideoScore → 各種形式（OTIO/aup2…）`** に変更。
解決の出力は VideoScore のまま（時間は具体・スタイルは意味のまま）。仕様書 §7「auto を全部数値に焼けば
完全具体スナップショットにできる（往復可能）」が既にこの概念を予感していた。

## 確定した方針

| 論点 | 決定 | 理由 |
|------|------|------|
| 出力 | 解決済み VideoScore（OTIO 直行しない） | スタイル等の意味情報を保つため |
| 型 | 案A（VideoScore の部分集合＝不変条件）。新型を作らない | §7 の往復思想・既存生成パイプラインに忠実。二重管理回避 |
| 解決の単位 | `Pass = VideoScore→(VideoScore,[Diagnostic])`。`after` 依存でトポロジカルソート | 拡張性（パス追加）・べき等・部分解決・段階出力が一様に手に入る |
| 実体解決の所在 | VideoScore の解決内（絵コンテ→清書の一部）。materialize が時間解決の前提 | 実測長がないと `auto` が解けない |
| 実体解決の拡張 | URI スキーム別 `AssetProvider`（tts/t2i/t2v…） | 種類追加＝プロバイダ1個 register。本体無改造 |
| 実測長 | materialize が **out に補完**して doc 内に残す | 案A・往復可能。time は `auto=start+(out-in)` の算術で済む |
| 失敗 | 例外でなく `Diagnostic` を返す。部分解決を一級市民に | `validate_styles` と同流儀。解けない auto は warning |
| 依存 | resolve は `videoscore.model` のみ（**OTIO 非依存**） | OTIO extra は将来のコンバータ側へ移す |

## 実装した内容

`python/src/videoscore/resolve/`（型/スキーマは増やさない＝ドリフト無影響）:

- `pipeline.py` — `Pass` プロトコル / `topo_order`（`after` 依存の DAG）/ `resolve(doc, ctx=None, *, passes, until)`。
- `providers.py` — `AssetProvider` / `ProviderRegistry`（fallback 可）/ `MockProvider`（開発用スタブ、tts はテキスト長から尺を概算）/ `parse_scheme`。`SYMBOLIC_SCHEMES=(tts,t2i,t2v)`。
- `context.py` — `Diagnostic` / `MaterializedAsset` / `ResolveContext` / `default_context()`（MockProvider 入り）。
- `passes/` — normalize（after→ref 脱糖・先頭after=0・gap→offset 畳み込み・合成id 付与）／materialize（記号 source 実体化＋out 補完）／time_resolve（auto/ref を DFS メモ化で解決・循環検出・合成id 除去）／validate（§7 完全具体・range・記号 source 残存）。

## 検証結果

- pytest: `test_resolve.py` 14件追加、合計 **30件パス**。
- §8 通しサンプルがエラー0で完全解決（時間が全部数値）。フィラー超過（video 尻 > シーン尺）は §3 どおり warning で surface。
- after 脱糖・レーン跨ぎ ref・lane.end 駆動 duration・循環/dangling 診断・未解決 auto（部分解決）・べき等・`until=` 段階出力を確認。
- `videoscore-gen-schema --check` 緑（型を増やしていないためドリフト無し）。

## ファイルマップ

```
documents/resolve-design.md               設計・計画（実装済み表示）
python/src/videoscore/resolve/            pipeline / providers / context / passes/
python/tests/test_resolve.py              解決のテスト（14件）
python/examples/resolve_pipeline.py       一連の流れの実行可能サンプル(.py)
```

## 次の候補

1. **補完パス**の試作（音声→テロップ生成、空フィラー B-roll 充填、多言語清書など）。同じ `Pass` 型で後付け（オプトイン）。
2. **実プロバイダ**（実 TTS・t2i/t2v・実ファイル長プローブ）を `AssetProvider` として追加。
3. **各形式コンバータ** `videoscore.export.*`（`→OTIO` / `→aup2`、スタイルのレシピ展開を含む）。OTIO は extra 側。
