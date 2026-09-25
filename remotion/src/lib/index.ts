// videoscore-remotion — 解決済み VideoScore を Remotion で再生・書き出すプレイヤー。
//
//   <Composition id="VideoScore" component={VideoScoreComposition}
//                calculateMetadata={calculateMetadata} defaultProps={{ score }} />

export {
  VideoScoreComposition,
  UnresolvedError,
  isImageSource,
  scoreFromProps,
  type VideoScoreCompositionProps,
  type VideoScoreInputProps,
} from './VideoScoreComposition'
export {
  calculateMetadata,
  makeCalculateMetadata,
  videoScoreMetadata,
  measureSourceSizes,
  probeMediaSize,
  visualSources,
  type VideoScoreMetadata,
} from './calculateMetadata'
export {
  standardRemotionRecipes,
  TelopDefault,
  TelopCaption,
  TelopTitle,
  TelopEmphasis,
  DEFAULT_VIDEO_LAYOUT,
  DEFAULT_OVERLAY_LAYOUT,
  LANE_DEFAULT_STYLE,
  type RemotionRecipe,
  type RemotionRecipeBook,
  type TelopRecipeProps,
  type VisualLayout,
} from './recipes.remotion'
export { defaultResolveSrc, makeDefaultResolveSrc, type ResolveSrc } from './resolveSrc'
export { placeMedia, fullFrame, FULL_CROP, type Fit, type Placement, type Rect } from './layout'
export { findUnresolved, schemaVersionWarning, PLAYER_SCHEMA_VERSION } from './validate'
export {
  DEFAULT_FPS,
  DEFAULT_SIZE,
  secToFrame,
  spanToFrames,
  sceneOffsets,
  totalSeconds,
} from './time'
export type * from './types'
