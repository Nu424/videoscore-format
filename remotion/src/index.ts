// サンプルの Remotion エントリ（`npx remotion studio|compositions|still src/index.ts`）。
// 本番プロジェクトでは自分のエントリから VideoScoreComposition を登録する（README 参照）。
import { registerRoot } from 'remotion'
import { Root } from './Root'

registerRoot(Root)
