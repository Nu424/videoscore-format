"""videoscore.model のテスト。仕様書 §3/§7/§8 の要点を固定する。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from videoscore.model import (
    AudioElement,
    Scene,
    StyleCatalog,
    TelopElement,
    VideoScore,
    validate_styles,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample() -> VideoScore:
    data = json.loads((FIXTURES / "sample_videoscore.json").read_text(encoding="utf-8"))
    return VideoScore.model_validate(data)


@pytest.fixture
def catalog() -> StyleCatalog:
    data = json.loads((FIXTURES / "sample_catalog.json").read_text(encoding="utf-8"))
    return StyleCatalog.model_validate(data)


# ---- §8 通しサンプルが読める ------------------------------------------------


def test_sample_parses(sample: VideoScore) -> None:
    assert len(sample.scenes) == 3
    assert sample.meta is not None
    assert sample.meta.size == (1920, 1080)


def test_in_alias_roundtrips(sample: VideoScore) -> None:
    # `in` は in_ に入り、出力時はエイリアス "in" で戻る
    clip = sample.scenes[0].video[0]
    assert clip.in_ == 5
    assert clip.out == 12
    dumped = clip.model_dump(by_alias=True, exclude_none=True)
    assert "in" in dumped and "in_" not in dumped


def test_time_vocabulary_preserved(sample: VideoScore) -> None:
    # 脱糖しない: "after" / "auto" / ref は素のまま保持される
    audio = sample.scenes[0].audio
    assert audio[0].t == (0, "auto")
    assert audio[1].t[0] == "after"
    telop1 = sample.scenes[0].telop[0]
    assert telop1.t[1].ref == "v1.end"  # RefObject として保持


def test_roundtrip_minimal_drops_empty_lanes(sample: VideoScore) -> None:
    out = sample.to_json_dict()
    # s2 には overlay が無い → 空レーンを出さない
    s2 = next(s for s in out["scenes"] if s["id"] == "s2")
    assert "overlay" not in s2
    # 再パースできる（往復可能）
    again = VideoScore.model_validate(out)
    assert again == sample


# ---- §3 鉄則・時間範囲 ------------------------------------------------------


def test_start_cannot_be_auto() -> None:
    # start に "auto" 単体は不可（循環防止の鉄則を型で表現）
    with pytest.raises(ValidationError):
        TelopElement(t=("auto", 3.0), text="x")


def test_concrete_start_must_be_before_end() -> None:
    with pytest.raises(ValidationError):
        TelopElement(t=(5.0, 3.0), text="x")


def test_negative_start_rejected() -> None:
    with pytest.raises(ValidationError):
        TelopElement(t=(-1.0, 3.0), text="x")


def test_non_concrete_span_not_range_checked() -> None:
    # end が auto なら尺未確定 → 範囲検査しない（解決側の責務）
    el = TelopElement(t=(3.0, "auto"), text="x")
    assert el.t == (3.0, "auto")


def test_gap_form_three_slot() -> None:
    el = TelopElement(t=("after", "auto", {"gap": 0.3}), text="x")
    assert el.t[2].gap == 0.3


def test_audio_role_enum() -> None:
    with pytest.raises(ValidationError):
        AudioElement(role="bogus", source="x.wav", t=(0.0, "auto"))


def test_unknown_field_forbidden() -> None:
    with pytest.raises(ValidationError):
        Scene.model_validate({"id": "s1", "duration": 5, "stlye": "typo"})


# ---- §7 カタログ横断検証 ----------------------------------------------------


def test_styles_all_valid(sample: VideoScore, catalog: StyleCatalog) -> None:
    assert validate_styles(sample, catalog) == []


def test_unknown_style_detected(sample: VideoScore, catalog: StyleCatalog) -> None:
    sample.scenes[0].telop[0].style = "no.such.style"
    issues = validate_styles(sample, catalog)
    assert len(issues) == 1
    assert issues[0].kind == "unknown-style"


def test_applies_to_violation_detected(sample: VideoScore, catalog: StyleCatalog) -> None:
    # tone.emphasis は telop 専用 → audio に付けると違反
    sample.scenes[1].audio[0].style = "tone.emphasis"
    issues = validate_styles(sample, catalog)
    assert any(i.kind == "applies-to" for i in issues)


# ---- v0.2.0 拡張: crop / annotations / meta.schemaVersion --------------------


def test_crop_on_video_and_overlay() -> None:
    from videoscore.model import OverlayElement, VideoElement

    v = VideoElement(source="a.mp4", t=(0.0, "auto"), crop=(0.25, 0.0, 0.5, 1.0))
    assert v.crop == (0.25, 0.0, 0.5, 1.0)
    o = OverlayElement(source="b.png", t=(0.0, 1.0), crop=[0, 0, 1, 1])
    assert o.crop == (0, 0, 1, 1)
    # 往復で保持される
    assert VideoElement.model_validate(v.model_dump(by_alias=True)).crop == v.crop


@pytest.mark.parametrize(
    "crop",
    [
        (-0.1, 0.0, 0.5, 0.5),  # x < 0
        (0.0, -0.1, 0.5, 0.5),  # y < 0
        (0.0, 0.0, 0.0, 0.5),  # w = 0
        (0.0, 0.0, 0.5, 0.0),  # h = 0
        (0.6, 0.0, 0.5, 0.5),  # x + w > 1
        (0.0, 0.6, 0.5, 0.5),  # y + h > 1
        (0.0, 0.0, 1.5, 0.5),  # w > 1
        (0.0, 0.0, 0.5),  # 要素数不足
    ],
)
def test_crop_out_of_range_rejected(crop) -> None:
    from videoscore.model import VideoElement

    with pytest.raises(ValidationError):
        VideoElement(source="a.mp4", t=(0.0, 1.0), crop=crop)


def test_crop_float_edge_tolerated() -> None:
    from videoscore.model import VideoElement

    # 0.1 + 0.9 のような浮動小数誤差で弾かない
    VideoElement(source="a.mp4", t=(0.0, 1.0), crop=(0.1, 0.7, 0.9, 0.3))


def test_crop_not_allowed_on_audio_or_telop() -> None:
    with pytest.raises(ValidationError):
        AudioElement.model_validate(
            {"role": "voice", "source": "v.wav", "t": [0, 1], "crop": [0, 0, 1, 1]}
        )
    with pytest.raises(ValidationError):
        TelopElement.model_validate({"t": [0, 1], "text": "x", "crop": [0, 0, 1, 1]})


def test_annotations_free_form_on_all_lanes_and_scene() -> None:
    ann = {"refs": ["src_01#ev_0042"], "candidate": "c3", "nested": {"score": 0.8}}
    doc = VideoScore.model_validate(
        {
            "scenes": [
                {
                    "id": "s1",
                    "duration": 3,
                    "annotations": ann,
                    "video": [{"source": "a.mp4", "t": [0, 3], "annotations": ann}],
                    "audio": [{"role": "voice", "source": "v.wav", "t": [0, 3], "annotations": ann}],
                    "telop": [{"t": [0, 1], "text": "x", "annotations": ann}],
                    "overlay": [{"source": "l.png", "t": [0, 1], "annotations": ann}],
                }
            ]
        }
    )
    s = doc.scenes[0]
    assert s.annotations == ann
    for lane in ("video", "audio", "telop", "overlay"):
        assert getattr(s, lane)[0].annotations == ann
    # 出力にもそのまま残る
    out = doc.to_json_dict()
    assert out["scenes"][0]["annotations"] == ann
    assert out["scenes"][0]["telop"][0]["annotations"] == ann


def test_schema_version_in_meta() -> None:
    from videoscore import SCHEMA_VERSION
    from videoscore.model import Meta

    assert SCHEMA_VERSION == "0.2.0"
    m = Meta(schemaVersion=SCHEMA_VERSION)
    assert m.schemaVersion == "0.2.0"
    # 省略可（既存文書はそのまま読める）
    assert Meta().schemaVersion is None


def test_schema_carries_version() -> None:
    from videoscore import SCHEMA_VERSION
    from videoscore.jsonschema import build_schemas

    schemas = build_schemas()
    assert schemas["videoscore.schema.json"]["x-videoscore-version"] == SCHEMA_VERSION
