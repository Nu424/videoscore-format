"""videoscore.export.aup2（VideoScore → .aup2 変換）のテスト。

時間換算・シーン連結・レーン→レイヤー割当・レシピ展開・診断・エミッタ整形、
および aviutl2-api を用いた往復パース（インストール時のみ）を確認する。
"""

from __future__ import annotations

import pytest

from videoscore.model import (
    AudioElement,
    Meta,
    OverlayElement,
    Scene,
    StyleCatalog,
    TelopElement,
    VideoElement,
    VideoScore,
)
from videoscore.export import render_aup2, dump_aup2
from videoscore.export.common import LayerAllocator, scene_offsets, span_to_frames
from videoscore.export.recipes import default_recipes, load_recipes, resolve_template


# --- ヘルパ ---------------------------------------------------------------

def _effect(obj, name):
    for eff in obj.effects:
        if eff.name == name:
            return eff
    return None


def _resolved_doc():
    """時間がすべて数値の（解決済み相当の）ドキュメント。"""
    return VideoScore(
        meta=Meta(fps=30, size=(1920, 1080)),
        scenes=[
            Scene(
                id="s1",
                duration=2.0,
                video=[VideoElement(source="a.mp4", in_=5, out=7, t=(0.0, 2.0))],
                audio=[AudioElement(source="v.wav", role="voice", t=(0.0, 2.0))],
                telop=[TelopElement(t=(0.0, 1.0), text="こんにちは", style="tone.emphasis")],
            )
        ],
    )


# --- 時間換算 -------------------------------------------------------------

def test_span_to_frames_inclusive_no_overlap():
    (s, e), degen = span_to_frames(0.0, 1.0, 30)
    assert (s, e) == (0, 29) and not degen
    # 隣接要素が 1 フレームも重ならない
    (s2, e2), _ = span_to_frames(1.0, 2.0, 30)
    assert s2 == e + 1 == 30


def test_span_degenerate_is_flagged():
    (s, e), degen = span_to_frames(0.0, 0.01, 30)  # 0.3 フレーム → 潰れる
    assert s == e and degen


def test_scene_offsets_accumulate():
    scenes = [Scene(id="a", duration=2.0), Scene(id="b", duration=1.5), Scene(id="c", duration=3.0)]
    assert scene_offsets(scenes) == [0.0, 2.0, 3.5]


def test_scene_concatenation_offsets_frames():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[
            Scene(id="s1", duration=2.0, telop=[TelopElement(t=(0.0, 1.0), text="a")]),
            Scene(id="s2", duration=2.0, telop=[TelopElement(t=(0.0, 1.0), text="b")]),
        ],
    )
    proj, _ = render_aup2(doc)
    # s2 のテロップは 2.0s オフセット → frame 60 から
    frames = sorted(o.frame_start for o in proj.scene.objects)
    assert frames == [0, 60]


# --- レイヤー割当 ---------------------------------------------------------

def test_layer_allocator_reuse_and_escalate():
    alloc = LayerAllocator()
    assert alloc.allocate(0, 29, floor=20) == 20      # 最初
    assert alloc.allocate(30, 59, floor=20) == 20     # 重ならない → 再利用
    assert alloc.allocate(10, 40, floor=20) == 21     # 重なる → 退避


def test_lane_bands_separated():
    doc = _resolved_doc()
    proj, _ = render_aup2(doc)
    layers = {_main_kind(o): o.layer for o in proj.scene.objects}
    assert layers["動画ファイル"] == 0      # video 帯
    assert layers["テキスト"] == 20         # telop 帯
    assert layers["音声ファイル"] == 30     # audio 帯（voice）


def test_audio_role_subbands():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[
            Scene(
                id="s1",
                duration=2.0,
                audio=[
                    AudioElement(source="v.wav", role="voice", t=(0.0, 2.0)),
                    AudioElement(source="m.wav", role="music", t=(0.0, 2.0)),  # 同時
                ],
            )
        ],
    )
    proj, _ = render_aup2(doc)
    layers = sorted(o.layer for o in proj.scene.objects)
    assert layers == [30, 34]  # voice=30, music=30+4


def _main_kind(obj):
    return obj.effects[0].name


# --- レシピ展開 -----------------------------------------------------------

def test_tone_emphasis_expands_text_and_filter():
    doc = _resolved_doc()
    proj, _ = render_aup2(doc)
    telop = next(o for o in proj.scene.objects if _main_kind(o) == "テキスト")
    text = _effect(telop, "テキスト")
    assert text.props["文字装飾"] == "縁取り文字(太)"
    assert text.props["影・縁色"] == "1a4fff"
    # telop.default も当たっている
    assert text.props["文字揃え"] == "中央[中]"
    # ドロップシャドウ フィルタが追記される
    assert _effect(telop, "ドロップシャドウ") is not None


def test_layout_relative_value_to_px():
    doc = VideoScore(
        meta=Meta(fps=30, size=(1920, 1080)),
        scenes=[Scene(id="s1", duration=2.0,
                      video=[VideoElement(source="a.mp4", t=(0.0, 2.0), style="layout.split-left")])],
    )
    proj, _ = render_aup2(doc)
    draw = _effect(proj.scene.objects[0], "標準描画")
    assert draw.props["X"] == -480.0   # -25% of 1920
    assert draw.props["拡大率"] == 50


def test_resolve_template_units():
    assert resolve_template("-25%w", width=1920, height=1080) == -480.0
    assert resolve_template("40%h", width=1920, height=1080) == 432.0
    assert resolve_template(30, width=1920, height=1080) == 30
    assert resolve_template("通常", width=1920, height=1080) == "通常"


def test_unknown_style_warns_but_renders():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0,
                      telop=[TelopElement(t=(0.0, 1.0), text="x", style="no.such.style")])],
    )
    proj, diags = render_aup2(doc)
    assert any(d.kind == "unknown-style" for d in diags)
    assert len(proj.scene.objects) == 1  # 素の既定で描画される


def test_unsupported_style_warns():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0,
                      telop=[TelopElement(t=(0.0, 1.0), text="x", style="highlight")])],
    )
    _, diags = render_aup2(doc)
    assert any(d.kind == "unsupported-style" for d in diags)


def test_applies_to_warning_with_catalog():
    catalog = StyleCatalog.model_validate(
        {"styles": {"tone.emphasis": {"intent": "i", "feeling": "f", "appliesTo": ["telop"]}}}
    )
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0,
                      video=[VideoElement(source="a.mp4", t=(0.0, 2.0), style="tone.emphasis")])],
    )
    _, diags = render_aup2(doc, catalog=catalog)
    assert any(d.kind == "appliesTo" for d in diags)


def test_custom_recipe_book():
    book = load_recipes({"telop.default": {"text": {"サイズ": 72}}})
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0, telop=[TelopElement(t=(0.0, 1.0), text="x")])],
    )
    proj, _ = render_aup2(doc, recipes=book)
    text = _effect(proj.scene.objects[0], "テキスト")
    assert text.props["サイズ"] == 72


# --- 診断 -----------------------------------------------------------------

def test_unresolved_time_is_error():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0,
                      telop=[TelopElement(t=(0.0, "auto"), text="x")])],
    )
    proj, diags = render_aup2(doc)
    assert any(d.kind == "not-resolved" and d.severity == "error" for d in diags)
    assert len(proj.scene.objects) == 0  # 未解決要素は置かれない


def test_symbolic_source_is_error():
    doc = VideoScore(
        meta=Meta(fps=30),
        scenes=[Scene(id="s1", duration=2.0,
                      audio=[AudioElement(source="tts://未実体化", role="voice", t=(0.0, 2.0))])],
    )
    _, diags = render_aup2(doc)
    assert any(d.kind == "symbolic-source" and d.severity == "error" for d in diags)


# --- トリム／メタ ---------------------------------------------------------

def test_video_trim_in_becomes_play_position():
    doc = _resolved_doc()
    proj, _ = render_aup2(doc)
    video = next(o for o in proj.scene.objects if _main_kind(o) == "動画ファイル")
    assert _effect(video, "動画ファイル").props["再生位置"] == 5.0


def test_meta_defaults_when_absent():
    doc = VideoScore(scenes=[Scene(id="s1", duration=1.0,
                                   telop=[TelopElement(t=(0.0, 1.0), text="x")])])
    proj, _ = render_aup2(doc)
    assert (proj.scene.width, proj.scene.height, proj.scene.fps) == (1920, 1080, 30)


# --- エミッタ -------------------------------------------------------------

def test_emit_crlf_and_hex_and_header():
    doc = _resolved_doc()
    proj, _ = render_aup2(doc, project_file="C:/out/demo.aup2")
    text = proj.to_text()
    assert "\r\n" in text and "\n" not in text.replace("\r\n", "")  # 改行は CRLF のみ
    assert "文字色=ffffff" in text                                   # hex は文字列のまま
    assert "video.rate=30" in text and "file=C:/out/demo.aup2" in text
    assert text.startswith("[project]\r\n")


def test_top_level_lanes_are_placed():
    doc = VideoScore(
        meta=Meta(fps=30),
        audio=[AudioElement(source="bgm.wav", role="music", t=(0.0, 4.0))],  # シーン跨ぎ BGM
        scenes=[Scene(id="s1", duration=2.0, telop=[TelopElement(t=(0.0, 1.0), text="x")])],
    )
    proj, _ = render_aup2(doc)
    kinds = {_main_kind(o) for o in proj.scene.objects}
    assert "音声ファイル" in kinds and "テキスト" in kinds


# --- 往復（aviutl2-api がある時のみ） -------------------------------------

def test_roundtrip_with_aviutl2_api(tmp_path):
    aviutl2_api = pytest.importorskip("aviutl2_api")
    doc = _resolved_doc()
    out = tmp_path / "demo.aup2"
    diags = dump_aup2(doc, str(out))
    assert not [d for d in diags if d.severity == "error"]

    parsed = aviutl2_api.parse_file(str(out))
    sc = parsed.scenes[0]
    assert sc.width == 1920 and sc.fps == 30
    assert len(sc.objects) == 3  # video / telop / audio
    # フレーム範囲とレイヤーが保存されている
    by_layer = {o.layer: (o.frame_start, o.frame_end) for o in sc.objects}
    assert by_layer[0] == (0, 59)     # video 2.0s
    assert by_layer[20] == (0, 29)    # telop 1.0s
    assert by_layer[30] == (0, 59)    # audio voice
