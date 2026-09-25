// VideoScore から Remotion のメタデータ（尺・fps・サイズ）を決める。
//
// <Composition calculateMetadata={calculateMetadata} .../> に渡す。あわせて、crop・配置の
// 計算に要る素材の画素サイズ（sourceSizes）を、props に無いものだけブラウザで実測して補う。

import type { CalculateMetadataFunction } from 'remotion'
import { makeDefaultResolveSrc, type ResolveSrc } from './resolveSrc'
import { scoreFps, scoreSize, secToFrame, totalSeconds } from './time'
import type { LaneElement, Size, SourceSizes, VideoScore } from './types'
import { findUnresolved } from './validate'
import { isImageSource, scoreFromProps, type VideoScoreInputProps } from './VideoScoreComposition'

/** 未解決の VideoScore のときの尺（エラー画面を見せるため）。 */
const ERROR_SECONDS = 3

export interface VideoScoreMetadata {
  durationInFrames: number
  fps: number
  width: number
  height: number
}

/** VideoScore から尺・fps・サイズを計算する（純粋関数。実測はしない）。 */
export function videoScoreMetadata(score: VideoScore | undefined): VideoScoreMetadata {
  if (!score || findUnresolved(score).length > 0) {
    const fps = score ? scoreFps(score) : 30
    const [width, height] = score ? scoreSize(score) : [1920, 1080]
    return { durationInFrames: secToFrame(ERROR_SECONDS, fps), fps, width, height }
  }
  const fps = scoreFps(score)
  const [width, height] = scoreSize(score)
  const seconds = totalSeconds(score)
  return { durationInFrames: Math.max(1, secToFrame(seconds, fps)), fps, width, height }
}

/** crop/配置の計算に素材サイズが要る（画を持つ media の）source 一覧。 */
export function visualSources(score: VideoScore): string[] {
  const out = new Set<string>()
  const add = (els: LaneElement[] | null | undefined) => {
    for (const el of els ?? []) if ('source' in el && !('role' in el)) out.add(el.source)
  }
  add(score.video)
  add(score.overlay)
  for (const sc of score.scenes ?? []) {
    add(sc.video)
    add(sc.overlay)
  }
  return [...out]
}

/** ブラウザで素材の画素サイズを測る（失敗・タイムアウトは null）。 */
export function probeMediaSize(url: string, image: boolean, timeoutMs = 8000): Promise<Size | null> {
  if (typeof document === 'undefined') return Promise.resolve(null)
  return new Promise((resolve) => {
    const done = (v: Size | null) => {
      clearTimeout(timer)
      resolve(v)
    }
    const timer = setTimeout(() => done(null), timeoutMs)
    if (image) {
      const img = new Image()
      img.onload = () => done(img.naturalWidth > 0 ? [img.naturalWidth, img.naturalHeight] : null)
      img.onerror = () => done(null)
      img.src = url
    } else {
      const v = document.createElement('video')
      v.preload = 'metadata'
      v.muted = true
      v.onloadedmetadata = () => done(v.videoWidth > 0 ? [v.videoWidth, v.videoHeight] : null)
      v.onerror = () => done(null)
      v.src = url
    }
  })
}

/** 与えられた sourceSizes に無い素材のサイズを実測して補った SourceSizes を返す。 */
export async function measureSourceSizes(
  score: VideoScore,
  resolveSrc: ResolveSrc,
  known: SourceSizes = {},
): Promise<SourceSizes> {
  const sizes: SourceSizes = { ...known }
  const missing = visualSources(score).filter((s) => !sizes[s])
  const results = await Promise.all(missing.map((s) => probeMediaSize(resolveSrc(s), isImageSource(s))))
  missing.forEach((s, i) => {
    const r = results[i]
    if (r) sizes[s] = r
  })
  return sizes
}

/**
 * calculateMetadata を作る。resolveSrc を差し替えたいとき用（既定は props.mediaBase で staticFile）。
 * probe=false で素材サイズの実測をしない（sourceSizes を必ず渡す運用のとき）。
 */
export function makeCalculateMetadata<P extends VideoScoreInputProps>(
  options: { resolveSrc?: ResolveSrc; probe?: boolean } = {},
): CalculateMetadataFunction<P> {
  return async ({ props }) => {
    const score = scoreFromProps(props)
    const meta = videoScoreMetadata(score)
    if (!score || options.probe === false || findUnresolved(score).length > 0) return meta
    const resolveSrc = options.resolveSrc ?? makeDefaultResolveSrc(props.mediaBase)
    const sourceSizes = await measureSourceSizes(score, resolveSrc, props.sourceSizes)
    return { ...meta, props: { ...props, sourceSizes } }
  }
}

/** 既定の calculateMetadata（尺・fps・サイズを VideoScore から決め、素材サイズを実測で補う）。 */
export const calculateMetadata: CalculateMetadataFunction<VideoScoreInputProps> = makeCalculateMetadata()
