# videoscore-remotion

**解決済み VideoScore** を Remotion で再生・書き出すプレイヤー（再利用部品）。
制作ごとにタイムライン解釈器を書かず、`videoscore.resolve` の出力をそのまま props で渡して描画する。

```
VideoScore（絵コンテ） → videoscore.resolve → 解決済み VideoScore ──(--props)──► <VideoScoreComposition>
```

- シーンは `<Sequence>` で直列に並べる（開始 = 直前までのシーン尺の累積）。トップレベルレーンは動画全体の時計で置く。
- 描画順（奥→手前）: `video` → `overlay` → `telop`。`audio` は `<Audio>`。
- 映像は `<OffthreadVideo>`（`in`/`out` → `trimBefore`/`trimAfter`、フレーム換算）。**映像は無音で再生する**
  （VideoScore は音を `audio` レーンに分けて持つため。元音声を使うなら同じ区間の `audio` 要素を置く）。
- 画像（拡張子で判定）は `<Img>`。
- 見た目はスタイルの印 → `recipes.remotion.tsx` のレシピで決める（**カタログと同じ id で結合**。aup2 の
  `recipes.aup2.json` と同じ考え方）。未知の印は既定で描いて `console.warn`。
- `crop`（`[x, y, w, h]` 比率）は、素材を overflow: hidden の箱の中で拡大・位置合わせして表現する。
  どの箱にどう収めるか（contain / cover）は `layout.*` レシピが決める。
- 未解決の値（`auto`/`ref`/`after`/gap、`tts://` 等の記号 source）が残っていれば、描画せずエラー画面を出す。

## 公開 API（`videoscore-remotion`）

| 名前 | 種別 | 内容 |
|------|------|------|
| `VideoScoreComposition` | React コンポーネント | 解決済み VideoScore を描画する本体。props は `VideoScoreCompositionProps` |
| `calculateMetadata` | `CalculateMetadataFunction` | 尺・fps・サイズを VideoScore から決め、`sourceSizes` の欠けを実測で補う |
| `makeCalculateMetadata({ resolveSrc?, probe? })` | 関数 | `resolveSrc` を差し替えた calculateMetadata を作る |
| `videoScoreMetadata(score)` | 関数 | 尺・fps・サイズだけを計算（純粋関数） |
| `standardRemotionRecipes` | `Record<StandardStyleId, RemotionRecipe>` | 標準カタログの全 id のレシピ（型で網羅を担保） |
| `TelopDefault` / `TelopCaption` / `TelopTitle` / `TelopEmphasis` | React コンポーネント | telop レシピの部品（自前レシピから再利用可） |
| `makeDefaultResolveSrc(mediaBase?)` / `defaultResolveSrc` | 関数 | 既定の source → URL 解決 |
| `findUnresolved(score)` | 関数 | 未解決箇所の一覧（空なら解決済み） |
| `placeMedia(size, crop, box, fit)` | 関数 | crop・配置の計算（純粋関数） |

### props

```ts
// JSON で渡せる部分（--props / Studio の入力 props）
type VideoScoreInputProps = Partial<VideoScore> & {
  score?: VideoScore                        // 解決済み VideoScore
  mediaBase?: string                        // 相対 source の前に付ける public/ 内のディレクトリ（例 "media/"）
  sourceSizes?: Record<string, [number, number]>  // source → 素材の画素サイズ（無ければ実測、失敗時は 16:9 と仮定）
}
// コードから使うときに足せるもの
type VideoScoreCompositionProps = VideoScoreInputProps & {
  resolveSrc?: (source: string) => string   // 既定: http(s)/data/blob はそのまま、相対パスは staticFile(mediaBase + path)
  recipes?: RemotionRecipeBook              // 既定: standardRemotionRecipes
}
```

props は `{ "score": <解決済み VideoScore> }` のほか、**解決済み VideoScore そのもの**（`{ "meta": …, "scenes": […] }`）
でもよい（`scenes` があればそちらを優先）。

### 標準カタログのレシピ

| 印 | Remotion での表現 |
|----|------------------|
| `telop.default` | 下寄り中央、白文字＋黒縁 |
| `telop.caption` | 大きな太字＋太い縁取り。下の帯（縦型は下から 14%、横型は 7%） |
| `telop.title` | 上の帯に太字＋半透明の座布団、軽いフェードイン |
| `tone.emphasis` | 中央に大きく、黄色＋縁取り＋弾む出現 |
| `layout.vertical-fit` | フレーム全体に contain（16:9 を 9:16 に入れると幅合わせで中央、上下は暗い帯） |
| `layout.vertical-crop` | `crop` 領域（未指定なら中央）でフレームを cover |
| `audio.default` | 音量 1 |
| `position.corner` | 右上に、フレーム短辺 18% の箱へ contain |

大きさはフレーム寸法に対する比率で書いてあるので、横型・縦型のどちらでも使える。
プロジェクト固有の印は `recipes={{ ...standardRemotionRecipes, 'my.style': { Telop: MyTelop } }}` で足す。

## 本番プロジェクトへの導入

Remotion プロジェクト（`remotion` / `@remotion/cli` を **4.0.529** に固定）に、pnpm の git サブディレクトリ指定で入れる
（TS 型パッケージと同じ方式）。

```bash
pnpm add "Nu424/videoscore-format#path:/typescript" "Nu424/videoscore-format#path:/remotion"
pnpm add -E remotion@4.0.529 @remotion/cli@4.0.529 react react-dom
```

このパッケージは **TypeScript ソースのまま配布**する（ビルド工程なし）。Remotion のバンドラは `node_modules` 内の
`.ts/.tsx` もトランスパイルするので、そのまま import できる。`videoscore`（TS 型）は型のためだけの peer 依存
（実行時には読まない）。

```tsx
// src/Root.tsx（本番プロジェクト）
import { Composition } from 'remotion'
import { VideoScoreComposition, calculateMetadata } from 'videoscore-remotion'

export const Root = () => (
  <Composition
    id="VideoScore"
    component={VideoScoreComposition}
    calculateMetadata={calculateMetadata}
    defaultProps={{ mediaBase: 'media/' }}
    fps={30} width={1920} height={1080} durationInFrames={1}  // 仮。calculateMetadata が上書きする
  />
)
```

### props を渡す（`--props=resolved.json`）

Python 側で解決して JSON に書き出す:

```python
import json
from videoscore.model import VideoScore
from videoscore.resolve import resolve

doc = VideoScore.model_validate_json(open("videoscore.json", encoding="utf-8").read())
resolved, diags = resolve(doc)   # error 診断が無いことを確認してから渡す
with open("videoscore.resolved.json", "w", encoding="utf-8") as f:
    json.dump(resolved.to_json_dict(), f, ensure_ascii=False, indent=2)
```

```bash
npx remotion studio  src/index.ts --props=videoscore.resolved.json
npx remotion still   src/index.ts VideoScore out/check.png --frame=30 --props=videoscore.resolved.json
npx remotion render  src/index.ts VideoScore out/video.mp4 --props=videoscore.resolved.json
```

`mediaBase` や `sourceSizes` も渡したいときは `{ "score": …, "mediaBase": "media/", "sourceSizes": {…} }` の形の JSON にする。

### 素材の置き場（public/ へのステージング）

- 要素の `source` は**論理パス**（例 `clips/a.mp4`）として書き、実体はプロジェクトの `public/`（`mediaBase` を
  使うなら `public/media/`）の下に同じ相対パスで置く。既定の解決は `staticFile(mediaBase + source)`。
- 原本は動かさず、ハードリンクかコピーで `public/media/` に並べる（ステージング）。プレビュー（Studio）には
  軽いプロキシ、最終書き出しには原本、と置き換えても VideoScore は書き換えなくてよい。
- `http(s)://` の source はそのまま使う。それ以外の置き方は `resolveSrc` を渡して差し替える。
- `crop`・配置の計算には素材の画素サイズが要る。`calculateMetadata` がブラウザで実測するが、分かっているなら
  `sourceSizes` で渡すと速く確実（プロキシと原本で縦横比が同じならどちらのサイズでもよい）。

## このリポジトリでの開発

```bash
cd remotion
pnpm install              # videoscore（TS 型）は link:../typescript
pnpm typecheck
pnpm sample-media         # ffmpeg で public/sample/ に合成素材（testsrc2 + sine、ロゴ画像）を作る
pnpm compositions         # VideoScore（16:9）と VideoScoreVertical（9:16）が出る
pnpm still:wide           # out/wide.png
pnpm still:vertical       # out/vertical.png
pnpm studio
```

- サンプル: `samples/wide.resolved.json`（16:9: タイトル・通常テロップ・強調・字幕・隅のロゴ）と
  `samples/vertical.resolved.json`（9:16: `layout.vertical-fit`＋字幕、`crop`＋`layout.vertical-crop`）。
  どちらも合成素材だけを使う。Python 側のテストが、これらが解決済み VideoScore として妥当か（標準カタログ・§7）を検査する。
- サンプル素材（`public/sample/`）と出力（`out/`）はコミットしない。
- 型チェックでは `videoscore` を `../typescript/src` へ paths で解決する（TS 型のビルド不要）。
