// 要素の source 文字列 → ブラウザで読める URL。
// 既定: http(s)/data/blob の URL はそのまま、相対パスは public/ 配下とみなして staticFile() に通す。
import { staticFile } from 'remotion'

export type ResolveSrc = (source: string) => string

const URL_LIKE = /^(https?:|data:|blob:)/i

/** 既定の解決。`mediaBase`（例 "media/"）を相対パスの前に付けてから staticFile する。 */
export function makeDefaultResolveSrc(mediaBase = ''): ResolveSrc {
  const base = mediaBase && !mediaBase.endsWith('/') ? `${mediaBase}/` : mediaBase
  return (source: string) => {
    if (URL_LIKE.test(source)) return source
    const rel = source.replace(/\\/g, '/').replace(/^\.\//, '').replace(/^\/+/, '')
    return staticFile(`${base}${rel}`)
  }
}

export const defaultResolveSrc: ResolveSrc = makeDefaultResolveSrc()
