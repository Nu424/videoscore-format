// 映像/画像の配置計算（純粋関数）。
//
// VideoScore の `crop` は「元フレームのどこを映すか」だけを持つ。それをフレーム内の
// どの箱（box）にどう収めるか（contain = 全体を収める / cover = 箱を埋める）はレシピが決める。
// ここは (素材サイズ, crop, 箱, 収め方) → CSS 用の矩形を計算するだけ。

import type { Size } from './types'

export interface Rect {
  left: number
  top: number
  width: number
  height: number
}

export type Fit = 'contain' | 'cover'

/** crop 未指定時の領域（元フレーム全体）。 */
export const FULL_CROP: [number, number, number, number] = [0, 0, 1, 1]

export interface Placement {
  /** 箱（フレーム座標）。overflow: hidden で切る。 */
  box: Rect
  /** 箱の中で、切り出し領域が表示される矩形（箱座標）。contain なら箱より小さく、cover なら大きい。 */
  region: Rect
  /** 切り出し領域の中で、素材全体（media 要素）を置く矩形（領域座標）。 */
  media: Rect
}

/**
 * 素材（sourceSize）の crop 領域を、box に fit で収める配置を計算する。
 * media 要素は object-fit: fill で `media` 矩形に描けば、crop 領域がちょうど `region` に来る。
 */
export function placeMedia(
  sourceSize: Size,
  crop: readonly [number, number, number, number] | null | undefined,
  box: Rect,
  fit: Fit,
): Placement {
  const [sw, sh] = sourceSize
  const [x, y, w, h] = crop ?? FULL_CROP
  const cw = w * sw
  const ch = h * sh
  const scale =
    fit === 'cover' ? Math.max(box.width / cw, box.height / ch) : Math.min(box.width / cw, box.height / ch)
  const rw = cw * scale
  const rh = ch * scale
  return {
    box,
    region: { left: (box.width - rw) / 2, top: (box.height - rh) / 2, width: rw, height: rh },
    media: { left: -x * sw * scale, top: -y * sh * scale, width: sw * scale, height: sh * scale },
  }
}

/** フレーム全体の箱。 */
export const fullFrame = (width: number, height: number): Rect => ({ left: 0, top: 0, width, height })
