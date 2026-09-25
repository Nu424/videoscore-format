"""videoscore.resolve のテスト（解決パイプライン）。

§8 通しサンプルの解決、after 脱糖、ref/lane.end/duration、循環・dangling 診断、
未解決 auto（部分解決）、べき等、until= の段階出力を確認する。
"""

from __future__ import annotations

import json
from pathlib import Path

from videoscore.model import RefObject, Scene, TelopElement, VideoScore
from videoscore.resolve import (
    DEFAULT_PASSES,
    MockProvider,
    ProviderRegistry,
    ResolveContext,
    default_context,
    resolve,
    topo_order,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _sample() -> VideoScore:
    raw = (FIXTURES / "sample_videoscore.json").read_text(encoding="utf-8")
    return VideoScore.model_validate_json(raw)


def _all_times_concrete(doc: VideoScore) -> bool:
    def num(v) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    for scene in doc.scenes:
        if not num(scene.duration):
            return False
        for lane in ("video", "audio", "telop", "overlay"):
            for el in getattr(scene, lane):
                if not (num(el.t[0]) and num(el.t[1])):
                    return False
    return True


# --- §8 通しサンプル ---------------------------------------------------------


def test_sample_fully_resolves_without_errors():
    doc = _sample()
    resolved, diags = resolve(doc)
    assert _all_times_concrete(resolved)
    assert [d for d in diags if d.severity == "error"] == []


def test_sample_audio_driver_duration():
    # s1 は audio ドライバ。duration = audio.end = 全 voice の連結尾
    resolved, _ = resolve(_sample())
    s1 = resolved.scenes[0]
    assert s1.duration == s1.audio[-1].t[1]
    # voice は after 連結: 0 から隙間なく直列
    assert s1.audio[0].t[0] == 0.0
    assert s1.audio[1].t[0] == s1.audio[0].t[1]
    assert s1.audio[2].t[0] == s1.audio[1].t[1]


def test_sample_back_to_back_montage():
    # s2 は video ドライバ。a.mp4[0,4] → b.mp4[4,7]、duration = video.end = 7
    resolved, _ = resolve(_sample())
    s2 = resolved.scenes[1]
    assert s2.video[0].t == (0.0, 4.0)
    assert s2.video[1].t == (4.0, 7.0)
    assert s2.duration == 7.0


def test_sample_cross_lane_ref():
    # s1 telop は v1/v2 の end/start を参照して同期する
    resolved, _ = resolve(_sample())
    s1 = resolved.scenes[0]
    assert s1.telop[0].t == (0.0, s1.audio[0].t[1])      # [0, v1.end]
    assert s1.telop[1].t == (s1.audio[1].t[0], s1.audio[1].t[1])  # [v2.start, v2.end]


def test_synthetic_ids_are_stripped():
    # after 脱糖で振った合成 id は解決後の出力に残らない
    resolved, _ = resolve(_sample())
    for scene in resolved.scenes:
        for lane in ("video", "audio", "telop", "overlay"):
            for el in getattr(scene, lane):
                assert el.id is None or not el.id.startswith("__vsafter_")


def test_idempotent():
    resolved, _ = resolve(_sample())
    again, _ = resolve(resolved)
    assert again.to_json_dict() == resolved.to_json_dict()


# --- 段階出力 ---------------------------------------------------------------


def test_until_normalize_desugars_after_only():
    norm, _ = resolve(_sample(), until="normalize")
    # after は ref に脱糖されるが、auto はまだ残る
    s2v1_start = norm.scenes[1].video[1].t[0]
    assert isinstance(s2v1_start, RefObject)
    assert s2v1_start.ref.endswith(".end")
    assert norm.scenes[1].video[1].t[1] == "auto"


# --- after / gap の細部 ------------------------------------------------------


def test_first_after_is_zero_and_gap_folds():
    doc = VideoScore(
        scenes=[
            Scene(
                id="s",
                duration=10.0,
                telop=[
                    TelopElement(t=("after", 2.0), text="a"),                 # 先頭 after = 0
                    TelopElement(t=("after", "auto", {"gap": 0.5}), text="b"),  # gap 畳み込み
                ],
            )
        ]
    )
    norm, _ = resolve(doc, until="normalize")
    t = norm.scenes[0].telop
    assert t[0].t[0] == 0.0
    assert isinstance(t[1].t[0], RefObject)
    assert t[1].t[0].offset == 0.5


# --- 異常系の診断 ------------------------------------------------------------


def test_cycle_is_diagnosed():
    # a.start -> b.start, b.start -> a.start の相互参照で循環
    doc = VideoScore(
        scenes=[
            Scene(
                id="s",
                duration=5.0,
                telop=[
                    TelopElement(id="a", t=(RefObject(ref="b.start"), 5.0), text="a"),
                    TelopElement(id="b", t=(RefObject(ref="a.start"), 5.0), text="b"),
                ],
            )
        ]
    )
    _, diags = resolve(doc)
    assert any(d.kind == "cycle" for d in diags)


def test_dangling_ref_is_diagnosed():
    doc = VideoScore(
        scenes=[
            Scene(
                id="s",
                duration=5.0,
                telop=[TelopElement(t=(RefObject(ref="nope.end"), 1.0), text="x")],
            )
        ]
    )
    _, diags = resolve(doc)
    assert any(d.kind == "dangling-ref" for d in diags)


def test_unresolved_auto_is_partial_not_error():
    # telop は固有尺を持たない → end="auto" は解けず warning（部分解決）
    doc = VideoScore(
        scenes=[Scene(id="s", duration=5.0, telop=[TelopElement(t=(0.0, "auto"), text="x")])]
    )
    resolved, diags = resolve(doc)
    assert any(d.kind == "unresolved-auto" for d in diags)
    assert resolved.scenes[0].telop[0].t[1] == "auto"  # 未解決のまま残る


# --- プロバイダ / 実体化 -----------------------------------------------------


def test_mock_tts_length_fills_out_and_drives_duration():
    # tts のテキスト長から尺が決まり、out 補完 → auto 解決 → duration まで波及
    doc = VideoScore(
        scenes=[
            Scene(
                id="s",
                duration=RefObject(ref="audio.end"),
                audio=[{"role": "voice", "source": "tts://" + "あ" * 10, "t": (0.0, "auto")}],
            )
        ]
    )
    ctx = default_context()
    resolved, _ = resolve(doc, ctx)
    el = resolved.scenes[0].audio[0]
    assert el.out == 10 * MockProvider().tts_seconds_per_char
    assert el.t == (0.0, el.out)
    assert resolved.scenes[0].duration == el.out
    assert el.source.startswith("mock://")  # 記号 source は実体パスへ書き換え


def test_custom_provider_via_registry():
    registry = ProviderRegistry().set_fallback(MockProvider(tts_seconds_per_char=1.0))
    ctx = ResolveContext(providers=registry)
    doc = VideoScore(
        scenes=[
            Scene(
                id="s",
                duration=5.0,
                audio=[{"role": "voice", "source": "tts://" + "x" * 3, "t": (0.0, "auto")}],
            )
        ]
    )
    resolved, _ = resolve(doc, ctx)
    assert resolved.scenes[0].audio[0].t[1] == 3.0


# --- パイプライン機構 --------------------------------------------------------


def test_topo_order_respects_dependencies():
    names = [p.name for p in topo_order(list(DEFAULT_PASSES))]
    assert names.index("normalize") < names.index("materialize")
    assert names.index("materialize") < names.index("resolve-time")
    assert names.index("resolve-time") < names.index("validate-resolved")


# --- annotations / crop は解決で素通し（v0.2.0） -------------------------------


def test_annotations_and_crop_survive_resolve() -> None:
    ann = {"refs": ["src_01#ev_0042"], "note": "hook"}
    doc = VideoScore.model_validate(
        {
            "meta": {"schemaVersion": "0.2.0"},
            "audio": [{"role": "music", "source": "bgm.mp3", "t": [0, {"ref": "scenes.end"}], "annotations": ann}],
            "scenes": [
                {
                    "id": "s1",
                    "duration": {"ref": "video.end"},
                    "annotations": ann,
                    "video": [
                        {"source": "a.mp4", "in": 1, "out": 3, "t": [0, "auto"], "crop": [0.2, 0, 0.6, 1], "annotations": ann},
                        {"source": "b.mp4", "in": 0, "out": 2, "t": ["after", "auto"], "annotations": ann},
                    ],
                    "telop": [{"t": [0, {"ref": "video.end"}], "text": "x", "annotations": ann}],
                }
            ],
        }
    )
    resolved, diags = resolve(doc)
    assert not [d for d in diags if d.severity == "error"]
    assert _all_times_concrete(resolved)
    s = resolved.scenes[0]
    assert s.annotations == ann
    assert s.video[0].annotations == ann and s.video[1].annotations == ann
    assert s.video[0].crop == (0.2, 0, 0.6, 1)
    assert s.telop[0].annotations == ann
    assert resolved.audio[0].annotations == ann
    assert resolved.meta.schemaVersion == "0.2.0"
    # JSON 往復でも残る
    again = VideoScore.model_validate(resolved.to_json_dict())
    assert again.scenes[0].video[0].annotations == ann
