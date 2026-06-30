"""生成済み JSON Schema が pydantic モデルと一致するか（ドリフト検知）。

モデルを変更したら `videoscore-gen-schema` で schema/ を再生成すること。
比較はパース後のオブジェクト同士（整形差に頑健）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videoscore.jsonschema import build_schemas

# python/tests/test_schema.py -> python/tests -> python -> リポジトリルート
REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schema"


@pytest.mark.parametrize("name,schema", list(build_schemas().items()))
def test_committed_schema_up_to_date(name: str, schema: dict) -> None:
    path = SCHEMA_DIR / name
    assert path.exists(), f"{path} が無い — `videoscore-gen-schema` で生成してください"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == schema, f"{name} が古い — `videoscore-gen-schema` で再生成してください"
