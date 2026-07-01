# VideoScore → aup2 変換設計（`videoscore.export.aup2`）

解決済み VideoScore を AviUtl2 のプロジェクトファイル `.aup2` へ書き出す **最初の形式コンバータ**の設計。
仕様の一次ソースは [`intermediate-structure-guideline.md`](intermediate-structure-guideline.md)、
解決系は [`resolve-design.md`](resolve-design.md)。本書はその下流＝各形式コンバータの第一弾を定める。

> 状況（2026-07-01）: 本設計は **実装済み**（`python/src/videoscore/export/`、テスト
> `python/tests/test_export_aup2.py`、サンプル `python/examples/export_aup2.py`）。v1 スコープ
> （基本4レーン＋代表スタイル）を満たす。フィルタ全種・アニメ・トランジション・OTIO は未着手（§12）。

## 0. 方針（合意済み）

- **入力は解決済み VideoScore、出力は `.aup2`。** 時間は全部具体・source は実ファイル・スタイルは意味のまま、
  という解決済み不変条件（resolve-design §0 案A）を前提にする。未解決（`auto`/`ref`/記号 source 残存）は
  **例外でなく診断**で返す（`resolve` と同流儀）。
- **レシピ展開はコンバータの責務（解決の外）。** 意味的な印（`tone.emphasis` 等）→ AviUtl2 具体エフェクト
  （`縁取り`・`ドロップシャドウ`・X/Y/拡大率…）の展開は、`recipes.aup2.json` を読んでここで行う。
  カタログ三層（意味 `style-catalog.json` ＋実装 `recipes.<editor>.json`、id で握手）の**実装層の初の消費者**。
- **自前の薄いエミッタ（ランタイム依存なし）。** 型・解決系と同じく pydantic のみ依存で通す。`.aup2` の
  シリアライズ（CRLF・UTF-8 BOMなし・日本語プロパティ）は in-repo で実装。参照実装 `aviutl2-api` は
  **dev extra `[aup2-dev]` の往復テストオラクル**に限定する。
- **型・スキーマは増やさない。** レシピ型は `videoscore.export` 層の Python 型として持ち、schema/TS 生成
  パイプラインには載せない（ドリフト検査に無影響）。

## 1. スコープ

| | 含む（v1） | 含まない（将来） |
|---|---|---|
| シーン | scenes を frame オフセットで**単一 `[scene.0]` に連結** | 複数 `scene.N` 分割 / シーン間トランジション（保留10.2） |
| 要素 | video / audio / telop / overlay の基本オブジェクト化 | 入れ子コンポジション（保留10.3） |
| スタイル | 代表印のレシピ展開（`telop.default` / `tone.emphasis` / `position.corner` / `layout.split-*`） | フィルタ全種網羅・語別強調 `highlight`（`{{params.target}}`） |
| レイヤー | レーン別帯＋帯内 interval partitioning による自動割当 | ダッキング等ミキシング・z順の細かな制御（保留10.4） |
| 時間表現 | 静的 `frame=開始,終了` | アニメーション（移動・ベジエ・回転） |
| 出力 | `.aup2` テキスト（＋診断リスト） | プレビュー描画・レンダ |

## 2. `.aup2` 形式の要点（AviUtl2）

INI 風テキスト。**UTF-8 BOMなし・CRLF 必須**。構文は `[セクション]` ＋ `キー=値`、**プロパティ名は日本語**。

```
[project]            version=2001901 / file=<絶対パス> / display.scene=0
[scene.0]            video.width,height / video.rate(=fps) / audio.rate  ← 全体設定はここ
[K]                  layer=<番号> / frame=<開始>,<終了>（両端含む、尺=終-始+1）
[K.0]                メインエフェクト（テキスト/動画ファイル/音声ファイル/画像ファイル/図形）
[K.1]                標準描画（位置X/Y・拡大率・透明度・合成モード）。音声のみ 音声再生（音量/左右）
[K.2]+               追加フィルタ（縁取り・ドロップシャドウ…）
```

- **時間はフレーム整数**。**同一レイヤー・同一時刻に複数オブジェクト不可**（衝突禁止）。
- 座標は画面中央原点・**Y 上が正**・拡大率 %。色は **6桁 hex 文字列**（数値化しない）。パスは**絶対パス**。
- 値の型: 静的数値（2桁小数 `100.00`）／アニメ値（`開始,終了,移動タイプ,パラメータ`）／文字列（フォント名・hex・合成モード）。
- 空プロジェクトは 28 行（`EmptyProject.aup2`）。これを土台に `[K]` 群を後置する。

## 3. 変換マッピング（全体像）

| VideoScore | → | .aup2 |
|---|---|---|
| `meta.fps` / `meta.size` | → | `[scene.0]` の `video.rate` / `video.width,height`（既定 30 / 1920×1080） |
| `scenes[]`（直列・ローカル時計） | → | 単一 `[scene.0]`。scene 開始 = 直前までの scene 尺の累積オフセット |
| 要素 `t=(start,end)` 秒（scene ローカル） | → | グローバル `frame=round((off+s)·fps), round((off+e)·fps)-1` |
| `video`（in/out トリム＋t 配置） | → | `動画ファイル`（`再生位置=in`, `ファイル=絶対パス`）＋`標準描画` |
| `audio`（role） | → | `音声ファイル`（`再生位置=in`）＋`音声再生`。role でレイヤー副帯を分離 |
| `telop`（text） | → | `テキスト`（`テキスト=`＋既定/レシピの装飾）＋`標準描画` |
| `overlay`（画像 or 動画 PiP） | → | `画像ファイル`/`動画ファイル`＋`標準描画`（位置/拡大率はレシピ） |
| `style`（意味的な印） | → | `recipes.aup2.json` を引いてプロパティ・パッチ＋追記フィルタへ展開 |

## 4. 時間モデル（scenes → グローバルフレーム）

- **scene オフセット**: `off(s_i) = Σ_{j<i} duration(s_j)`。解決済みなので `duration` は数値。累積で先頭からの秒位置を出す。
- **秒 → フレーム**: `start_f = round(sec · fps)`、`end_f = round(end · fps) - 1`（**inclusive**）。
  隣接要素（scene 連結・モンタージュ）が 1 フレームも重ならず隙間なく連なる。丸め規則は `common.sec_to_frame` の1箇所に集約。
- **トップレベルレーン（§10.1）**: `VideoScore.video/audio/…` はシーン跨ぎ要素。オフセット 0 の全体トラックとして
  同じ機構で配置する（解決済みなら `t` は数値）。
- 退化ケース: `end_f < start_f`（極端に短い要素）は `end_f = start_f`（最短1フレーム）に丸め、診断 `degenerate-span`（warning）。

## 5. レーン → レイヤー割当

AviUtl2 は「同一レイヤー・同一時刻に複数オブジェクト不可」。これを機械的に満たすため、**レーンごとに帯を割り当て、
帯内では区間分割（interval partitioning）で最小の空きレイヤーへ貪欲割当**する。

| レーン | 基底レイヤー | 副帯（role 等） |
|---|---|---|
| `video` | 0 | — |
| `overlay` | 10 | — |
| `telop` | 20 | — |
| `audio` | 30 | role 順に voice / se / music / ambient で副帯を分ける（重なり許容） |

- **同一レーン内で時間が重ならない要素は同一レイヤーを再利用**（モンタージュ・back-to-back）。
- **重なる要素は帯内の次の空きレイヤーへ自動退避**（同時テロップ＝保留10.4 の当面の既定挙動）。
- 帯が枯渇しても隣の帯を侵さないよう、帯ごとに上限を設けず「基底＋オフセット」で単調増加させ、割当結果を診断に残す。
- 描画順は「番号が大きいほど手前」。video(0–) < overlay(10–) < telop(20–) となり、テロップが最前面に来る。

## 6. スタイル → レシピ展開（`recipes.aup2.json`）

意味的な印を AviUtl2 の具体エフェクトへ展開する。**生の hex/px はここ（レシピ層）に閉じ込める**（AI・中間構造には出さない）。
レシピは「プロパティ・パッチ ＋ 追記フィルタ」の宣言形。

```json
{
  "telop.default": {
    "text": { "フォント": "Yu Gothic UI", "サイズ": 48, "文字色": "ffffff", "文字揃え": "中央[中]" }
  },
  "tone.emphasis": {
    "text": { "文字装飾": "縁取り文字(太)", "影・縁色": "1a4fff" },
    "filters": [ { "name": "ドロップシャドウ", "props": { "影色": "000000", "濃さ": 50 } } ]
  },
  "position.corner": {
    "draw": { "X": "40%w", "Y": "40%h", "拡大率": 30 }
  },
  "layout.split-left":  { "draw": { "X": "-25%w", "拡大率": 50 } },
  "layout.split-right": { "draw": { "X":  "25%w", "拡大率": 50 } }
}
```

- **3つのパッチ口**: `text`（`テキスト` エフェクトのプロパティ上書き）/ `draw`（`標準描画` の上書き）/ `filters`（`[K.2]+` へ追記）。
- **相対値テンプレート**: `"-25%w"` = 幅の -25%、`"40%h"` = 高さの 40%。中央原点・Y 上正へ換算して px 化。生数値はそのまま。
- **既定は `xxx.default`**（カタログの既定値思想）。telop で `style` 未指定なら `telop.default` を当てる。
- **未知 style**: カタログ/レシピに無ければ **warning `unknown-style`** ＋素の既定で描画（例外にしない）。
- **appliesTo 不整合**: `style-catalog.json` を渡した場合、印がそのレーンに適用不可なら warning（`validate_styles` と同じ判定を流用）。
- **v1 非対応**: 語別強調 `highlight`（`{{params.target}}`）は AviUtl2 では表現困難 → warning `unsupported-style`。

レシピは `RecipeBook`（id → 展開規則）としてロードする。同梱の `recipes/recipes.aup2.json` を既定に、
呼び出し側が差し替え・追加できる。

## 7. 要素 → オブジェクト変換（既定プロパティ）

`cli.py` / サンプル `.aup2` の最小構成に準拠（プロパティ名・既定値はそのまま踏襲）。

- **telop → `テキスト` ＋ `標準描画`**: `テキスト=<text>`、フォント/サイズ/色は `telop.default` 由来。改行は `\n` エスケープ。
  中央寄せ・画面中央配置を既定に、`style` パッチで上書き。
- **video → `動画ファイル` ＋ `標準描画`**: `再生位置=<in>`（素材内トリム）、`再生速度=100`、`ファイル=<絶対パス>`。
  配置は `frame`、画面いっぱい（拡大率100・X/Y=0）を既定に。
- **audio → `音声ファイル` ＋ `音声再生`**: `再生位置=<in>`、`ファイル=<絶対パス>`、`音量=100`。role は副帯割当に使う。
- **overlay → `画像ファイル`/`動画ファイル` ＋ `標準描画`**: 拡張子で画像/動画を判定。PiP の位置/縮小は `position.*`/`layout.*` レシピで。
- **色/パス/値**: 色は 6桁 hex 文字列のまま、パスは絶対パス化、数値は 2桁小数で整形（`aviutl2-api` 準拠）。

## 8. 診断（`Diagnostic` を再利用）

`videoscore.resolve.context.Diagnostic` をそのまま使う（export でも同じ型で統一）。主な kind:

| kind | severity | いつ |
|---|---|---|
| `not-resolved` | error | `t`/`duration` に数値でない値（未解決 VideoScore を渡した） |
| `symbolic-source` | error | `tts://` 等の記号 source が残存（未実体化） |
| `unknown-style` | warning | style がカタログ/レシピに無い |
| `unsupported-style` | warning | v1 未対応の印（`highlight` 等） |
| `appliesTo` | warning | 印がそのレーンに適用不可 |
| `degenerate-span` | warning | フレーム換算で尺が 0 以下 → 最短1フレームに丸めた |
| `layer-overflow` | info | 帯内でレイヤーが多段に退避した（同時要素過多の気づき） |

error があっても**可能な範囲で出力は生成**（部分変換）。呼び出し側が error 有無で採否を決める。

## 9. モジュール構成 / 公開 API

```
python/src/videoscore/export/
    __init__.py       公開: render_aup2 / dump_aup2（薄い re-export）
    common.py         sec_to_frame / scene オフセット / LayerAllocator（区間分割）/ Diagnostic 再利用
    recipes.py        Recipe / RecipeBook / load_recipes（recipes.<editor>.json ローダ）/ 相対値テンプレート解決
    aup2/
        __init__.py   render_aup2(doc, *, recipes=None, catalog=None, project_file=None) -> (Aup2Project, [Diagnostic])
                      dump_aup2(doc, path, **kw) -> [Diagnostic]
        model.py      Aup2Project / Aup2Scene / Aup2Object / Aup2Effect（薄い dataclass）
        emit.py       to_text(project) -> str（CRLF/UTF-8）/ 値整形
        defaults.py   要素種ごとの既定エフェクト（テキスト/動画/音声/画像＋標準描画/音声再生）
        convert.py    VideoScore → Aup2Project（本体: scene連結・要素変換・レシピ適用・レイヤー割当・診断）
recipes/recipes.aup2.json   代表印のレシピ実ファイル（初）
python/examples/export_aup2.py   authored → resolve → render_aup2 → .aup2 出力の通しサンプル
```

- `common` は将来の OTIO コンバータと共有（秒→フレーム以外の scene 連結・レイヤー割当は汎用）。
- 公開 API は **`resolve` と同じく `(結果, [Diagnostic])` を返す**。`render_aup2` は入力が未解決でも診断を出して部分変換する。
- 便宜のため `render_aup2(doc, resolve_first=True)` で解決を前段に噛ませられるようにする（既定は False＝解決済み前提）。

## 10. テスト方針

- **通し**: §8 サンプル VideoScore を resolve → render_aup2 して、`.aup2` テキストが生成され frame/レイヤーが期待どおりか。
- **往復オラクル**: 生成した `.aup2` を dev 依存 `aviutl2-api.parse_file` で読み戻し、オブジェクト数・frame・layer が一致（`[aup2-dev]` があるときのみ実行、無ければ skip）。
- **時間**: 秒→フレーム丸め（隣接要素が重ならない）、scene 連結オフセット、退化スパン診断。
- **レイヤー**: 非重複要素の同一レイヤー再利用、重複要素の退避、レーン帯の分離、audio role 副帯。
- **レシピ**: `tone.emphasis` が `文字装飾`＋`ドロップシャドウ` に展開、`layout.split-left` の相対値 px 化、未知 style の warning、既定 `telop.default` 適用。
- **診断**: 未解決入力で `not-resolved`、記号 source で `symbolic-source`。
- 既存テスト（型・スキーマ・ドリフト・resolve）に影響を与えない（型・スキーマを増やさない）。

## 11. 確定事項

| 論点 | 決定 |
|---|---|
| 出力 | `.aup2`（AviUtl2、UTF-8 BOMなし・CRLF・フレーム単位） |
| エミッタ | 自前の薄いエミッタ（ランタイム依存なし）。`aviutl2-api` は dev extra `[aup2-dev]` の往復オラクル |
| レシピ型 | `videoscore.export` 層の Python 型。schema/TS 生成に載せない（ドリフト無影響） |
| シーン | 単一 `[scene.0]` に frame オフセットで連結 |
| 秒→フレーム | `start_f=round(s·fps)` / `end_f=round(e·fps)-1`（inclusive） |
| レイヤー | レーン別帯（video 0–／overlay 10–／telop 20–／audio 30–、role 副帯）＋帯内 interval partitioning |
| レシピ | `text`/`draw`/`filters` の3パッチ口＋相対値テンプレート＋`xxx.default` 既定。生 hex/px はレシピ層に閉じる |
| 失敗 | 例外でなく `Diagnostic`。error があっても部分変換 |
| v1 スコープ | 基本4レーン＋代表スタイル。フィルタ全種/アニメ/トランジション/語別強調は将来 |

## 12. 保留・将来

- **アニメーション**: `標準描画` の値を `開始,終了,移動タイプ,パラメータ` にすれば移動/ベジエ/回転が入る。VideoScore にキーフレーム語彙を足すかは別議論。
- **トランジション**（保留10.2）: シーン継ぎ目の属性として持ち、`[K]` の重なり＋`フェード` 等へ展開。
- **複数 `scene.N`**: 章・別コンポジションを分けたいときの分割出力。
- **ミキシング**: music の voice 下ダッキング（§6）を `音量` アニメ or フィルタで。
- **OTIO コンバータ**: `videoscore.export.otio`（`[otio]` extra）。`common`（scene 連結・レイヤー割当の相当）を共有する。
