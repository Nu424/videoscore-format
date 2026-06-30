# videoscore (Python)

VideoScore 中間構造の型定義と検証。**Pydantic v2 を Single Source of Truth** とし、
ここから JSON Schema / TypeScript 型を生成する。

- 型本体: `videoscore.model`（依存は pydantic のみ）
- 将来: `videoscore.resolve` で VideoScore→OTIO 解決（optional extra `[otio]`）

仕様の一次ソースは [`../documents/intermediate-structure-guideline.md`](../documents/intermediate-structure-guideline.md)。

## インストール（git 経由）

```bash
pip install "git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
# OTIO 解決まで使う場合:
pip install "videoscore[otio] @ git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
```

## 使い方

```python
from videoscore.model import VideoScore, StyleCatalog, validate_styles

doc = VideoScore.model_validate_json(open("video.json", encoding="utf-8").read())

# 出力（最小・素の形: None と空レーンを省き、in 等はエイリアスで）
data = doc.to_json_dict()

# カタログ横断検証（§7 enum / appliesTo）
catalog = StyleCatalog.model_validate_json(open("style-catalog.json", encoding="utf-8").read())
for issue in validate_styles(doc, catalog):
    print(issue)
```

### 設計の要点

- 時間語彙（§3）は**脱糖しない**。`after` / `auto` / `ref` / `gap` 形は素のまま保持し、
  脱糖・時間解決は解決スクリプト（`videoscore.resolve`、将来）の責務。
- 循環防止の鉄則「start は具体 or 参照、派生は end だけ」を**型で表現**（start に `"auto"` は不可）。
- pydantic で静的に書ける検証のみモデルに持たせ、カタログを要する検証は `validate_styles` に分離。

## 開発

```bash
pip install -e ".[dev]"
pytest
videoscore-gen-schema --out-dir ../schema           # JSON Schema を再生成
videoscore-gen-schema --out-dir ../schema --check   # ドリフト検知（CI 用）
```
