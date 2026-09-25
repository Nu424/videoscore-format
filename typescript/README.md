# videoscore (TypeScript)

VideoScore 中間構造の **TypeScript 型**。型本体は `schema/*.json`（pydantic が SoT）から
生成された `src/*.gen.ts`。手編集しない。

## クイックスタート

```ts
import type { VideoScore } from 'videoscore'

const doc: VideoScore = {
  meta: { title: 'サンプル', fps: 30, size: [1920, 1080] },
  scenes: [
    {
      id: 's1',
      duration: { ref: 'audio.end' },
      audio: [{ id: 'v1', role: 'voice', source: 'tts://まずは結論から', t: [0, 'auto'] }],
      telop: [{ t: [0, { ref: 'v1.end' }], text: 'まずは結論から', style: 'tone.emphasis' }],
    },
  ],
}

// 時間語彙 t はタプル型 [start, end] / [start, end, gap]。
// start に "auto" を渡すと型エラー（循環防止の鉄則が型でも効く）:
// @ts-expect-error
const bad: VideoScore['scenes'][number]['telop'] = [{ t: ['auto', 3], text: 'x' }]

void doc
void bad
```

標準スタイルカタログと形式の版も生成物として入っている:

```ts
import { SCHEMA_VERSION, STANDARD_STYLE_CATALOG, type StandardStyleId } from 'videoscore'

SCHEMA_VERSION                                   // "0.2.0"（python の videoscore.SCHEMA_VERSION と同じ）
STANDARD_STYLE_CATALOG.styles['telop.caption']   // 意味（intent/feeling/appliesTo）
// レシピを Record<StandardStyleId, …> で書けば、全 id を揃えないと型エラーになる（§7 網羅）
type MyRecipes = Record<StandardStyleId, { className: string }>
```

## インストール（pnpm 9+）

素の npm は git のサブディレクトリ指定が弱いため **pnpm**（または yarn）を使う。

```bash
pnpm add "Nu424/videoscore-format#path:/typescript"
# ブランチ/タグ指定: "Nu424/videoscore-format#main&path:/typescript"
```

git 依存の `prepare` で `tsc` が走り、`dist/` に型がビルドされる。

## 開発

```bash
pnpm install
pnpm gen          # schema/*.json と標準カタログ JSON から src/*.gen.ts を再生成
pnpm gen:check    # ドリフト検知（CI 用）
pnpm build        # tsc で dist/ を生成
```

> 型は Python（pydantic）が正。型を変えるときは Python 側を直し、
> `videoscore-gen-schema` → `pnpm gen` の順で再生成する。
