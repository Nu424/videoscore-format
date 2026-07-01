"""要素種ごとの既定エフェクト（AviUtl2 の最小構成）。

プロパティ名・既定値は `aviutl2-api` の CLI（実績のある最小構成）とサンプル `.aup2` に準拠する。
ここは「素の器」を作るだけ。スタイル（レシピ）による上書き・フィルタ追記は convert 側で行う。
"""

from __future__ import annotations

from .model import Aup2Effect

__all__ = [
    "standard_draw",
    "audio_playback",
    "text_effects",
    "video_effects",
    "audio_effects",
    "image_effects",
]


def standard_draw(x: float = 0.0, y: float = 0.0, scale: float = 100.0) -> Aup2Effect:
    """`標準描画`（位置・拡大・透明度・合成モード）。映像系オブジェクトの [K.1]。"""
    return Aup2Effect(
        "標準描画",
        {
            "X": x,
            "Y": y,
            "Z": 0.0,
            "Group": 1.0,
            "中心X": 0.0,
            "中心Y": 0.0,
            "中心Z": 0.0,
            "X軸回転": 0.0,
            "Y軸回転": 0.0,
            "Z軸回転": 0.0,
            "拡大率": scale,
            "縦横比": 0.0,
            "透明度": 0.0,
            "合成モード": "通常",
        },
    )


def audio_playback(volume: float = 100.0) -> Aup2Effect:
    """`音声再生`（音量・左右）。音声オブジェクトの [K.1]。"""
    return Aup2Effect("音声再生", {"音量": volume, "左右": 0.0})


def text_effects(content: str, *, size: float = 48.0) -> list[Aup2Effect]:
    """`テキスト` ＋ `標準描画`。改行は \\n エスケープ。"""
    text = Aup2Effect(
        "テキスト",
        {
            "サイズ": size,
            "字間": 0.0,
            "行間": 0.0,
            "表示速度": 0.0,
            "フォント": "Yu Gothic UI",
            "文字色": "ffffff",
            "影・縁色": "000000",
            "文字装飾": "標準文字",
            "文字揃え": "左寄せ[上]",
            "B": 0,
            "I": 0,
            "テキスト": content.replace("\n", "\\n"),
            "文字毎に個別オブジェクト": 0,
            "自動スクロール": 0,
            "移動座標上に表示": 0,
            "オブジェクトの長さを自動調節": 0,
        },
    )
    return [text, standard_draw()]


def video_effects(path: str, *, play_pos: float = 0.0) -> list[Aup2Effect]:
    """`動画ファイル` ＋ `標準描画`。play_pos は素材内トリム開始（秒）。"""
    video = Aup2Effect(
        "動画ファイル",
        {
            "再生位置": play_pos,
            "再生速度": 100.0,
            "ループ再生": 0,
            "アルファチャンネルを読み込む": 0,
            "ファイル": path,
        },
    )
    return [video, standard_draw()]


def audio_effects(path: str, *, play_pos: float = 0.0) -> list[Aup2Effect]:
    """`音声ファイル` ＋ `音声再生`。play_pos は素材内トリム開始（秒）。"""
    audio = Aup2Effect(
        "音声ファイル",
        {
            "再生位置": play_pos,
            "再生速度": 100.0,
            "ループ再生": 0,
            "動画ファイルと連携": 0,
            "ファイル": path,
        },
    )
    return [audio, audio_playback()]


def image_effects(path: str) -> list[Aup2Effect]:
    """`画像ファイル` ＋ `標準描画`。"""
    image = Aup2Effect("画像ファイル", {"ファイル": path})
    return [image, standard_draw()]
