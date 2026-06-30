/**
 * このファイルは schema/*.json から自動生成される。手で編集しないこと。
 * 生成元は pydantic モデル(videoscore.model)。再生成: pnpm gen
 */
/* eslint-disable */

/**
 * `style-catalog.json` ルート（§5）。印 id → StyleEntry。
 */
export interface StyleCatalog {
  styles: {
    [k: string]: StyleEntry;
  };
}
/**
 * カタログ1エントリ（意味の層）。`intent`/`feeling` は「いつ・どんな気分で使うか」。
 */
export interface StyleEntry {
  intent: string;
  feeling: string;
  appliesTo: ("video" | "audio" | "telop" | "overlay")[];
  params?: {
    [k: string]: unknown;
  } | null;
  example?: string | null;
}
