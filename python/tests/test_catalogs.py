"""標準スタイルカタログ（videoscore.catalogs）のテスト。

同梱カタログが読めること、§7 の enum/appliesTo・網羅（aup2 レシピ）が通ること、
縦型ショートの典型構成が標準カタログだけで書けることを確認する。
"""

from __future__ import annotations

from videoscore.catalogs import (
    load_catalog,
    merge_catalogs,
    standard_catalog,
    standard_catalog_path,
)
from videoscore.export import render_aup2
from videoscore.export.recipes import default_recipes
from videoscore.model import StyleCatalog, StyleEntry, VideoScore, validate_coverage, validate_styles

STANDARD_IDS = {
    "telop.default",
    "telop.caption",
    "telop.title",
    "tone.emphasis",
    "layout.vertical-fit",
    "layout.vertical-crop",
    "audio.default",
    "position.corner",
}


def _vertical_doc() -> VideoScore:
    """9:16 縦型ショートの典型（横長素材を vertical-fit/crop、上にタイトル、下に字幕）。"""
    return VideoScore.model_validate(
        {
            "meta": {"fps": 30, "size": [1080, 1920], "schemaVersion": "0.2.0"},
            "telop": [{"t": [0, 2], "text": "架空のタイトル", "style": "telop.title"}],
            "scenes": [
                {
                    "id": "s1",
                    "duration": 3,
                    "video": [{"source": "clip.mp4", "in": 0, "out": 3, "t": [0, 3], "style": "layout.vertical-fit"}],
                    "audio": [{"role": "voice", "source": "clip.mp4", "in": 0, "out": 3, "t": [0, 3], "style": "audio.default"}],
                    "telop": [
                        {"t": [0, 1.5], "text": "はじめの一言", "style": "telop.caption"},
                        {"t": [1.5, 3], "text": "ここが大事", "style": "tone.emphasis"},
                    ],
                    "overlay": [{"source": "logo.png", "t": [0, 3], "style": "position.corner"}],
                },
                {
                    "id": "s2",
                    "duration": 2,
                    "video": [
                        {"source": "clip.mp4", "in": 3, "out": 5, "t": [0, 2], "crop": [0.34, 0, 0.32, 1], "style": "layout.vertical-crop"}
                    ],
                    "telop": [{"t": [0, 2], "text": "寄りの字幕", "style": "telop.caption"}],
                },
            ],
        }
    )


def test_standard_catalog_loads() -> None:
    cat = standard_catalog()
    assert set(cat.styles) == STANDARD_IDS
    for entry in cat.styles.values():
        assert entry.intent and entry.feeling and entry.appliesTo


def test_standard_catalog_path_readable() -> None:
    path = standard_catalog_path()
    assert path.name == "style-catalog.json"
    assert load_catalog(path) == standard_catalog()


def test_standard_catalog_covered_by_aup2_recipes() -> None:
    # §7 網羅: 意味の全 id が recipes.aup2 に揃っている
    assert validate_coverage(standard_catalog(), default_recipes().ids(), editor="aup2") == []


def test_coverage_detects_missing_recipe() -> None:
    issues = validate_coverage(standard_catalog(), {"telop.default"}, editor="x")
    assert {i.style for i in issues} == STANDARD_IDS - {"telop.default"}
    assert all(i.kind == "coverage" for i in issues)


def test_vertical_short_validates_against_standard() -> None:
    assert validate_styles(_vertical_doc(), standard_catalog()) == []


def test_vertical_short_exports_without_style_warnings() -> None:
    proj, diags = render_aup2(
        _vertical_doc(), catalog=standard_catalog(), source_sizes={"clip.mp4": (1920, 1080)}
    )
    kinds = {d.kind for d in diags}
    assert not kinds & {"unknown-style", "appliesTo", "unsupported-crop", "not-resolved"}
    assert "effect.name=クリッピング" in proj.to_text()


def test_merge_catalogs_project_override() -> None:
    extra = StyleCatalog(
        styles={
            "telop.caption": StyleEntry(intent="上書き", feeling="x", appliesTo=["telop"]),
            "tone.warning": StyleEntry(intent="注意喚起", feeling="警告", appliesTo=["telop"]),
        }
    )
    merged = merge_catalogs(standard_catalog(), extra)
    assert merged.styles["telop.caption"].intent == "上書き"
    assert "tone.warning" in merged.styles and "telop.title" in merged.styles
