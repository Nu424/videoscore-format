# 動画編集 中間構造ガイドライン

絵コンテ的な「構成」を機械可読に記述するための中間表現の仕様書。
実タイムライン（各エディタ形式）の手前に置く、過少指定の中間層を定義する。

---

## 0. 位置づけと方針

パイプライン上の立ち位置：

```
台本 / アウトライン   →   構成（★この中間構造）   →   タイムライン   →   レンダ
```

設計方針は3つ。

1. **時間は具体的に書く。** 「元動画の何秒から何秒」「テロップを何秒表示」を実体値で持つ。
2. **見た目（スタイル）は抽象に保つ。** 具体レシピ（縁取り青2px等）は書かず、意味的な印だけ置く。実装は変換時にカタログから引く。
3. **構造は薄く。** 入れ子（再帰）を持たず、固定された浅い階層で表現する。

---

## 1. 全体構造：scenes と 4レーン

動画は **scenes（シーンの直列リスト）**。
各シーンは **4レーン**（`video` / `audio` / `telop` / `overlay`）を持つ唯一の器。

```jsonc
{
  "meta": { ... },           // title / fps / size / styleCatalog / schemaVersion
  "scenes": [
    {
      "id": "s1",
      "duration": { ... },     // このシーンの尺（どのレーンに従うか）
      "video":   [ ... ],      // 映像クリップ
      "audio":   [ ... ],      // 音声（voice/se/music/ambient）
      "telop":   [ ... ],      // テロップ
      "overlay": [ ... ]       // 画像/動画オーバーレイ
    }
  ]
}
```

1シーン＝1つのローカル時計。シーン内の全要素はこの時計を共有する。

`meta.schemaVersion` には文書が準拠する形式のバージョン（現行 `"0.2.0"`）を書ける（任意）。
部品間（生成・解決・書き出し・プレイヤー）の互換確認に使う。現行値は Python の
`videoscore.SCHEMA_VERSION` / TypeScript の `SCHEMA_VERSION` 定数と同じ。

### ドライバとフィラー

シーン内で、1レーンが**ドライバ**（尺を決める）、残りが**フィラー**（その尺を埋める）。
`duration: { "ref": "audio.end" }` は「このシーンは音声がドライバ」の宣言。
典型は **音声がドライバ（剛体）／映像がフィラー（流体）**。`video.end` を指せば映像ドライバになる。

---

## 2. レーン要素：全レーン同一スケルトン

全レーンの要素は **共通の骨 + レーン固有の差分**。

**共通の骨:**

```jsonc
{ "id": "...", "t": [start, end], "style": "...", "params": {...}, "marks": [...], "annotations": {...} }
```

**レーン固有の差分:**

| レーン | 追加プロパティ | 備考 |
|--------|--------------|------|
| `video` | `source, in?, out?, crop?` | 映像クリップ |
| `audio` | `source, in?, out?, role` | `role` で voice/se/music/ambient |
| `overlay` | `source, in?, out?, crop?` | 画像/動画の PiP |
| `telop` | `text` | 表示文字（source/in/out なし） |

`id` `style` `params` `marks` `annotations` は任意。`id` は他から参照される要素にのみ振る。

### `crop`（映す領域）

`video` / `overlay` は `crop: [x, y, w, h]` で**元フレームのどこを映すか**を持てる（v0.2.0〜）。

- 値は元フレームに対する **0〜1 の比率**（左上原点）。`0 ≤ x, y`、`w, h > 0`、`x + w ≤ 1`、`y + h ≤ 1`。
- **静的な切り抜きのみ**（時間で動くパンは将来）。
- 意味は「切り出した領域が映る」ことだけ。**領域をフレームへどう収めるか**（全面に拡大・帯付きで縮小・位置）は
  スタイル（`layout.*` の印）とレシピが決める。
- 見た目ではなく**内容に依存するデータ**（被写体がどこにいるか）なので、style の `params` ではなく要素の項目にする。

```jsonc
{ "source": "talk.mp4", "in": 12, "out": 20, "t": [0, "auto"],
  "crop": [0.34, 0, 0.32, 1], "style": "layout.vertical-crop" }   // 16:9 の中央縦長帯を 9:16 に
```

### `annotations`（注記）

全レーン要素と `scene` は自由な object `annotations` を持てる（v0.2.0〜）。根拠の参照
（`{"refs": ["src_01#ev_0042"]}`）、候補 ID、メモなど、**構成を作った側の文脈**を置く場所。

- 中身の形は決めない（任意のキー・入れ子可）。
- **解決（resolve）と書き出し（export）は解釈しない。** 解決済み VideoScore にもそのまま残る（素通し）。
- **`marks` を注記に流用しない。** `marks` は時間アンカー（参照される時刻の名前）用で、意味が違う。

### `t`（配置）と `in`/`out`（トリム）

2つの時間概念を別名で持つ。

- **`t: [start, end]`** … シーン時計上の**配置**（いつ出て、いつ消えるか）。全レーン共通。
- **`in` / `out`** … 素材内の**トリム**（元素材の何秒〜何秒を使うか）。media を持つレーンのみ。

```jsonc
"video": [
  { "source": "a.mp4", "in": 5, "out": 12, "t": [0, "auto"] }
  //                    ↑素材5-12秒        ↑シーン0秒から配置（auto = out-in = 7秒）
]
```

### この統一が表せるもの

- `t: ["after", "auto"]` を並べる → 映像の**back-to-back モンタージュ**
- `t: [0, "auto"]` を2本重ねる → **スプリットスクリーン**（レイアウトは layout 系の style 印で表す）

→ par のような構造ノードは持たない。「同時併置」は重ね＋style 印で表現する。

---

## 3. 時間モデル

### ローカル具体時刻

時間は **シーン基準のローカル秒**を**具体値**で持つ。
各シーンが自己完結するので、並べ替え・挿入で時刻を書き直さなくて済む。
絶対時刻は前シーンまでの尺を足し上げて算出できる（情報は失われない）。

同期は自動：同じシーン時計上で `telop:[3.0,7.0]` と `audio:[2.5,8.0]` は数字が重なる＝同期している。

### 時間スロットの4語彙

`t` の `start` / `end` に書ける値：

| 値 | 意味 | 用途 |
|----|------|------|
| 数値（例 `3.2`） | 具体時刻 | **既定** |
| `"auto"` | 自分の固有尺 | TTS 実測長・素材長・画像の既定表示時間・`out - in` |
| `"after"` | 同レーンの直前要素の `end` | 同レーン連結 |
| `{ "ref": "id.end", "offset": 0.2 }` | 他要素のマーク参照 | レーン跨ぎ同期 |

### 循環を防ぐ鉄則

> **`start` は常に「具体 or 参照」。派生してよいのは `end`（＝尺）だけ。**

これで時間依存に循環が生じ得ず、解決は **DAG のトポロジカルソート**で済む（循環したらエラー）。

### `"after"`：同レーン連結

```jsonc
"audio": [
  { "role": "voice", "source": "tts://今日は",     "t": [0,       "auto"] },
  { "role": "voice", "source": "tts://重要な話を", "t": ["after", "auto"] },
  { "role": "voice", "source": "tts://します",     "t": ["after", "auto"] }
]
```

- 定義：**同レーン・リスト順で直前の兄弟の `end`**（時間順ではなくリスト順に固定）
- 挿入に強い（相対参照なので間に挟めば勝手にズレる）／id 不要
- 先頭の `"after"` は **0 扱い**
- ギャップは `["after", "auto", { "gap": 0.3 }]`
- 実装上は入口で `{ ref: "<前要素>.end" }` に脱糖すれば既存解決をそのまま使える

### 使い分け

> 縦に詰める（同レーン）＝ `"after"` ／ 横で合わせる（レーン跨ぎ）＝ `"ref"` + id

### レーン参照：`audio.end` / `video.end`

> **`レーン.end` = そのレーン内の全要素の `end` の最大値**

`duration` やレーン跨ぎの基準に使える。最後の要素に id を振らずに済む。

### シーン尺と素材尻のズレ

`duration` が伸びてフィラーの素材長が足りない／余る場合の挙動（凍結・ループ・スロー・カット）は
**レシピ/方針の領域**で、中間構造には書かない。**配置 `t` が実使用尺、`out` は素材上限のキャップ**として扱う。

### 可視範囲

`ref` の参照先は**同じシーン内**に限る。シーン跨ぎは §7.1 で扱う。

---

## 4. スタイル（意味的な印）

### 原則：印は「見た目」でなく「意味」で名付ける

```
✗ "blue-outline-2px-shadow"   ← 名前に実装が漏れている
◯ "emphasis"                  ← 何のためか、だけを言う
```

リトマス試験：名前から見た目を一意に当てられたらアウト（`warning` は健全、`red-big` は漏れている）。

### params

印に意味的な引数を渡せる。**生の px / hex は禁止。**

```jsonc
"style": "highlight",
"params": { "target": "重要" }     // ◯ 意味（どの語か）
// "params": { "color": "#ff0000" } // ✗ レシピが漏れている
```

型は意味カタログで宣言、実装はレシピで定義する。

### 1要素 = 1印

複数印のカスケード（重ね合わせ）は採用しない。重ねを許すと「印の組み合わせでレシピを直書き」に化けるため。
レイアウト（スプリット位置等）も layout 系の印を1つ付けるだけで表す。

---

## 5. スタイルカタログ

三層構成。構造は印を**参照するだけ**、カタログが**意味と実装の橋**、コンパイラが各エディタへ展開する。

### ファイル分割：意味1枚 + レシピをエディタ別に N 枚

| ファイル | 中身 | 誰が読むか |
|---------|------|-----------|
| `style-catalog.json` | `id` `intent` `feeling` `appliesTo` `params`型 `example` | **AI と検証器** |
| `recipes.<editor>.json` | `id → そのエディタでのレシピ` | **コンパイラ**（出力先のものだけ） |

三者は **`id`（結合キー）だけ**で握手する。

- AI にはレシピを見せない（具体値を構造に書き出す誘惑を断つ）
- エディタ追加 = レシピファイルを1枚足すだけ
- 意味ファイルから AI/人間向け説明書を自動生成できる

### 既定値も印として持つ

`telop.default` `audio.default` 等を1エントリ置く（「常にどれか1つの印を引く」に統一、SoT 化）。

### AI 生成に効く点

1. **閉じた集合（enum）** … カタログにある印しか選べない（捏造防止）
2. **`intent` / `feeling` は「いつ・どんな気分で使うか」で書く** … セリフの意味からマッチできる
3. **`appliesTo` で適用先を絞る** … 検証でも弾ける

### `style-catalog.json` の例（意味の層）

```json
{
  "styles": {
    "telop.default": {
      "intent": "通常のテロップ。特別な強調がないとき。",
      "feeling": "標準・中立",
      "appliesTo": ["telop"],
      "params": null,
      "example": "ふつうの説明字幕"
    },
    "tone.emphasis": {
      "intent": "視聴者に一番伝えたい一言。目を引かせたいとき。",
      "feeling": "強い・はっきり・前に出る",
      "appliesTo": ["telop"],
      "params": null,
      "example": "決め台詞"
    },
    "highlight": {
      "intent": "テロップ内の特定の語だけを際立たせたいとき。",
      "feeling": "部分的に目を引く",
      "appliesTo": ["telop"],
      "params": { "target": { "type": "string", "desc": "強調する語" } },
      "example": "「ここが【重要】です」の重要だけ"
    },
    "position.corner": {
      "intent": "ロゴや補助情報を隅に小さく置きたいとき。",
      "feeling": "控えめ・常駐",
      "appliesTo": ["overlay"],
      "params": null,
      "example": "右上のチャンネルロゴ"
    },
    "layout.split-left": {
      "intent": "スプリットスクリーンの左側に配置したいとき。",
      "feeling": "並列・対比",
      "appliesTo": ["video"],
      "params": null,
      "example": "ビフォーアフターの左"
    },
    "audio.default": {
      "intent": "通常の音声。加工なし。",
      "feeling": "素の音",
      "appliesTo": ["audio"],
      "params": null,
      "example": "そのままのナレーション"
    }
  }
}
```

### 標準カタログ（v0.2.0〜）

どのプロジェクトでもまず使える最小セットを「標準カタログ」として同梱する
（`python/src/videoscore/catalogs/standard/style-catalog.json`。Python は `videoscore.catalogs.standard_catalog()`、
TypeScript は `STANDARD_STYLE_CATALOG` / `StandardStyleId`）。プロジェクトは独自のカタログで上書き・追加できる
（`merge_catalogs`）。

| id | いつ使うか（要約） | appliesTo |
|----|------------------|-----------|
| `telop.default` | 特別な役割のない通常テロップ | telop |
| `telop.caption` | 発話を文字でも追わせる字幕（短い塊で順に出す） | telop |
| `telop.title` | 冒頭で「何の動画か」を一言で示す | telop |
| `tone.emphasis` | 一番伝えたい一言を目立たせる | telop |
| `layout.vertical-fit` | 横長素材を切らずに縦長画面へ収める（上下の空きはタイトル・字幕の置き場） | video, overlay |
| `layout.vertical-crop` | 素材の注目部分（`crop`）だけを縦長画面いっぱいに見せる | video, overlay |
| `audio.default` | 加工なしの音声 | audio |
| `position.corner` | ロゴ等を隅に小さく常駐させる | overlay |

各エディタのレシピは標準カタログの全 id を揃える（§7 網羅）。

### `recipes.premiere.json` の例（実装の層）

```json
{
  "tone.emphasis": {
    "fontStyle": "bold",
    "stroke": { "color": "#1a4fff", "width": 2 },
    "effects": ["dropShadow"]
  },
  "highlight": {
    "perWordOverride": { "match": "{{params.target}}", "color": "#ffd400" }
  },
  "layout.split-left": {
    "transform": { "x": "-25%", "scale": 0.5 }
  }
}
```

---

## 6. audio の role

| role | 用途 | コンパイラ側の扱い |
|------|------|------------------|
| `voice` | ナレーション・セリフ | 尺=発話長を実測して公開（アンカー生成の既定対象） |
| `se` | 効果音 | — |
| `music` | BGM | `voice` の下で自動ダッキング |
| `ambient` | 環境音 | — |

role ごとに別トラックへ振り分ける。スタイル印も audio に乗る（`audio.phone` 等）。

---

## 7. 検証ルール

| チェック | 内容 |
|---------|------|
| 時間範囲 | `t:[start,end]` が `0 ≤ start < end ≤ シーン尺` を満たす |
| enum | `style` がカタログに存在する id |
| appliesTo | 印がそのレーンに対応している |
| 網羅 | 意味ファイルの全 id が各 `recipes.<editor>.json` に揃っている |
| 循環 | 時間依存に循環がない（DAG が解ける） |
| 可視範囲 | `ref` の参照先が同じシーン内にある |
| crop | `video`/`overlay` の `crop:[x,y,w,h]` が `0 ≤ x,y`、`w,h > 0`、`x+w ≤ 1`、`y+h ≤ 1` を満たす（型で検査） |
| annotations | 形は検査しない（自由な object）。resolve / export は無視して素通しする |
| auto の責任 | 実測できない素材に `auto` が付いていたら「尺確定フェーズ要」のフラグを立てる |

> `auto` を全部数値に焼けば「完全具体」のスナップショットにもできる（情報は失われず往復可能）。

---

## 8. 通しサンプル（全要素入り）

解説用に JSONC 表記。実運用では標準 JSON。

```jsonc
{
  "meta": {
    "title": "サンプル動画",
    "fps": 30,
    "size": [1920, 1080],
    "styleCatalog": "style-catalog.json"
  },

  "scenes": [

    // ===== シーン1：TTS 駆動。音声がドライバ、映像がフィラー =====
    {
      "id": "s1",
      "duration": { "ref": "audio.end" },
      "video": [
        { "source": "broll.mp4", "in": 5, "out": 12, "t": [0, "auto"] }
      ],
      "audio": [
        { "id": "v1", "role": "voice", "source": "tts://今日は",     "t": [0,       "auto"] },
        { "id": "v2", "role": "voice", "source": "tts://重要な話を", "t": ["after", "auto"] },
        {            "role": "voice", "source": "tts://します",     "t": ["after", "auto"] }
      ],
      "telop": [
        { "t": [0,                     { "ref": "v1.end" }], "text": "今日は",     "style": "tone.emphasis" },
        { "t": [{ "ref": "v2.start" }, { "ref": "v2.end" }], "text": "重要な話を", "style": "tone.emphasis" }
      ],
      "overlay": [
        { "source": "logo.png", "t": [0.5, "auto"], "style": "position.corner" }
      ]
    },

    // ===== シーン2：back-to-back モンタージュ + カット跨ぎテロップ =====
    {
      "id": "s2",
      "duration": { "ref": "video.end" },
      "video": [
        { "source": "a.mp4", "in": 0,  "out": 4,  "t": [0,       "auto"] },
        { "source": "b.mp4", "in": 10, "out": 13, "t": ["after", "auto"] }
      ],
      "telop": [
        { "t": [1.0, 6.0], "text": "カットを跨ぐテロップ", "style": "telop.default" }
      ],
      "audio": [
        { "role": "se", "source": "whoosh.wav", "t": [3.5, "auto"] }
      ]
    },

    // ===== シーン3：スプリットスクリーン + オーバーレイ動画 =====
    {
      "id": "s3",
      "duration": 5,
      "video": [
        { "source": "left.mp4",  "in": 0, "out": 5, "t": [0, "auto"], "style": "layout.split-left"  },
        { "source": "right.mp4", "in": 0, "out": 5, "t": [0, "auto"], "style": "layout.split-right" }
      ],
      "telop": [
        { "t": [0.5, 4.5], "text": "比較", "style": "tone.emphasis" }
      ],
      "overlay": [
        { "id": "pip1", "source": "insert.mp4", "in": 2, "out": 6, "t": [1.0, "auto"], "marks": ["pip_end"] }
      ]
    }

  ]
}
```

### サンプルの読みどころ

| 箇所 | 何を示すか |
|------|-----------|
| s1 `duration:{ref:"audio.end"}` | レーン参照で尺を音声に従わせる（音声ドライバ） |
| s1 `"after"` 連結 | 同レーンの連結。id は外部参照される要素のみ |
| s1 telop の `{ref:"v1.end"}` | レーン跨ぎ同期 |
| s1 video の `in/out` と `t` | トリムと配置の語彙分離 |
| s2 video の `t:["after","auto"]` | back-to-back モンタージュ |
| s2 跨ぎ telop | カット境界を越えるテロップが自動で解ける |
| s3 video 2本を `t:[0,...]` で重ね | スプリット（layout 印で表現） |
| s3 `pip1` overlay 動画 | 素材トリム付きオーバーレイ + mark |

---

## 9. 設計判断の早見表

| 論点 | 方針 | 理由 |
|------|------|------|
| 全体構造 | scenes（直列）+ 4レーン、再帰なし | 薄く・AIに扱わせやすい |
| 時計 | 1シーンに1つのローカル時計 | カット跨ぎ等が自動で解ける |
| 配置 vs トリム | `t`（配置）と `in`/`out`（トリム）で分離 | start/end の2義衝突を回避 |
| レーン要素 | 全レーン同一スケルトン | AIに「この形を埋めろ」で済む |
| 同時併置（par 相当） | 重ね + layout 印 | レイアウトは style の領分 |
| 時間 | ローカル具体時刻 | 編集に強い |
| 時間語彙 | 数値 / auto / after / ref | start は具体、派生は end のみ → 循環不能 |
| シーン尺 | `duration` がドライバのレーンを名指し | 剛体/流体の役割を明示 |
| スタイル | 意味で名付ける | 具体レシピを構造から排除 |
| 重ね合わせ | 不採用（1要素=1印） | 重ね＝レシピ直書きに化けるため |
| カタログ | 意味1枚 + レシピ N 枚（id で握手） | AIに意味だけ見せる |
| 既定値 | `xxx.default` を持つ | 分岐統一・SoT 化 |
| 音声 | `audio` + `role` | 同じ骨で扱い、差は role に逃がす |
| 切り抜き | `crop:[x,y,w,h]`（比率・静的）を video/overlay の項目に | 映す場所は内容依存のデータ。収め方は layout 印 |
| 注記 | `annotations`（自由 object、resolve/export は無視） | 根拠・候補 ID を運ぶ。`marks`（時間アンカー）と分ける |
| 版 | `meta.schemaVersion`（任意の文字列） | 部品間の互換確認 |

---

## 10. 保留事項

### 10.1 トップレベルレーン（シーン跨ぎ要素）

**課題：** `scenes` がフラットで上に器がないため、全体 BGM やシーン跨ぎテロップの置き場がない。

**対応アイデア（推奨）：** scenes の1段上に、**シーンと同じ形の4レーン**を置く。

```jsonc
{
  "meta": { ... },
  "audio":   [ { "role": "music", "source": "bgm.mp3", "t": [0, { "ref": "scenes.end" }] } ],
  "video":   [ ... ],
  "telop":   [ ... ],
  "overlay": [ ... ],
  "scenes":  [ ... ]
}
```

レーンの概念が「全体」「シーン」の2スコープで同じ形になり、薄さを保ったまま跨ぎが解ける。
全体スコープの原点は動画先頭、`scenes.end`（全シーン尺の合計）を参照可能にする。
可視範囲は分離（全体レーンの `ref` は全体内に閉じ、シーン内部 id は参照しない）。

### 10.2 トランジション

シーン間トランジションは `scenes[i]` と `scenes[i+1]` の**継ぎ目の属性**として持つ。
独立ノードにはせず、継ぎ目から両隣の N 秒を「借りる」扱いにする。

### 10.3 入れ子コンポジション

overlay 動画の中でさらに scenes を組む再帰は未対応。
必要なら overlay 要素に `scenes` を持たせ、局所的に再帰を許す（全体の薄さは保つ）。

### 10.4 重なるテロップ

同レーンで時間的に重なる場合の z 順は未定義。
必要になったらレーンを「サブレーンのリスト（各 z順付き）」へ昇格する。

### 10.5 スタイル継承

シーンの印を子要素が継ぐカスケードは未対応。当面「レーン既定 → 要素の明示印で上書き」の1段のみ。
