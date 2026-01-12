#!/usr/bin/env python3
import sqlite3
import argparse
import bibtexparser
import sys
import os
import difflib

DB_PATH = os.path.expanduser("~/refs.db")

def init_db(conn):
    """テーブル初期化（変更なし）"""
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cite_key TEXT UNIQUE NOT NULL,
        entry_type TEXT NOT NULL,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
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

def get_db_entry_dict(cur, cite_key):
    """DBから既存データを取得して辞書形式で返す"""
    cur.execute("SELECT id, entry_type FROM entries WHERE cite_key = ?", (cite_key,))
    row = cur.fetchone()
    if not row:
        return None, None
    
    entry_id, entry_type = row
    cur.execute("SELECT field_key, field_value FROM fields WHERE entry_id = ?", (entry_id,))
    
    # 比較しやすいように辞書化
    data = {row[0]: row[1] for row in cur.fetchall()}
    data['ENTRYTYPE'] = entry_type # ENTRYTYPEも含めて比較対象にする
    return entry_id, data

def show_diff(cite_key, db_data, new_data):
    """差分をGitライクに表示する"""
    print(f"\n--- Conflict detected: {cite_key} ---")
    
    # キーの和集合をとる
    all_keys = sorted(set(db_data.keys()) | set(new_data.keys()))
    
    for key in all_keys:
        # IDキーは比較しない
        if key in ['ID']:
            continue
            
        val_db = db_data.get(key)
        val_new = new_data.get(key)
        
        # bibtexparserの仕様でENTRYTYPE以外は小文字化されている場合があるので調整
        # ここでは厳密比較を行う
        
        if val_db != val_new:
            print(f"Key: {key}")
            if val_db is not None:
                print(f"  - DB : {val_db}")
            else:
                print(f"  - DB : (Not exists)")
                
            if val_new is not None:
                print(f"  + New: {val_new}")
            else:
                print(f"  + New: (Deleted)")

def upsert_entry(conn, entry, force=False):
    """
    1件の文献データを処理する。
    差分がある場合はユーザーに確認する。
    """
    cur = conn.cursor()
    cite_key = entry.get('ID')
    new_type = entry.get('ENTRYTYPE')
    
    if not cite_key or not new_type:
        return

    # 入力データの整形（DBと比較できるようにする）
    new_data = {'ENTRYTYPE': new_type}
    for k, v in entry.items():
        if k == 'ID': continue
        new_data[k.lower()] = v.strip() # DBは小文字・strip済みで格納前提

    # 1. DBから既存データを取得
    entry_id, db_data = get_db_entry_dict(cur, cite_key)

    # 2. 新規登録の場合
    if not entry_id:
        print(f"[NEW] Adding {cite_key}...")
        cur.execute("INSERT INTO entries (cite_key, entry_type) VALUES (?, ?)", (cite_key, new_type))
        entry_id = cur.lastrowid
        for k, v in new_data.items():
            if k == 'ENTRYTYPE': continue
            cur.execute("INSERT INTO fields (entry_id, field_key, field_value) VALUES (?, ?, ?)",
                        (entry_id, k, v))
        conn.commit()
        return

    # 3. 既存データがある場合の比較
    # 辞書同士が等しければ何もしない（ID増加問題も解決）
    if db_data == new_data:
        # print(f"[SKIP] No changes for {cite_key}")
        return

    # 4. コンフリクト発生（差分あり）
    if force:
        choice = 'o' # 強制上書き
    else:
        show_diff(cite_key, db_data, new_data)
        while True:
            choice = input("Action? [o]verwrite / [s]kip : ").lower()
            if choice in ['o', 's']:
                break

    # 5. ユーザー選択に基づく処理
    if choice == 's':
        print(f"-> Skipped {cite_key}")
        return
    elif choice == 'o':
        print(f"-> Overwriting {cite_key}...")
        # エントリタイプ更新
        cur.execute("UPDATE entries SET entry_type = ? WHERE id = ?", (new_type, entry_id))
        # フィールド洗い替え
        cur.execute("DELETE FROM fields WHERE entry_id = ?", (entry_id,))
        for k, v in new_data.items():
            if k == 'ENTRYTYPE': continue
            cur.execute("INSERT INTO fields (entry_id, field_key, field_value) VALUES (?, ?, ?)",
                        (entry_id, k, v))
        conn.commit()

def main():
    parser = argparse.ArgumentParser(description="Import .bib file into SQLite with conflict check")
    parser.add_argument("bibfile", help="Input .bib file path")
    parser.add_argument("--force", "-f", action="store_true", help="Force overwrite all conflicts")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    with open(args.bibfile, 'r', encoding='utf-8') as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    total = len(bib_database.entries)
    print(f"Processing {total} entries from {args.bibfile}...")

    for entry in bib_database.entries:
        upsert_entry(conn, entry, force=args.force)

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
