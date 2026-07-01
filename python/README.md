# videoscore (Python)

VideoScore 中間構造の型定義と検証。**Pydantic v2 を Single Source of Truth** とし、
ここから JSON Schema / TypeScript 型を生成する。

- 型本体: `videoscore.model`（依存は pydantic のみ）
- 解決系: `videoscore.resolve` — 絵コンテ的 VideoScore を段階的に清書方向へ具体化する
  （出力は**解決済み VideoScore**。OTIO 等への変換は将来の別モジュール）。依存は model のみ。

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

## 解決パイプライン（`videoscore.resolve`）

`after`/`auto`/`ref` や `tts://…` を含む絵コンテ的 VideoScore を、段階的に具体化する。
出力は**解決済み VideoScore**（時間は全部具体・スタイルは意味のまま）。各「解決」は
`VideoScore→VideoScore` のパスで、`after` 依存でトポロジカルソートして回る。

```python
from videoscore.resolve import resolve

resolved, diagnostics = resolve(doc)          # 既定: mock プロバイダ入りコンテキスト
print(resolved.scenes[0].duration)            # 例: 1.92（audio.end を数値化）
print(resolved.scenes[0].audio[0].t)          # (0.0, 0.84) — auto/ref が具体秒に

resolved, _ = resolve(doc, until="normalize") # 途中段階で止める（after→ref だけ見る）
```

- **診断は例外でなくリスト**（`Diagnostic`）。解けない `auto` は error でなく部分解決の警告。
- **実体解決は拡張点**: `tts://`/`t2i://`/`t2v://` は URI スキーム別の `AssetProvider`。
  スキーム別プロバイダを1個 register するだけで種類を足せる（`MockProvider` は開発用スタブ）。
- **べき等**: `resolve(resolve(x)) == resolve(x)`。

→ 一連の流れ（段階出力・プロバイダ差し替え・部分解決まで）の実行可能サンプル:
[`examples/resolve_pipeline.py`](examples/resolve_pipeline.py)（`python examples/resolve_pipeline.py`）。
設計の詳細は [`../documents/resolve-design.md`](../documents/resolve-design.md)。

## インストール（git 経由）

型と解決（`videoscore.resolve`）はどちらも依存 pydantic のみ。素の install で使える。

```bash
pip install "git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
# 将来の各形式コンバータ（VideoScore→OTIO 等）まで使う場合の extra:
pip install "videoscore[otio] @ git+https://github.com/Nu424/videoscore-format.git#subdirectory=python"
```

## 設計の要点

- 時間語彙（§3）は**型では脱糖しない**。`after` / `auto` / `ref` / `gap` 形は素のまま保持し、
  脱糖・時間解決は解決系（`videoscore.resolve`）の責務。
- 循環防止の鉄則「start は具体 or 参照、派生は end だけ」を**型で表現**（start に `"auto"` は不可）。
- pydantic で静的に書ける検証のみモデルに持たせ、カタログを要する検証は `validate_styles` に分離。

## 開発

```bash
pip install -e ".[dev]"
pytest
videoscore-gen-schema --out-dir ../schema           # JSON Schema を再生成
videoscore-gen-schema --out-dir ../schema --check   # ドリフト検知（CI 用）
```
