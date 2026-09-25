/**
 * このファイルは schema/*.json から自動生成される。手で編集しないこと。
 * 生成元は pydantic モデル(videoscore.model)。再生成: pnpm gen
 */
/* eslint-disable */

/** 現行の VideoScore 形式のバージョン（python の videoscore.model.SCHEMA_VERSION と同じ）。 */
export const SCHEMA_VERSION = "0.2.0";

/**
 * VideoScore ドキュメントのルート（§1, §8）。
 */
export interface VideoScore {
  meta?: Meta | null;
  video?: VideoElement[] | null;
  audio?: AudioElement[] | null;
  telop?: TelopElement[] | null;
  overlay?: OverlayElement[] | null;
  scenes: Scene[];
}
/**
 * ドキュメントのメタ情報（§8）。
 */
export interface Meta {
  title?: string | null;
  fps?: number | null;
  size?: [number, number] | null;
  styleCatalog?: string | null;
  /**
   * この文書が準拠する VideoScore 形式のバージョン（例 "0.2.0"）。部品間（生成・解決・書き出し・プレイヤー）の互換確認に使う。省略可。
   */
  schemaVersion?: string | null;
}
/**
 * 映像クリップ（§2）。
 */
export interface VideoElement {
  id?: string | null;
  t:
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject, Gap]
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject];
  style?: string | null;
  params?: {
    [k: string]: unknown;
  } | null;
  marks?: string[] | null;
  /**
   * 自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。時間アンカーには marks を使い、ここには置かない。
   */
  annotations?: {
    [k: string]: unknown;
  } | null;
  source: string;
  in?: number | null;
  out?: number | null;
  /**
   * 元フレームのうち映す領域 [x, y, w, h]（左上原点・0〜1 の比率、静的）。x+w<=1, y+h<=1。領域をフレームへどう収めるかは style（layout 系）が決める。
   */
  crop?: [number, number, number, number] | null;
}
/**
 * 他要素のマーク参照、またはレーン参照（§3）。
 *
 * 例: `{ "ref": "v1.end", "offset": 0.2 }` / `{ "ref": "audio.end" }`
 * 参照先 id は同一シーン内に限る（可視範囲ルール）が、その検証は解決側で行う。
 */
export interface RefObject {
  ref: string;
  offset?: number | null;
}
/**
 * `t` の第3要素として置くギャップ指定（§3「`["after", "auto", { "gap": 0.3 }]`」）。
 */
export interface Gap {
  gap: number;
}
/**
 * 音声（§2, §6）。role で voice/se/music/ambient を区別する。
 */
export interface AudioElement {
  id?: string | null;
  t:
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject, Gap]
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject];
  style?: string | null;
  params?: {
    [k: string]: unknown;
  } | null;
  marks?: string[] | null;
  /**
   * 自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。時間アンカーには marks を使い、ここには置かない。
   */
  annotations?: {
    [k: string]: unknown;
  } | null;
  source: string;
  in?: number | null;
  out?: number | null;
  role: "voice" | "se" | "music" | "ambient";
}
/**
 * テロップ（§2）。表示文字 text を持ち、source/in/out は持たない。
 */
export interface TelopElement {
  id?: string | null;
  t:
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject, Gap]
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject];
  style?: string | null;
  params?: {
    [k: string]: unknown;
  } | null;
  marks?: string[] | null;
  /**
   * 自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。時間アンカーには marks を使い、ここには置かない。
   */
  annotations?: {
    [k: string]: unknown;
  } | null;
  text: string;
}
/**
 * 画像/動画オーバーレイ（PiP）（§2）。
 */
export interface OverlayElement {
  id?: string | null;
  t:
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject, Gap]
    | [number | "after" | RefObject, number | ("auto" | "after") | RefObject];
  style?: string | null;
  params?: {
    [k: string]: unknown;
  } | null;
  marks?: string[] | null;
  /**
   * 自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。時間アンカーには marks を使い、ここには置かない。
   */
  annotations?: {
    [k: string]: unknown;
  } | null;
  source: string;
  in?: number | null;
  out?: number | null;
  /**
   * 元フレームのうち映す領域 [x, y, w, h]（左上原点・0〜1 の比率、静的）。x+w<=1, y+h<=1。領域をフレームへどう収めるかは style（layout 系）が決める。
   */
  crop?: [number, number, number, number] | null;
}
/**
 * 1シーン＝1つのローカル時計（§1）。4レーンを持つ唯一の器。
 */
export interface Scene {
  id: string;
  duration: number | RefObject;
  video?: VideoElement[];
  audio?: AudioElement[];
  telop?: TelopElement[];
  overlay?: OverlayElement[];
  /**
   * 自由な注記（根拠の参照・候補 ID・メモ等）。resolve と export は解釈せず素通しで保持する。
   */
  annotations?: {
    [k: string]: unknown;
  } | null;
}
