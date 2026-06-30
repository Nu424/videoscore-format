// schema/*.json (pydantic が出力する JSON Schema = SoT) から TypeScript 型を生成する。
//
// json2ts は draft 2020-12 の prefixItems(タプル) を未サポートで、時間語彙 `t` が
// unknown に劣化する。そこで生成前にスキーマを以下のように前処理(downlevel)する:
//   1. prefixItems -> draft-07 の items:[...] へ（json2ts が正しいタプルを出す）
//   2. JSON Schema の title アノテーション(文字列)を除去（プロパティ毎の別名爆発を防ぐ）
//      ※ properties 配下の「title という名のフィールド」は値がオブジェクトなので残る
//
// 生成物 src/*.gen.ts はコミットする（TS 利用者は Python 不要）。
//
// 使い方:
//   node scripts/gen-types.mjs           # src/*.gen.ts を書き出す
//   node scripts/gen-types.mjs --check   # 書き込まず、差分があれば非0終了（CI用）

import { compile } from 'json-schema-to-typescript'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const here = dirname(fileURLToPath(import.meta.url))
const schemaDir = resolve(here, '../../schema')
const srcDir = resolve(here, '../src')

// ファイル名(schema) -> [ルート型名, 出力ファイル]
const TARGETS = [
  { schema: 'videoscore.schema.json', name: 'VideoScore', out: 'videoscore.gen.ts' },
  { schema: 'style-catalog.schema.json', name: 'StyleCatalog', out: 'style-catalog.gen.ts' },
]

const BANNER = `/**
 * このファイルは schema/*.json から自動生成される。手で編集しないこと。
 * 生成元は pydantic モデル(videoscore.model)。再生成: pnpm gen
 */`

function downlevel(node) {
  if (Array.isArray(node)) return node.map(downlevel)
  if (node && typeof node === 'object') {
    const out = {}
    for (const [k, v] of Object.entries(node)) {
      if (k === 'prefixItems') {
        out.items = downlevel(v) // 2020-12 タプル -> draft-07 タプル
        continue
      }
      if (k === 'title' && typeof v === 'string') {
        continue // title アノテーションのみ除去（フィールド名 "title" は値がオブジェクトなので残る）
      }
      out[k] = downlevel(v)
    }
    return out
  }
  return node
}

async function buildOne(target) {
  const raw = JSON.parse(readFileSync(resolve(schemaDir, target.schema), 'utf-8'))
  const schema = downlevel(raw)
  const body = await compile(schema, target.name, {
    bannerComment: '',
    additionalProperties: false,
    declareExternallyReferenced: true,
  })
  return `${BANNER}\n/* eslint-disable */\n\n${body}`
}

const check = process.argv.includes('--check')
let changed = []
for (const target of TARGETS) {
  const next = await buildOne(target)
  const path = resolve(srcDir, target.out)
  const prev = existsSync(path) ? readFileSync(path, 'utf-8') : null
  if (prev === next) continue
  changed.push(target.out)
  if (!check) writeFileSync(path, next, 'utf-8')
}

if (check) {
  if (changed.length) {
    console.error('TS 型が古い:', changed.join(', '), '— `pnpm gen` で再生成してください。')
    process.exit(1)
  }
  console.log('TS 型は最新です。')
} else {
  console.log(changed.length ? `wrote ${changed.join(', ')}` : '変更なし（最新）。')
}
