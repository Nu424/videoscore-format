"""pydantic モデルから JSON Schema を書き出す（フェーズ2）。

pydantic v2 を Single Source of Truth とし、ここで生成する JSON Schema が
TypeScript 型生成（json2ts）など下流の生成元になる。生成物は schema/ に
コミットし、git 経由インストール時にビルド不要にする。

CLI:
    videoscore-gen-schema [--out-dir schema] [--check]

`--check` は書き込まずにドリフト（モデルと生成物のズレ）を検知する（CI 用）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .model import SCHEMA_VERSION, StyleCatalog, VideoScore

# json2ts や各種バリデータが解釈できるよう、ドラフトを明示する。
# pydantic v2 は 2020-12 準拠の JSON Schema を出力する（タプルは prefixItems）。
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

# 出力ファイル名 -> モデル
_MODELS = {
    "videoscore.schema.json": VideoScore,
    "style-catalog.schema.json": StyleCatalog,
}


# 形式バージョンを載せるスキーマ（下流の TS 生成が SCHEMA_VERSION 定数として取り出す）。
_VERSIONED = {"videoscore.schema.json"}


def _schema_for(model: type, *, versioned: bool = False) -> dict:
    schema = model.model_json_schema()
    # $schema を先頭に付与（pydantic は既定で付けない）。
    head: dict = {"$schema": JSON_SCHEMA_DIALECT}
    if versioned:
        # 形式バージョン（videoscore.model.SCHEMA_VERSION）。検証には効かない注記キー。
        head["x-videoscore-version"] = SCHEMA_VERSION
    return {**head, **schema}


def build_schemas() -> dict[str, dict]:
    """ファイル名 -> JSON Schema(dict) を返す。書き込みはしない。"""
    return {
        name: _schema_for(model, versioned=name in _VERSIONED) for name, model in _MODELS.items()
    }


def render(schema: dict) -> str:
    """ファイルに書く正規形（決定的: indent=2, 非ASCII保持, 末尾改行）。"""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="videoscore-gen-schema",
        description="VideoScore の pydantic モデルから JSON Schema を生成する。",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("schema"),
        help="出力先ディレクトリ（既定: ./schema）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="書き込まず、生成物がモデルと一致するか検査する（ズレていたら非0終了）",
    )
    args = parser.parse_args(argv)

    changed: list[str] = []
    for name, schema in build_schemas().items():
        path = args.out_dir / name
        new = render(schema)
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old == new:
            continue
        changed.append(name)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new, encoding="utf-8")

    if args.check:
        if changed:
            print("JSON Schema が古い:", ", ".join(changed), file=sys.stderr)
            print("`videoscore-gen-schema` で再生成してください。", file=sys.stderr)
            return 1
        print("JSON Schema は最新です。")
        return 0

    for name in changed:
        print("wrote", args.out_dir / name)
    if not changed:
        print("変更なし（最新）。")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
