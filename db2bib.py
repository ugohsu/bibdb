#!/usr/bin/env python3
import sqlite3
import argparse
import sys
import os

DB_PATH = os.path.expanduser("~/refs.db")

def get_bib_entry(cur, cite_key):
    # エントリIDとタイプの取得
    cur.execute("SELECT id, entry_type FROM entries WHERE cite_key = ?", (cite_key,))
    row = cur.fetchone()
    if not row:
        sys.stderr.write(f"Warning: {cite_key} not found.\n")
        return None
    
    entry_id, entry_type = row
    
    # フィールドの取得
    cur.execute("SELECT field_key, field_value FROM fields WHERE entry_id = ?", (entry_id,))
    fields = cur.fetchall()
    
    # BibTeX形式への整形
    lines = [f"@{entry_type}{{{cite_key},"]
    for k, v in fields:
        # yomi など BibTeX 標準でないフィールドを出力に含めるかどうかはここで制御可能
        # 今回は全て出力します（Pandocなどは未知のフィールドを無視するため無害）
        lines.append(f"  {k} = {{{v}}},")
    lines.append("}\n")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Export BibTeX from SQLite master DB")
    parser.add_argument("--keys", "-k", help="File containing list of cite keys (one per line)")
    parser.add_argument("--all", "-a", action="store_true", help="Export all entries")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    target_keys = []

    if args.all:
        cur.execute("SELECT cite_key FROM entries")
        target_keys = [row[0] for row in cur.fetchall()]
    elif args.keys:
        # ファイルからキーリストを読み込む
        with open(args.keys, 'r', encoding='utf-8') as f:
            target_keys = [line.strip() for line in f if line.strip()]
    else:
        # 引数がなければ標準入力から読み込む（パイプ対応）
        if not sys.stdin.isatty():
            target_keys = [line.strip() for line in sys.stdin if line.strip()]

    # 出力
    for key in target_keys:
        bib_str = get_bib_entry(cur, key)
        if bib_str:
            print(bib_str)

    conn.close()

if __name__ == "__main__":
    main()
