/**
 * このファイルは python/src/videoscore/catalogs/standard/style-catalog.json から自動生成される。手で編集しないこと。
 * 生成元は 標準カタログ JSON（Python パッケージ同梱）。再生成: pnpm gen
 */
/* eslint-disable */

import type { StyleCatalog } from './style-catalog.gen.js';

/** 標準スタイルカタログの印 id。 */
export type StandardStyleId =
  | "telop.default"
  | "telop.caption"
  | "telop.title"
  | "tone.emphasis"
  | "layout.vertical-fit"
  | "layout.vertical-crop"
  | "audio.default"
  | "position.corner";

/** 標準スタイルカタログの印 id 一覧（カタログ記載順）。 */
export const STANDARD_STYLE_IDS: readonly StandardStyleId[] = ["telop.default","telop.caption","telop.title","tone.emphasis","layout.vertical-fit","layout.vertical-crop","audio.default","position.corner"];

/** 標準スタイルカタログ（意味の層）。Python の videoscore.catalogs.standard_catalog() と同じ内容。 */
export const STANDARD_STYLE_CATALOG: StyleCatalog & { styles: Record<StandardStyleId, StyleCatalog['styles'][string]> } =
  {
    "styles": {
      "telop.default": {
        "intent": "通常のテロップ。特別な強調も役割もないとき。",
        "feeling": "標準・中立",
        "appliesTo": [
          "telop"
        ],
        "params": null,
        "example": "ふつうの説明字幕"
      },
      "telop.caption": {
        "intent": "話している内容を文字でも追えるようにしたいとき（発話の字幕）。音を出せない環境でも内容が伝わるようにする。発話を短い塊に区切って順に出す。",
        "feeling": "読みやすい・話し言葉に寄り添う・映像の邪魔をしない",
        "appliesTo": [
          "telop"
        ],
        "params": null,
        "example": "話者の発言を、一息ぶんずつ区切って出す字幕"
      },
      "telop.title": {
        "intent": "動画の冒頭などで、これが何の動画かを一言で示したいとき。視聴者をつかむ看板の一行。",
        "feeling": "導入・看板・つかみ",
        "appliesTo": [
          "telop"
        ],
        "params": null,
        "example": "冒頭に出す動画のタイトル"
      },
      "tone.emphasis": {
        "intent": "視聴者に一番伝えたい一言。目を引かせたいとき。",
        "feeling": "強い・はっきり・前に出る",
        "appliesTo": [
          "telop"
        ],
        "params": null,
        "example": "決め台詞"
      },
      "layout.vertical-fit": {
        "intent": "横長の素材を、切り落とさずに全体が見えるまま縦長の画面に収めたいとき。余った上下の空きは、タイトルや字幕の置き場になる。",
        "feeling": "全体が見える・落ち着いた・情報を足す余地がある",
        "appliesTo": [
          "video",
          "overlay"
        ],
        "params": null,
        "example": "横長の画面収録を縦型ショートで見せる（上にタイトル、下に字幕）"
      },
      "layout.vertical-crop": {
        "intent": "素材のうち注目したい部分だけを縦長の画面いっぱいに見せたいとき。見せる部分は要素の crop で指定する（未指定なら中央）。",
        "feeling": "近い・没入・主役に集中",
        "appliesTo": [
          "video",
          "overlay"
        ],
        "params": null,
        "example": "横長の対談映像から、話している人だけを縦型で大きく見せる"
      },
      "audio.default": {
        "intent": "通常の音声。加工なし。",
        "feeling": "素の音",
        "appliesTo": [
          "audio"
        ],
        "params": null,
        "example": "そのままのナレーション"
      },
      "position.corner": {
        "intent": "ロゴや補助情報を隅に小さく置きたいとき。",
        "feeling": "控えめ・常駐",
        "appliesTo": [
          "overlay"
        ],
        "params": null,
        "example": "右上のチャンネルロゴ"
      }
    }
  };
