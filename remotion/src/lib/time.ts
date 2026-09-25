// 秒 → フレームの換算と、シーンの連結（累積オフセット）。
// 換算規則は Python の videoscore.export.common と同じ: start_f = round(s·fps)、
// 尺 = round(e·fps) - start_f（隣接要素が 1 フレームも重ならず隙間なく並ぶ）。

import type { LaneElement, Scene, VideoScore } from './types'

export const DEFAULT_FPS = 30
export const DEFAULT_SIZE: [number, number] = [1920, 1080]

export const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v)

export const secToFrame = (sec: number, fps: number): number => Math.round(sec * fps)

/** 秒区間 [start, end) → { from, durationInFrames }（最短 1 フレーム）。 */
export function spanToFrames(start: number, end: number, fps: number): { from: number; durationInFrames: number } {
  const from = secToFrame(start, fps)
  const to = secToFrame(end, fps)
  return { from, durationInFrames: Math.max(1, to - from) }
}

/** 要素の配置 t（解決済みなら両端とも数値）を取り出す。未解決なら null。 */
export function elementSpan(el: LaneElement): [number, number] | null {
  const [s, e] = el.t
  return isNumber(s) && isNumber(e) ? [s, e] : null
}

/** シーン尺（解決済みなら数値）。未解決なら 0 とみなす（呼び側が別途エラーにする）。 */
export const sceneSeconds = (scene: Scene): number => (isNumber(scene.duration) ? scene.duration : 0)

/** 各シーンの開始秒（直前までのシーン尺の累積）。 */
export function sceneOffsets(scenes: Scene[]): number[] {
  const out: number[] = []
  let acc = 0
  for (const sc of scenes) {
    out.push(acc)
    acc += sceneSeconds(sc)
  }
  return out
}

const LANES = ['video', 'audio', 'telop', 'overlay'] as const

/** 動画全体の尺（秒）: 全シーン尺の合計と、トップレベルレーン要素の end の最大値の大きい方。 */
export function totalSeconds(score: VideoScore): number {
  let total = score.scenes.reduce((acc, sc) => acc + sceneSeconds(sc), 0)
  for (const lane of LANES) {
    for (const el of score[lane] ?? []) {
      const span = elementSpan(el)
      if (span) total = Math.max(total, span[1])
    }
  }
  return total
}

export const scoreFps = (score: VideoScore): number => {
  const fps = score.meta?.fps
  return isNumber(fps) && fps > 0 ? fps : DEFAULT_FPS
}

export const scoreSize = (score: VideoScore): [number, number] => {
  const size = score.meta?.size
  return size && isNumber(size[0]) && isNumber(size[1]) ? [size[0], size[1]] : DEFAULT_SIZE
}
