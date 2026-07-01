"""VideoScore → 解決 → .aup2 書き出し（Python スクリプト版）。

絵コンテ的な VideoScore を解決し、AviUtl2 の `.aup2` プロジェクトへ変換する一連の流れを実演する。

    VideoScore（authored）
      → resolve            時間を具体化・tts:// 等を実体化（解決済み VideoScore）
      → render_aup2        シーンを frame 連結・要素をオブジェクト化・スタイルをレシピ展開
      = .aup2（AviUtl2 プロジェクト。UTF-8/CRLF・フレーム単位・日本語プロパティ）

スタイルの意味的な印（tone.emphasis 等）は recipes.aup2.json で AviUtl2 の具体エフェクト
（縁取り文字・ドロップシャドウ・座標/拡大率…）へ展開される。生の hex/px はレシピ層に閉じる。

実行:  python examples/export_aup2.py
事前に型パッケージを入れておく（このリポジトリの python/ で `pip install -e .`）。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from videoscore.model import VideoScore
from videoscore.export import dump_aup2, render_aup2
from videoscore.export.recipes import load_recipes
from videoscore.resolve import resolve


def rule(title: str) -> None:
    print(f"\n{'=' * 4} {title} {'=' * 4}")


def show_objects(project) -> None:
    """生成された各オブジェクトの レイヤー / frame / 種別 を1行ずつ表示。"""
    for i, obj in enumerate(project.scene.objects):
        kind = obj.effects[0].name if obj.effects else "?"
        extra = [e.name for e in obj.effects[1:]]
        print(f"  [{i}] layer={obj.layer:>2}  frame={obj.frame_start},{obj.frame_end}  {kind}  +{extra}")


# 絵コンテ的な入力: s1=音声ドライバ / s2=分割画面（同時2クリップ） ------------------
AUTHORED = """
{
  "meta": { "title": "aup2 書き出しデモ", "fps": 30, "size": [1920, 1080] },
  "scenes": [
    {
      "id": "s1",
      "duration": { "ref": "audio.end" },
      "video": [
        { "source": "broll.mp4", "in": 5, "t": [0, { "ref": "audio.end" }] }
      ],
      "audio": [
        { "id": "v1", "role": "voice", "source": "tts://まずは結論から述べます", "t": [0, "auto"] }
      ],
      "telop": [
        { "t": [0, { "ref": "v1.end" }], "text": "まずは結論から", "style": "tone.emphasis" }
      ],
      "overlay": [
        { "source": "logo.png", "t": [0, { "ref": "audio.end" }], "style": "position.corner" }
      ]
    },
    {
      "id": "s2",
      "duration": 3.0,
      "video": [
        { "source": "left.mp4",  "in": 0, "out": 3, "t": [0, 3.0], "style": "layout.split-left" },
        { "source": "right.mp4", "in": 0, "out": 3, "t": [0, 3.0], "style": "layout.split-right" }
      ],
      "telop": [
        { "t": [0.5, 2.5], "text": "同時分割", "style": "telop.default" }
      ]
    }
  ]
}
"""


def main() -> None:
    doc = VideoScore.model_validate_json(AUTHORED)

    # --- 1. 解決（時間の具体化・実体化） ------------------------------------------
    rule("1. resolve（絵コンテ → 解決済み VideoScore）")
    resolved, rdiags = resolve(doc)
    print(f"  scenes: s1.duration={resolved.scenes[0].duration!r}  s2.duration={resolved.scenes[1].duration!r}")
    print(f"  解決の診断: {len(rdiags)} 件（warning のみなら実質OK）")

    # --- 2. .aup2 へ変換（レシピ展開・レイヤー割当） ------------------------------
    rule("2. render_aup2（解決済み → .aup2 モデル）")
    project, diags = render_aup2(resolved, project_file="C:/videos/demo.aup2")
    show_objects(project)
    print("\n  変換の診断:")
    for d in diags:
        print("   ", d)
    if not diags:
        print("    （診断なし）")

    # --- 3. .aup2 テキスト（先頭のオブジェクトまで） ------------------------------
    rule("3. .aup2 テキスト（telop がレシピ展開される様子に注目）")
    text = project.to_text()
    # s1 の telop オブジェクト（テキスト＋縁取り＋ドロップシャドウ）あたりを抜粋
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln == "effect.name=テキスト") - 2
    print("\n".join("  " + ln for ln in lines[start:start + 24]))

    # --- 4. ファイルへ書き出し ----------------------------------------------------
    rule("4. dump_aup2（UTF-8/CRLF でファイルへ）")
    out = Path(tempfile.gettempdir()) / "videoscore_demo.aup2"
    dump_aup2(resolved, str(out))
    raw = out.read_bytes()
    crlf_only = (b"\r\n" in raw) and (b"\n" not in raw.replace(b"\r\n", b""))
    print(f"  書き出し: {out}")
    print(f"  bytes={len(raw)}  改行はCRLF only: {crlf_only}")

    # --- 5. レシピ差し替え（意味は同じ・見た目だけ差し替わる） --------------------
    rule("5. レシピ差し替え（tone.emphasis を赤系の装飾に変える）")
    custom = load_recipes({
        "telop.default": {"text": {"フォント": "Meiryo", "サイズ": 64, "文字揃え": "中央[中]"}},
        "tone.emphasis": {"text": {"文字装飾": "縁取り文字(太)", "影・縁色": "ff2222"}},
    })
    p2, _ = render_aup2(resolved, recipes=custom)
    telop = next(o for o in p2.scene.objects if o.effects[0].name == "テキスト")
    props = telop.effects[0].props
    print(f"  フォント={props['フォント']}  サイズ={props['サイズ']}  影・縁色={props['影・縁色']}")
    print("  → VideoScore 側（意味の印）は不変。レシピ層だけで見た目が変わる。")


if __name__ == "__main__":
    main()
