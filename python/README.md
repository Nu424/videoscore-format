# videoscore (Python)

VideoScore 中間構造の型定義と検証。**Pydantic v2 を Single Source of Truth** とし、
ここから JSON Schema / TypeScript 型を生成する。

- 型本体: `videoscore.model`（依存は pydantic のみ）
- 解決系: `videoscore.resolve` — 絵コンテ的 VideoScore を段階的に清書方向へ具体化する
  （出力は**解決済み VideoScore**）。依存は model のみ。
- コンバータ: `videoscore.export` — 解決済み VideoScore を各エディタ形式へ書き出す。第一弾は
  AviUtl2 `.aup2`（`videoscore.export.aup2`）。スタイルの印を具体エフェクトへ展開する。依存は model のみ。

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

標準スタイルカタログ（`telop.caption`/`telop.title`/`layout.vertical-fit` 等の最小セット）は同梱されている:

```python
from videoscore.catalogs import standard_catalog, merge_catalogs

issues = validate_styles(doc, standard_catalog())            # 標準カタログで検証
catalog = merge_catalogs(standard_catalog(), my_catalog)     # プロジェクト固有の印で上書き・追加
```

形式の版は `videoscore.SCHEMA_VERSION`（現行 `"0.2.0"`）。`meta.schemaVersion` に書ける。
v0.2.0 で `crop`（video/overlay の映す領域 `[x,y,w,h]` 比率）と `annotations`（全要素と scene の自由な注記。
resolve/export は素通し）が加わった。

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

## コンバータ（`videoscore.export.aup2`）

解決済み VideoScore を AviUtl2 `.aup2` へ書き出す。スタイルの意味的な印（`tone.emphasis` 等）を
`recipes.aup2.json` で AviUtl2 の具体エフェクト（縁取り文字・ドロップシャドウ・座標/拡大率…）へ展開する。

```python
from videoscore.export import render_aup2, dump_aup2

project, diags = render_aup2(resolved)         # 解決済み VideoScore → .aup2 モデル＋診断
print(project.scene.objects[0].layer)          # レーン別帯へ自動割当（video 0/telop 20/audio 30…）
dump_aup2(resolved, "demo.aup2")               # UTF-8/CRLF・フレーム単位でファイルへ

render_aup2(doc, resolve_first=True)           # 未解決 VideoScore は解決を前段に噛ませられる
```

- **診断は例外でなくリスト**。未解決の時間は `not-resolved`、記号 source 残存は `symbolic-source`（error）。
  error があっても可能な範囲で出力する（部分変換）。
- **scenes は単一 `[scene.0]` に frame 連結**。レーン→レイヤーは帯＋区間分割で衝突なく自動割当。
- **スタイルは `recipes.aup2.json` で展開**（`text`/`draw`/`filters` の3パッチ口＋相対値 `%w`/`%h`）。
  生の hex/px はレシピ層に閉じる（中間構造・AI には出さない）。レシピは差し替え可能。
- **`crop` はクリッピングへ**: `render_aup2(resolved, source_sizes={"a.mp4": (1920, 1080)})` のように素材の
  画素サイズを渡すと `クリッピング` フィルタに展開する。渡さなければ warning `unsupported-crop` を出して無視。
- **自前エミッタ（依存なし）**。往復テスト用に `aviutl2-api` を dev extra `[aup2-dev]` で使える。

→ 実行可能サンプル: [`examples/export_aup2.py`](examples/export_aup2.py)（`python examples/export_aup2.py`）。
設計の詳細は [`../documents/export-aup2-design.md`](../documents/export-aup2-design.md)。

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
