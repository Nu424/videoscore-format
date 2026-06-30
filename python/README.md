# videoscore (Python)

VideoScore 中間構造の型定義と検証。**Pydantic v2 を Single Source of Truth** とし、
ここから JSON Schema / TypeScript 型を生成する。

- 型本体: `videoscore.model`（依存は pydantic のみ）
- 将来: `videoscore.resolve` で VideoScore→OTIO 解決（optional extra `[otio]`）

仕様の一次ソースは [`../documents/intermediate-structure-guideline.md`](../documents/intermediate-structure-guideline.md)。

## クイックスタート

```python
import json
from videoscore.model import VideoScore, StyleCatalog, validate_styles

# 1. JSON から読み込む（パース＋検証が同時に走る）
doc = VideoScore.model_validate_json("""
{
  "meta": { "title": "サンプル", "fps": 30, "size": [1920, 1080] },
  "scenes": [
    {
      "id": "s1",
      "duration": { "ref": "audio.end" },
      "audio": [
        { "id": "v1", "role": "voice", "source": "tts://まずは結論から", "t": [0, "auto"] }
      ],
      "telop": [
        { "t": [0, { "ref": "v1.end" }], "text": "まずは結論から", "style": "tone.emphasis" }
      ]
    }
  ]
}
""")

# 2. 構造にアクセス（時間語彙 "auto"/"after"/{ref} は脱糖されず素のまま）
print(doc.scenes[0].audio[0].t)        # (0.0, 'auto')
print(doc.scenes[0].telop[0].t[1])     # ref='v1.end' offset=None

# 3. 最小 JSON として出力（None・空レーンを省き、in 等はエイリアスで）
print(json.dumps(doc.to_json_dict(), ensure_ascii=False, indent=2))

# 4. スタイルをカタログと突き合わせる（§7 enum / appliesTo）
catalog = StyleCatalog.model_validate({
    "styles": {"tone.emphasis": {"intent": "決め台詞", "feeling": "強い", "appliesTo": ["telop"]}}
})
issues = validate_styles(doc, catalog)   # 問題のリスト（空なら OK）
print(issues)
```

→ 組み立て・検証エラー例まで含む実行可能ノートブック: [`examples/quickstart.ipynb`](examples/quickstart.ipynb)

## インストール（git 経由）

```bash
pip install "git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
# OTIO 解決まで使う場合:
pip install "videoscore[otio] @ git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
```

## 設計の要点

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
