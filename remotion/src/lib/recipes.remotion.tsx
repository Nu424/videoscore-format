// Remotion 用レシピ（カタログ三層の実装層）。
//
// スタイルの印（id）→ React コンポーネント / 配置の props。**カタログと同じ id で結合する**
// （aup2 の recipes.aup2.json と同じ考え方）。標準カタログの全 id を持つことは
// `Record<StandardStyleId, RemotionRecipe>` の型で担保する（§7 網羅）。
// 生の色・px はこの層に閉じる（中間構造・AI には出さない）。大きさはフレーム寸法に対する比率で書く。

import React from 'react'
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion'
import type { StandardStyleId } from 'videoscore'
import type { Fit, Rect } from './layout'
import type { TelopElement } from './types'

/** telop レシピのコンポーネントが受け取る props。 */
export interface TelopRecipeProps {
  text: string
  element: TelopElement
  /** フレーム寸法（px）。 */
  width: number
  height: number
}

/** video / overlay の収め方。 */
export interface VisualLayout {
  /** フレーム内の箱（既定: フレーム全体）。 */
  box?: (width: number, height: number) => Rect
  /** 箱への収め方。contain = 全体を見せる / cover = 箱を埋める（はみ出しは切る）。 */
  fit: Fit
  /** 箱の背景（contain で余った帯の色）。未指定なら透明。 */
  background?: string
}

/** 1つの印の Remotion 展開規則。レーンに応じて使う口が違う。 */
export interface RemotionRecipe {
  /** telop: テキストを描くコンポーネント。 */
  Telop?: React.FC<TelopRecipeProps>
  /** video / overlay: 配置。 */
  layout?: VisualLayout
  /** audio: 音量（0〜1）。 */
  volume?: number
}

/** 印 id → レシピ。プロジェクト固有の印は `{...standardRemotionRecipes, 'my.style': {...}}` で足す。 */
export type RemotionRecipeBook = Record<string, RemotionRecipe>

// ---- 共通の見た目（レシピ層に閉じる） ------------------------------------------

const FONT_FAMILY =
  '"Noto Sans JP", "Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", sans-serif'

const baseText = (size: number): React.CSSProperties => ({
  fontFamily: FONT_FAMILY,
  fontSize: size,
  lineHeight: 1.3,
  color: '#ffffff',
  textAlign: 'center',
  whiteSpace: 'pre-wrap',
  overflowWrap: 'anywhere',
})

/** 縁取り（stroke を塗りの下に描く）。 */
const outline = (px: number, color = '#000000'): React.CSSProperties => ({
  WebkitTextStroke: `${px}px ${color}`,
  paintOrder: 'stroke fill',
})

/** 横いっぱいの帯（top か bottom を px で指定）に中央寄せで置く。 */
const Band: React.FC<{ top?: number; bottom?: number; width: number; children: React.ReactNode }> = ({
  top,
  bottom,
  width,
  children,
}) => (
  <div
    style={{
      position: 'absolute',
      left: width * 0.05,
      right: width * 0.05,
      top,
      bottom,
      display: 'flex',
      justifyContent: 'center',
    }}
  >
    {children}
  </div>
)

/** 出現を少しだけやわらげる（数フレームのフェードイン）。 */
const useFadeIn = (frames = 4): number => {
  const frame = useCurrentFrame()
  return interpolate(frame, [0, frames], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
}

// ---- telop --------------------------------------------------------------------

/** telop.default: 下寄りの中央に、白文字＋黒縁の素直なテロップ。 */
export const TelopDefault: React.FC<TelopRecipeProps> = ({ text, width, height }) => {
  const size = Math.min(width, height) * 0.05
  const opacity = useFadeIn()
  return (
    <Band bottom={height * 0.08} width={width}>
      <div style={{ ...baseText(size), ...outline(size * 0.12), fontWeight: 600, opacity }}>{text}</div>
    </Band>
  )
}

/** telop.caption: 発話字幕。大きく太く、縁取りで読みやすく、下の帯に置く。 */
export const TelopCaption: React.FC<TelopRecipeProps> = ({ text, width, height }) => {
  const size = Math.min(width, height) * 0.07
  const portrait = height > width
  return (
    <Band bottom={height * (portrait ? 0.14 : 0.07)} width={width}>
      <div style={{ ...baseText(size), ...outline(size * 0.16), fontWeight: 900 }}>{text}</div>
    </Band>
  )
}

/** telop.title: 冒頭の看板。上の帯に、太字を半透明の座布団つきで。 */
export const TelopTitle: React.FC<TelopRecipeProps> = ({ text, width, height }) => {
  const size = Math.min(width, height) * 0.085
  const portrait = height > width
  const { fps } = useVideoConfig()
  const frame = useCurrentFrame()
  const pop = spring({ frame, fps, config: { damping: 200 }, durationInFrames: Math.round(fps * 0.4) })
  return (
    <Band top={height * (portrait ? 0.12 : 0.08)} width={width}>
      <div
        style={{
          ...baseText(size),
          ...outline(size * 0.1),
          fontWeight: 900,
          padding: `${size * 0.2}px ${size * 0.5}px`,
          borderRadius: size * 0.25,
          background: 'rgba(0, 0, 0, 0.45)',
          opacity: pop,
          transform: `translateY(${(1 - pop) * -size * 0.4}px)`,
        }}
      >
        {text}
      </div>
    </Band>
  )
}

/** tone.emphasis: 一番伝えたい一言。中央に大きく、色と縁取りと小さな弾みで前に出す。 */
export const TelopEmphasis: React.FC<TelopRecipeProps> = ({ text, width, height }) => {
  const size = Math.min(width, height) * 0.09
  const { fps } = useVideoConfig()
  const frame = useCurrentFrame()
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 180 } })
  return (
    <div
      style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <div
        style={{
          ...baseText(size),
          ...outline(size * 0.18, '#1a1a1a'),
          maxWidth: width * 0.9,
          fontWeight: 900,
          color: '#ffd400',
          textShadow: `0 ${size * 0.08}px ${size * 0.2}px rgba(0,0,0,0.6)`,
          transform: `scale(${interpolate(pop, [0, 1], [0.6, 1])})`,
        }}
      >
        {text}
      </div>
    </div>
  )
}

// ---- 配置 ----------------------------------------------------------------------

/** 既定の映像配置: フレーム全体に全体を収める（余りは黒）。 */
export const DEFAULT_VIDEO_LAYOUT: VisualLayout = { fit: 'contain', background: '#000000' }

/** 既定の overlay 配置: フレーム全体に収める（背景は透明）。 */
export const DEFAULT_OVERLAY_LAYOUT: VisualLayout = { fit: 'contain' }

// ---- 標準カタログのレシピ --------------------------------------------------------

/** 標準カタログ（videoscore の STANDARD_STYLE_CATALOG）の全 id に対する Remotion レシピ。 */
export const standardRemotionRecipes: Record<StandardStyleId, RemotionRecipe> = {
  'telop.default': { Telop: TelopDefault },
  'telop.caption': { Telop: TelopCaption },
  'telop.title': { Telop: TelopTitle },
  'tone.emphasis': { Telop: TelopEmphasis },
  // 横長素材を幅に合わせて中央に置き、上下は暗い帯（タイトル・字幕の置き場）。
  'layout.vertical-fit': { layout: { fit: 'contain', background: '#0b0b0f' } },
  // crop 領域（未指定なら素材全体の中央）でフレームを埋める。
  'layout.vertical-crop': { layout: { fit: 'cover', background: '#000000' } },
  'audio.default': { volume: 1 },
  // 右上の隅に小さく（フレーム短辺の 18% の正方形の箱に収める）。
  'position.corner': {
    layout: {
      fit: 'contain',
      box: (w, h) => {
        const s = Math.min(w, h) * 0.18
        const m = Math.min(w, h) * 0.04
        return { left: w - s - m, top: m, width: s, height: s }
      },
    },
  },
}

/** レーンの既定印（カタログの `xxx.default` 思想）。 */
export const LANE_DEFAULT_STYLE = { telop: 'telop.default', audio: 'audio.default' } as const
