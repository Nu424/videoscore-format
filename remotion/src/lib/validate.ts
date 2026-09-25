// 入力が「解決済み VideoScore」かを検査する（Python の validate-resolved の要点）。
// 未解決の値が残っていれば、プレイヤーは描画せずエラー画面を出す。

import { isNumber } from './time'
import type { LaneElement, VideoScore } from './types'

/** プレイヤーが前提とする形式バージョン（videoscore の SCHEMA_VERSION と揃える）。 */
export const PLAYER_SCHEMA_VERSION = '0.2.0'

const LANES = ['video', 'audio', 'telop', 'overlay'] as const
const SYMBOLIC_SCHEMES = ['tts', 't2i', 't2v']

const describe = (v: unknown): string => (typeof v === 'object' ? JSON.stringify(v) : String(v))

function checkElement(el: LaneElement, where: string, out: string[]): void {
  const [s, e] = el.t
  if (!isNumber(s)) out.push(`${where}.t[0] が未解決: ${describe(s)}`)
  if (!isNumber(e)) out.push(`${where}.t[1] が未解決: ${describe(e)}`)
  if (el.t.length === 3) out.push(`${where}.t に gap が残っている（未解決）`)
  if ('source' in el) {
    const scheme = el.source.includes('://') ? el.source.split('://', 1)[0] : ''
    if (SYMBOLIC_SCHEMES.includes(scheme)) out.push(`${where}.source が未実体化: ${el.source}`)
  }
}

/** 未解決の箇所を人間が読める文字列のリストで返す（空なら解決済み）。 */
export function findUnresolved(score: VideoScore | null | undefined): string[] {
  const out: string[] = []
  if (!score || !Array.isArray(score.scenes)) {
    return ['VideoScore が渡されていない（props.score が空）']
  }
  for (const lane of LANES) {
    ;(score[lane] ?? []).forEach((el, i) => checkElement(el, `$.${lane}[${i}]`, out))
  }
  score.scenes.forEach((scene, si) => {
    const label = `$.scenes[${si}(${scene.id})]`
    if (!isNumber(scene.duration)) out.push(`${label}.duration が未解決: ${describe(scene.duration)}`)
    for (const lane of LANES) {
      ;(scene[lane] ?? []).forEach((el, i) => checkElement(el, `${label}.${lane}[${i}]`, out))
    }
  })
  return out
}

/** meta.schemaVersion がプレイヤーの前提（major.minor）と違えば警告文を返す。 */
export function schemaVersionWarning(score: VideoScore): string | null {
  const v = score.meta?.schemaVersion
  if (!v) return null
  const mm = (x: string) => x.split('.').slice(0, 2).join('.')
  return mm(v) === mm(PLAYER_SCHEMA_VERSION)
    ? null
    : `schemaVersion ${v} はプレイヤーの前提 ${PLAYER_SCHEMA_VERSION} と異なる（描画は試みる）`
}
