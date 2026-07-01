"""videoscore.resolve クイックスタート（Python スクリプト版）。

絵コンテ的な VideoScore（過少指定）を、解決パイプラインで段階的に清書方向へ具体化する
一連の流れを実演する。

    VideoScore（authored）
      → normalize      after→ref 脱糖 / gap 畳み込み
      → materialize     tts:// 等を実体化し、実測長を out に補完（mock プロバイダ）
      → resolve-time    auto/ref を DAG で具体秒へ
      → validate-resolved  §7 の不変条件を表明
      = 解決済み VideoScore（時間は全部具体・スタイルは意味のまま）

実行:  python examples/resolve_pipeline.py
事前に型パッケージを入れておく（このリポジトリの python/ で `pip install -e .`）。
"""

from __future__ import annotations

import json

from videoscore.model import RefObject, Scene, TelopElement, VideoScore
from videoscore.resolve import (
    MockProvider,
    ProviderRegistry,
    ResolveContext,
    default_context,
    resolve,
)


def rule(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def show_times(doc: VideoScore) -> None:
    """各シーンの duration と要素の t を1行ずつ表示（解決の進み具合が見える）。"""
    for scene in doc.scenes:
        print(f"  scene {scene.id}: duration={scene.duration!r}")
        for lane in ("video", "audio", "telop", "overlay"):
            for i, el in enumerate(getattr(scene, lane)):
                label = getattr(el, "text", None) or getattr(el, "source", "")
                print(f"    {lane}[{i}] t={tuple(el.t)!r}  ({label})")


# 絵コンテ的な入力: 音声ドライバ + after 連結 + レーン跨ぎ ref + auto フィラー ---------
AUTHORED = """
{
  "meta": { "title": "解決デモ", "fps": 30, "size": [1920, 1080] },
  "scenes": [
    {
      "id": "s1",
      "duration": { "ref": "audio.end" },
      "video": [
        { "source": "broll.mp4", "in": 5, "out": 12, "t": [0, "auto"] }
      ],
      "audio": [
        { "id": "v1", "role": "voice", "source": "tts://まずは結論から",     "t": [0,       "auto"] },
        {            "role": "voice", "source": "tts://理由を3つ挙げます",   "t": ["after", "auto"] }
      ],
      "telop": [
        { "t": [0, { "ref": "v1.end" }], "text": "まずは結論から", "style": "tone.emphasis" }
      ],
      "overlay": [
        { "source": "logo.png", "t": [0.5, "auto"], "style": "position.corner" }
      ]
    },
    {
      "id": "s2",
      "duration": { "ref": "video.end" },
      "video": [
        { "source": "a.mp4", "in": 0,  "out": 4,  "t": [0,       "auto"] },
        { "source": "b.mp4", "in": 10, "out": 13, "t": ["after", "auto"] }
      ],
      "telop": [
        { "t": [1.0, 6.0], "text": "カットを跨ぐテロップ", "style": "telop.default" }
      ]
    }
  ]
}
"""


def main() -> None:
    doc = VideoScore.model_validate_json(AUTHORED)

    rule("0. authored（絵コンテ: 時間語彙は素のまま）")
    show_times(doc)

    # --- 段階1: normalize まで（after が ref に脱糖され、auto はまだ残る） ------------
    rule("1. until='normalize'（after→ref 脱糖のみ）")
    norm, _ = resolve(doc, until="normalize")
    show_times(norm)
    print("  → s2 video[1].start が直前要素への参照に脱糖された:",
          norm.scenes[1].video[1].t[0])

    # --- 段階2: フル解決（既定コンテキスト = mock プロバイダ入り） --------------------
    rule("2. フル解決（materialize → resolve-time → validate）")
    resolved, diags = resolve(doc)
    show_times(resolved)

    rule("2b. 診断（例外でなくリストで返る。空 or warning のみなら実質OK）")
    if not diags:
        print("  （診断なし）")
    for d in diags:
        print(" ", d)
    print("  errors:", sum(1 for d in diags if d.severity == "error"))

    rule("2c. 解決済み VideoScore（最小 JSON。スタイルは意味のまま残る点に注目）")
    print(json.dumps(resolved.to_json_dict()["scenes"][0], ensure_ascii=False, indent=2))

    # --- べき等: 解決済みをもう一度解決しても変わらない -----------------------------
    rule("3. べき等（resolve(resolve(x)) == resolve(x)）")
    again, _ = resolve(resolved)
    print("  idempotent:", again.to_json_dict() == resolved.to_json_dict())

    # --- プロバイダ差し替え: 実体解決の尺の出所を制御できる -------------------------
    rule("4. プロバイダ差し替え（tts の秒/文字を変える → 全体の尺が変わる）")
    slow = ResolveContext(providers=ProviderRegistry().set_fallback(
        MockProvider(tts_seconds_per_char=0.3)))
    r_slow, _ = resolve(doc, slow)
    print("  既定 s1.duration:", resolve(doc, default_context())[0].scenes[0].duration)
    print("  0.3s/字 s1.duration:", r_slow.scenes[0].duration)

    # --- 部分解決: 解けないものは error でなく診断＋そのまま残る ---------------------
    rule("5. 部分解決（telop は固有尺を持たない → end='auto' は解けず warning）")
    partial = VideoScore(scenes=[Scene(
        id="p", duration=5.0,
        telop=[TelopElement(t=(0.0, "auto"), text="固有尺のないauto")])])
    pr, pdiags = resolve(partial)
    print("  telop.t（未解決のまま残る）:", tuple(pr.scenes[0].telop[0].t))
    for d in pdiags:
        print(" ", d)


if __name__ == "__main__":
    main()
