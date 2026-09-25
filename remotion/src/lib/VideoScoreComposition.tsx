// 解決済み VideoScore を描画する Remotion コンポーネント。
//
// - シーンは <Sequence> で直列に並べる（開始 = 直前までのシーン尺の累積）。
// - トップレベル（シーン跨ぎ）レーンは動画全体の時計で置く。
// - 描画順（奥→手前）: video → overlay → telop。audio は画を持たない。
// - 見た目は印（style id）→ レシピ（recipes.remotion.tsx）で決める。未知の印は既定で描いて警告。
// - 未解決の値（auto/ref/after/gap・記号 source）が残っていれば、描画せずエラー画面を出す。

import React from 'react'
import { AbsoluteFill, Audio, Img, OffthreadVideo, Sequence, useVideoConfig } from 'remotion'
import { fullFrame, placeMedia } from './layout'
import {
  DEFAULT_OVERLAY_LAYOUT,
  DEFAULT_VIDEO_LAYOUT,
  LANE_DEFAULT_STYLE,
  TelopDefault,
  standardRemotionRecipes,
  type RemotionRecipeBook,
  type VisualLayout,
} from './recipes.remotion'
import { makeDefaultResolveSrc, type ResolveSrc } from './resolveSrc'
import { elementSpan, isNumber, sceneOffsets, secToFrame, spanToFrames } from './time'
import type {
  AudioElement,
  LaneElement,
  Scene,
  Size,
  SourceSizes,
  TelopElement,
  VideoScore,
  VisualElement,
} from './types'
import { findUnresolved, schemaVersionWarning } from './validate'

/**
 * JSON で渡せる props（`--props=...json` や Studio の入力 props）。
 * `{ "score": <解決済み VideoScore>, ... }` の形のほか、解決済み VideoScore そのもの
 * （`{ "meta": ..., "scenes": [...] }`）を props として渡してもよい（`scenes` があればそちらを優先）。
 */
export type VideoScoreInputProps = Partial<VideoScore> & {
  /** 解決済み VideoScore（時刻がすべて数値）。 */
  score?: VideoScore
  /** 相対パスの source に前置する public/ 内のディレクトリ（例 "media/"）。既定 ""。 */
  mediaBase?: string
  /** source → 素材の画素サイズ [幅, 高さ]。crop・配置の計算に使う。未指定分は calculateMetadata が実測で補う。 */
  sourceSizes?: SourceSizes
}

/** コンポーネントの props（コードから使うときは関数も渡せる）。 */
export type VideoScoreCompositionProps = VideoScoreInputProps & {
  /** source → URL の解決。既定は makeDefaultResolveSrc(mediaBase)（URL は素通し・相対は staticFile）。 */
  resolveSrc?: ResolveSrc
  /** 印 id → レシピ。既定は standardRemotionRecipes。 */
  recipes?: RemotionRecipeBook
}

/** props から VideoScore を取り出す（VideoScore 直渡しを優先、無ければ props.score）。 */
export function scoreFromProps(props: VideoScoreInputProps): VideoScore | undefined {
  if (Array.isArray(props.scenes)) {
    const { score: _score, mediaBase: _mb, sourceSizes: _ss, ...rest } = props as VideoScoreCompositionProps
    return rest as VideoScore
  }
  return props.score
}

/** 素材サイズが分からないときの仮定（16:9）。 */
const FALLBACK_VIDEO_SIZE: Size = [1920, 1080]

const IMAGE_EXT = /\.(png|jpe?g|gif|webp|bmp|svg|avif)$/i
export const isImageSource = (source: string): boolean => IMAGE_EXT.test(source.split('?')[0] ?? source)

const warned = new Set<string>()
const warnOnce = (msg: string): void => {
  if (warned.has(msg)) return
  warned.add(msg)
  console.warn(`[videoscore-remotion] ${msg}`)
}

interface Ctx {
  fps: number
  resolveSrc: ResolveSrc
  recipes: RemotionRecipeBook
  sourceSizes: SourceSizes
}

// ---- エラー画面 ------------------------------------------------------------------

export const UnresolvedError: React.FC<{ problems: string[] }> = ({ problems }) => (
  <AbsoluteFill
    style={{
      background: '#2b0000',
      color: '#ffdddd',
      padding: 48,
      fontFamily: 'monospace',
      fontSize: 28,
      lineHeight: 1.4,
    }}
  >
    <div style={{ fontSize: 40, fontWeight: 700, marginBottom: 24, color: '#ff6b6b' }}>
      VideoScore が解決されていません（videoscore.resolve を通してください）
    </div>
    {problems.slice(0, 20).map((p) => (
      <div key={p}>・{p}</div>
    ))}
    {problems.length > 20 ? <div>…ほか {problems.length - 20} 件</div> : null}
  </AbsoluteFill>
)

// ---- 各レーン ----------------------------------------------------------------------

function visualLayout(el: VisualElement, lane: 'video' | 'overlay', ctx: Ctx): VisualLayout {
  const fallback = lane === 'video' ? DEFAULT_VIDEO_LAYOUT : DEFAULT_OVERLAY_LAYOUT
  if (!el.style) return fallback
  const layout = ctx.recipes[el.style]?.layout
  if (!layout) {
    warnOnce(`印 '${el.style}' の ${lane} 用レシピが無い → 既定の配置で描画`)
    return fallback
  }
  return layout
}

const VisualMedia: React.FC<{ el: VisualElement; lane: 'video' | 'overlay'; ctx: Ctx }> = ({ el, lane, ctx }) => {
  const { width, height } = useVideoConfig()
  const layout = visualLayout(el, lane, ctx)
  const box = layout.box ? layout.box(width, height) : fullFrame(width, height)
  const image = isImageSource(el.source)
  let size = ctx.sourceSizes[el.source]
  if (!size) {
    if (el.crop || layout.fit === 'cover' || layout.box) {
      warnOnce(`'${el.source}' の画素サイズが不明 → 16:9 と仮定して配置（sourceSizes で渡せる）`)
    }
    size = FALLBACK_VIDEO_SIZE
  }
  const p = placeMedia(size, el.crop ?? null, box, layout.fit)
  const src = ctx.resolveSrc(el.source)
  const mediaStyle: React.CSSProperties = { position: 'absolute', ...p.media, objectFit: 'fill', maxWidth: 'none' }
  const trimBefore = isNumber(el.in) && el.in > 0 ? secToFrame(el.in, ctx.fps) : undefined
  const trimAfter = isNumber(el.out) ? secToFrame(el.out, ctx.fps) : undefined
  return (
    <div style={{ position: 'absolute', ...box, overflow: 'hidden', background: layout.background }}>
      <div style={{ position: 'absolute', ...p.region, overflow: 'hidden' }}>
        {image ? (
          <Img src={src} style={mediaStyle} />
        ) : (
          // 音は audio レーンが持つ（VideoScore は映像と音声を別レーンに分ける）ので映像は無音で再生。
          <OffthreadVideo src={src} muted trimBefore={trimBefore} trimAfter={trimAfter} style={mediaStyle} />
        )}
      </div>
    </div>
  )
}

const TelopView: React.FC<{ el: TelopElement; ctx: Ctx }> = ({ el, ctx }) => {
  const { width, height } = useVideoConfig()
  const style = el.style ?? LANE_DEFAULT_STYLE.telop
  let Telop = ctx.recipes[style]?.Telop
  if (!Telop) {
    warnOnce(`印 '${style}' の telop 用レシピが無い → ${LANE_DEFAULT_STYLE.telop} で描画`)
    Telop = ctx.recipes[LANE_DEFAULT_STYLE.telop]?.Telop ?? TelopDefault
  }
  return (
    <AbsoluteFill>
      <Telop text={el.text} element={el} width={width} height={height} />
    </AbsoluteFill>
  )
}

const AudioView: React.FC<{ el: AudioElement; ctx: Ctx }> = ({ el, ctx }) => {
  const style = el.style ?? LANE_DEFAULT_STYLE.audio
  const recipe = ctx.recipes[style]
  if (!recipe) warnOnce(`印 '${style}' の audio 用レシピが無い → 既定の音量で再生`)
  const volume = recipe?.volume ?? 1
  const trimBefore = isNumber(el.in) && el.in > 0 ? secToFrame(el.in, ctx.fps) : undefined
  const trimAfter = isNumber(el.out) ? secToFrame(el.out, ctx.fps) : undefined
  return <Audio src={ctx.resolveSrc(el.source)} volume={volume} trimBefore={trimBefore} trimAfter={trimAfter} />
}

/** 1要素を配置 t の区間の <Sequence> に包んで描画する（offset はスコープの開始秒）。 */
const ElementSequence: React.FC<{ lane: string; index: number; el: LaneElement; offset: number; ctx: Ctx; children: React.ReactNode }> = ({
  lane,
  index,
  el,
  offset,
  ctx,
  children,
}) => {
  const span = elementSpan(el)
  if (!span) return null
  const { from, durationInFrames } = spanToFrames(offset + span[0], offset + span[1], ctx.fps)
  const name = `${lane}[${index}]${el.id ? ` ${el.id}` : ''}${el.style ? ` (${el.style})` : ''}`
  return (
    <Sequence from={from} durationInFrames={durationInFrames} name={name}>
      {children}
    </Sequence>
  )
}

type LaneOwner = Pick<Scene, 'video' | 'audio' | 'telop' | 'overlay'> | VideoScore

function renderLane(owner: LaneOwner, lane: 'video' | 'overlay' | 'telop' | 'audio', offset: number, ctx: Ctx, key: string) {
  const els = (owner[lane] ?? []) as LaneElement[]
  return els.map((el, i) => (
    <ElementSequence key={`${key}-${lane}-${i}`} lane={lane} index={i} el={el} offset={offset} ctx={ctx}>
      {lane === 'telop' ? (
        <TelopView el={el as TelopElement} ctx={ctx} />
      ) : lane === 'audio' ? (
        <AudioView el={el as AudioElement} ctx={ctx} />
      ) : (
        <VisualMedia el={el as VisualElement} lane={lane} ctx={ctx} />
      )}
    </ElementSequence>
  ))
}

// ---- 本体 ------------------------------------------------------------------------

/** 解決済み VideoScore を描画する。尺・fps・サイズは calculateMetadata で VideoScore から決める。 */
export const VideoScoreComposition: React.FC<VideoScoreCompositionProps> = (props) => {
  const { mediaBase, sourceSizes, resolveSrc, recipes } = props
  const { fps } = useVideoConfig()
  const score = scoreFromProps(props)
  const problems = findUnresolved(score)
  if (!score || problems.length > 0) return <UnresolvedError problems={problems} />

  const versionWarning = schemaVersionWarning(score)
  if (versionWarning) warnOnce(versionWarning)

  const ctx: Ctx = {
    fps,
    resolveSrc: resolveSrc ?? makeDefaultResolveSrc(mediaBase),
    recipes: recipes ?? standardRemotionRecipes,
    sourceSizes: sourceSizes ?? {},
  }
  const offsets = sceneOffsets(score.scenes)
  const layers = ['video', 'overlay', 'telop', 'audio'] as const

  return (
    <AbsoluteFill style={{ background: '#000000' }}>
      {layers.map((lane) => (
        <React.Fragment key={lane}>
          {score.scenes.map((scene, si) => {
            const off = offsets[si] ?? 0
            const sceneSpan = spanToFrames(off, off + (isNumber(scene.duration) ? scene.duration : 0), fps)
            return (
              <Sequence
                key={`${scene.id}-${lane}`}
                from={sceneSpan.from}
                durationInFrames={sceneSpan.durationInFrames}
                name={`${scene.id} ${lane}`}
              >
                {/* シーン内の要素はシーンの時計（offset 0）で置く */}
                {renderLane(scene, lane, 0, ctx, scene.id)}
              </Sequence>
            )
          })}
          {renderLane(score, lane, 0, ctx, '$')}
        </React.Fragment>
      ))}
    </AbsoluteFill>
  )
}
