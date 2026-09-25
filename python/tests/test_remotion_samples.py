"""remotion/samples/*.resolved.json（Remotion プレイヤーのサンプル）が解決済み VideoScore として妥当か。

プレイヤー側は型しか見ないので、形式・標準カタログ・解決済み不変条件（§7）はここで固定する。
remotion/ が無い配布形態（python/ だけの install）では skip。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from videoscore.catalogs import standard_catalog
from videoscore.model import SCHEMA_VERSION, VideoScore, validate_styles
from videoscore.resolve import ValidateResolvedPass, default_context

SAMPLES = Path(__file__).resolve().parents[2] / "remotion" / "samples"
FILES = sorted(SAMPLES.glob("*.resolved.json")) if SAMPLES.exists() else []


@pytest.mark.skipif(not FILES, reason="remotion/samples が無い")
@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_remotion_sample_is_resolved_and_valid(path: Path) -> None:
    doc = VideoScore.model_validate_json(path.read_text(encoding="utf-8"))
    assert doc.meta is not None and doc.meta.schemaVersion == SCHEMA_VERSION
    assert validate_styles(doc, standard_catalog()) == []
    _, diags = ValidateResolvedPass().run(doc, default_context())
    assert [d for d in diags if d.severity == "error"] == []
    assert [d for d in diags if d.kind == "overrun"] == []


def test_samples_json_are_plain_json() -> None:
    for path in FILES:
        json.loads(path.read_text(encoding="utf-8"))
