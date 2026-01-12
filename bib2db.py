#!/usr/bin/env python3
import sqlite3
import argparse
import bibtexparser
import sys
import os

DB_PATH = os.path.expanduser("~/refs.db")  # DBの保存場所

def init_db(conn):
    """テーブルが存在しなければ作成する"""
    cur = conn.cursor()
    # 文献の基本エントリ
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cite_key TEXT UNIQUE NOT NULL,
        entry_type TEXT NOT NULL,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # 各フィールド (author, title, yomi, year 等すべてここ)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fields (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_id INTEGER,
        field_key TEXT NOT NULL,
        field_value TEXT,
        FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE,
        UNIQUE(entry_id, field_key)
    )
    """)
    conn.commit()

def upsert_entry(conn, entry):
    """1件の文献データをDBに登録または更新する"""
    cur = conn.cursor()
    cite_key = entry.get('ID')
    entry_type = entry.get('ENTRYTYPE')
    
    if not cite_key or not entry_type:
        return

    # 1. entries テーブルへの登録 (あればID取得、なければ新規作成)
    cur.execute("SELECT id FROM entries WHERE cite_key = ?", (cite_key,))
    row = cur.fetchone()
    
    if row:
        entry_id = row[0]
        # タイプが変更されている場合は更新
        cur.execute("UPDATE entries SET entry_type = ? WHERE id = ?", (entry_type, entry_id))
    else:
        cur.execute("INSERT INTO entries (cite_key, entry_type) VALUES (?, ?)", (cite_key, entry_type))
        entry_id = cur.lastrowid

    # 2. fields テーブルの更新
    # 既存のフィールドを一旦削除して入れ直す（シンプルな更新戦略）
    # ※ 特定のフィールドを残したい場合はロジックを調整してください
    cur.execute("DELETE FROM fields WHERE entry_id = ?", (entry_id,))
    
    for key, value in entry.items():
        if key in ['ID', 'ENTRYTYPE']:
            continue
        # bibtexparserは改行を含む場合があるので整形しても良い
        clean_value = value.strip()
        cur.execute("INSERT INTO fields (entry_id, field_key, field_value) VALUES (?, ?, ?)",
                    (entry_id, key.lower(), clean_value))
    
    conn.commit()
    print(f"Upserted: {cite_key}")

def main():
    parser = argparse.ArgumentParser(description="Import .bib file into SQLite master DB")
    parser.add_argument("bibfile", help="Input .bib file path")
    args = parser.parse_args()

    # DB接続
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # Bibファイル読み込み
    with open(args.bibfile, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    # データ登録
    for entry in bib_database.entries:
        upsert_entry(conn, entry)

    conn.close()

if __name__ == "__main__":
    main()
