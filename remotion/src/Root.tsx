// サンプルの Root: 解決済み VideoScore を props で受け取るコンポジションを登録する。
// 既定 props は合成素材のサンプル（samples/*.resolved.json）。`--props=resolved.json` で差し替える。
import React from 'react'
import { Composition } from 'remotion'
import wide from '../samples/wide.resolved.json'
import vertical from '../samples/vertical.resolved.json'
import {
  calculateMetadata,
  VideoScoreComposition,
  type VideoScore,
  type VideoScoreInputProps,
} from './lib'

// JSON import は配列をタプル型に推論しないので、型は VideoScore として扱う（中身は解決済みサンプル）。
const wideScore = wide as unknown as VideoScore
const verticalScore = vertical as unknown as VideoScore

// fps / サイズ / 尺は calculateMetadata が VideoScore の meta と scenes から決める（ここの値は仮）。
const placeholder = { fps: 30, width: 1920, height: 1080, durationInFrames: 1 }

export const Root: React.FC = () => (
  <>
    <Composition
      id="VideoScore"
      component={VideoScoreComposition}
      calculateMetadata={calculateMetadata}
      defaultProps={{ score: wideScore } satisfies VideoScoreInputProps}
      {...placeholder}
    />
    <Composition
      id="VideoScoreVertical"
      component={VideoScoreComposition}
      calculateMetadata={calculateMetadata}
      defaultProps={{ score: verticalScore } satisfies VideoScoreInputProps}
      {...placeholder}
    />
  </>
)
