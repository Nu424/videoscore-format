// VideoScore の型（videoscore パッケージ＝pydantic から生成された TS 型）を再公開する。
// プレイヤーは型だけを使う（実行時に videoscore パッケージへは依存しない）。
import type {
  AudioElement,
  OverlayElement,
  Scene,
  TelopElement,
  VideoElement,
  VideoScore,
} from 'videoscore'

export type { AudioElement, OverlayElement, Scene, TelopElement, VideoElement, VideoScore }

/** 4レーンの名前。 */
export type LaneName = 'video' | 'audio' | 'telop' | 'overlay'

/** 任意のレーン要素。 */
export type LaneElement = VideoElement | AudioElement | TelopElement | OverlayElement

/** 画を持つ media 要素（crop を持てる）。 */
export type VisualElement = VideoElement | OverlayElement

/** 素材の画素サイズ [幅, 高さ]。 */
export type Size = [number, number]

/** source 文字列 → 画素サイズ。crop と layout の計算に使う。 */
export type SourceSizes = Record<string, Size>
