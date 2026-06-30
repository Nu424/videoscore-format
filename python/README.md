# videoscore (Python)

VideoScore 中間構造の型定義と検証。**Pydantic v2 を Single Source of Truth** とし、
ここから JSON Schema / TypeScript 型を生成する。

- 型本体: `videoscore.model`（依存は pydantic のみ）
- 将来: `videoscore.resolve` で VideoScore→OTIO 解決（optional extra `[otio]`）

仕様の一次ソースは `../documents/intermediate-structure-guideline.md`。

```python
from videoscore.model import VideoScore, StyleCatalog, validate_styles

doc = VideoScore.model_validate_json(open("video.json", encoding="utf-8").read())
issues = validate_styles(doc, catalog)  # §7 enum / appliesTo
```

> 詳細な利用・インストール手順は後続フェーズで追記。
