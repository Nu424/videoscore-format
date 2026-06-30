# videoscore-format

動画編集の**中間構造（VideoScore 形式）**の定義と型実装。
台本/アウトラインと、実タイムライン（各エディタ形式）の間に置く、絵コンテ的で
過少指定な中間表現を扱う。

```
台本 / アウトライン  →  構成（★VideoScore 形式）  →  タイムライン  →  レンダ
```

- **仕様の一次ソース**: [`documents/intermediate-structure-guideline.md`](documents/intermediate-structure-guideline.md)
- **型の Single Source of Truth**: Python（pydantic v2）。ここから JSON Schema と TypeScript 型を生成する。

```
pydantic models (SoT)
   └─ schema/*.json ──► TypeScript 型 (typescript/src/*.gen.ts)
```

## リポジトリ構成

| パス | 役割 |
|------|------|
| `documents/` | 仕様書（設計判断・時間モデル・検証ルール） |
| `.claude/videoscore-format-skill/` | 台本→中間構造JSONを組み立てる Agent Skill |
| `python/` | **型本体（pydantic）と検証**。SoT。将来 OTIO 解決もここに |
| `schema/` | pydantic から生成した JSON Schema（コミット済み生成物） |
| `typescript/` | JSON Schema から生成した TypeScript 型（コミット済み生成物） |
| `.github/workflows/` | CI（テスト＋生成物のドリフト検知） |

## クイックスタート

同じ VideoScore JSON を、Python では検証付きで読み、TypeScript では型付きで書ける。

```python
# Python: 読み込み（パース＋検証）→ アクセス → カタログ検証
from videoscore.model import VideoScore, StyleCatalog, validate_styles

doc = VideoScore.model_validate_json(open("video.json", encoding="utf-8").read())
print(doc.scenes[0].audio[0].t)          # (0.0, 'auto') — 時間語彙は素のまま
issues = validate_styles(doc, catalog)   # §7 enum / appliesTo（空なら OK）
```

```ts
// TypeScript: 型付きで構築（start に "auto" を書くと型エラー）
import type { VideoScore } from 'videoscore'

const doc: VideoScore = {
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

各言語のより詳しい例: [`python/README.md`](python/README.md)（＋ [`python/examples/quickstart.ipynb`](python/examples/quickstart.ipynb)）/ [`typescript/README.md`](typescript/README.md)。

## インストール（git 経由）

### Python

```bash
pip install "git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
```

将来の VideoScore→OTIO 解決まで使う場合は extra `[otio]` を付ける（`opentimelineio` が入る）:

```bash
pip install "videoscore[otio] @ git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
```

### TypeScript（pnpm 9+）

素の npm は git のサブディレクトリ指定が弱いため **pnpm**（または yarn）を使う。

```bash
pnpm add "Nu424/videoscore-format#path:/typescript"
# ブランチ/タグ指定: "Nu424/videoscore-format#main&path:/typescript"
```

## 開発

```bash
# Python（型本体・検証・JSON Schema 生成）
cd python
pip install -e ".[dev]"
pytest
videoscore-gen-schema --out-dir ../schema     # schema/*.json を再生成

# TypeScript（JSON Schema から型生成・ビルド）
cd typescript
pnpm install
pnpm gen        # src/*.gen.ts を再生成（要 schema/）
pnpm build
```

モデルを変更したら **`videoscore-gen-schema` → `pnpm gen`** の順で再生成する。
CI は生成物がモデルと一致しているか（ドリフト）を `--check` / `gen:check` で検証する。

## 状況

設計・型実装の段階。VideoScore→OTIO 解決スクリプト（`videoscore.resolve`）は今後追加予定。
