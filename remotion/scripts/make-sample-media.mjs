// サンプル用の合成素材を ffmpeg で public/sample/ に作る（実素材は使わない）。
//   clip.mp4 … 1280x720 / 30fps / 6 秒の testsrc2 映像 + 440Hz の sine 音声
//   logo.png … 256x256 の単色図形（position.corner の確認用）
// 使い方: node scripts/make-sample-media.mjs   （要 ffmpeg。既にあれば作り直さない。--force で再生成）
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const outDir = resolve(here, '../public/sample')
const force = process.argv.includes('--force')
mkdirSync(outDir, { recursive: true })

const jobs = [
  {
    out: resolve(outDir, 'clip.mp4'),
    args: [
      '-f', 'lavfi', '-i', 'testsrc2=size=1280x720:rate=30:duration=6',
      '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=6',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '30', '-pix_fmt', 'yuv420p', '-g', '30',
      '-c:a', 'aac', '-b:a', '64k', '-shortest', '-movflags', '+faststart',
    ],
  },
  {
    out: resolve(outDir, 'logo.png'),
    args: [
      '-f', 'lavfi', '-i', 'color=c=0x2e86de:size=256x256:duration=1',
      '-vf', "drawbox=x=48:y=48:w=160:h=160:color=white@0.9:t=fill,drawbox=x=88:y=88:w=80:h=80:color=0xff9f43:t=fill",
      '-frames:v', '1',
    ],
  },
]

for (const job of jobs) {
  if (existsSync(job.out) && !force) {
    console.log('exists', job.out)
    continue
  }
  execFileSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', ...job.args, job.out], { stdio: 'inherit' })
  console.log('wrote', job.out)
}
