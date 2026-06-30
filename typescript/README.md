# videoscore (TypeScript)

VideoScore 中間構造の **TypeScript 型**。型本体は `schema/*.json`（pydantic が SoT）から
生成された `src/*.gen.ts`。手編集しない。

## インストール（pnpm 9+）

素の npm は git のサブディレクトリ指定が弱いため **pnpm**（または yarn）を使う。

```bash
pnpm add "Nu424/videoscore-format#path:/typescript"
# ブランチ/タグ指定: "Nu424/videoscore-format#main&path:/typescript"
```

git 依存の `prepare` で `tsc` が走り、`dist/` に型がビルドされる。

## 使い方

```ts
import type { VideoScore, Scene, RefObject } from 'videoscore'

const doc: VideoScore = {
  meta: { title: 'x', fps: 30, size: [1920, 1080] },
  scenes: [
    {
      id: 's1',
      duration: { ref: 'audio.end' },
      audio: [{ id: 'v1', role: 'voice', source: 'tts://a', t: [0, 'auto'] }],
      telop: [{ t: [0, { ref: 'v1.end' }], text: 'a', style: 'tone.emphasis' }],
    },
  ],
}
```

時間語彙 `t` はタプル型 `[start, end]` / `[start, end, gap]` として表現され、
`start` に `"auto"` を渡すと型エラーになる（循環防止の鉄則）。

## 開発

```bash
pnpm install
pnpm gen          # schema/*.json から src/*.gen.ts を再生成
pnpm gen:check    # ドリフト検知（CI 用）
pnpm build        # tsc で dist/ を生成
```

> 型は Python（pydantic）が正。型を変えるときは Python 側を直し、
> `videoscore-gen-schema` → `pnpm gen` の順で再生成する。
