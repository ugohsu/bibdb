#!/usr/bin/env python3
import sqlite3
import argparse
import os
import re
from difflib import SequenceMatcher

DB_PATH = os.path.expanduser("~/refs.db")

def normalize_text(text):
    """比較用にテキストを正規化（小文字化、記号削除）"""
    if not text:
        return ""
    return re.sub(r'[\W_]+', '', text.lower())

def get_similarity(a, b):
    """文字列の類似度を返す (0.0 ~ 1.0)"""
    return SequenceMatcher(None, a, b).ratio()

def get_entry_full_data(conn, eid):
    """エントリの詳細データ（Typeと全フィールド）を取得"""
    cur = conn.cursor()
    cur.execute("SELECT cite_key, entry_type FROM entries WHERE id = ?", (eid,))
    key, etype = cur.fetchone()
    
    cur.execute("SELECT field_key, field_value FROM fields WHERE entry_id = ?", (eid,))
    fields = {k: v for k, v in cur.fetchall()}
    fields['ENTRYTYPE'] = etype # 比較用に混ぜる
    return {'id': eid, 'key': key, 'fields': fields}

def get_all_entries_light(conn):
    """全エントリの軽量データ（検索用）を取得"""
    cur = conn.cursor()
    cur.execute("SELECT id, cite_key FROM entries")
    entries = []
    for eid, key in cur.fetchall():
        cur.execute("SELECT field_key, field_value FROM fields WHERE entry_id = ? AND field_key IN ('title', 'doi')", (eid,))
        fields = {k: v for k, v in cur.fetchall()}
        entries.append({
            'id': eid,
            'key': key,
            'doi': fields.get('doi', ''),
            'norm_title': normalize_text(fields.get('title', ''))
        })
    return entries

def merge_entries(conn, keep_id, delete_id):
    """delete_id のフィールドを keep_id にマージ（不足分のみコピー）して削除"""
    cur = conn.cursor()
    
    # 削除される側のフィールドを取得
    cur.execute("SELECT field_key, field_value FROM fields WHERE entry_id = ?", (delete_id,))
    del_fields = cur.fetchall()
    
    # 残す側のフィールドを取得
    cur.execute("SELECT field_key FROM fields WHERE entry_id = ?", (keep_id,))
    keep_keys = set(row[0] for row in cur.fetchall())
    
    # マージ
    for k, v in del_fields:
        if k not in keep_keys:
            cur.execute("INSERT INTO fields (entry_id, field_key, field_value) VALUES (?, ?, ?)",
                        (keep_id, k, v))
    
    # 削除実行
    cur.execute("DELETE FROM entries WHERE id = ?", (delete_id,))
    conn.commit()

def show_detailed_comparison(conn, entry_a_light, entry_b_light, reason):
    """詳細な比較（Diff）を表示"""
    data_a = get_entry_full_data(conn, entry_a_light['id'])
    data_b = get_entry_full_data(conn, entry_b_light['id'])
    
    fields_a = data_a['fields']
    fields_b = data_b['fields']
    
    # 全キーの和集合
    all_keys = sorted(set(fields_a.keys()) | set(fields_b.keys()))
    
    print("\n" + "="*80)
    print(f" DUPLICATE CANDIDATE FOUND ({reason})")
    print("="*80)
    print(f"{'[A] KEEP':<40} | {'[B] KEEP':<40}")
    print(f"{data_a['key']:<40} | {data_b['key']:<40}")
    print(f"(ID: {data_a['id']}){' '*30} | (ID: {data_b['id']})")
    print("-" * 80)

    # 差分表示
    has_diff = False
    for k in all_keys:
        val_a = fields_a.get(k, "")
        val_b = fields_b.get(k, "")
        
        # 値が異なる場合のみ表示（片方だけにある場合も含む）
        if val_a != val_b:
            has_diff = True
            # 長すぎる文字列（abstract等）は省略表示
            disp_a = (val_a[:35] + '...') if len(val_a) > 35 else val_a
            disp_b = (val_b[:35] + '...') if len(val_b) > 35 else val_b
            
            # ない場合は (missing) 表記
            if k not in fields_a: disp_a = "(missing)"
            if k not in fields_b: disp_b = "(missing)"

            print(f"{k.upper()}:")
            print(f"  A: {disp_a}")
            print(f"  B: {disp_b}")
    
    if not has_diff:
        print(" >> No field differences detected (Exact match excluding ID/Key).")
    print("-" * 80)

def process_duplicates(conn, threshold=0.9):
    entries = get_all_entries_light(conn)
    total = len(entries)
    processed = set()
    
    print(f"Scanning {total} entries for duplicates (Threshold: {threshold})...")
    
    for i in range(total):
        if entries[i]['id'] in processed:
            continue
            
        for j in range(i + 1, total):
            if entries[j]['id'] in processed:
                continue
            
            a = entries[i]
            b = entries[j]
            
            is_duplicate = False
            reason = ""

            if a['doi'] and b['doi'] and a['doi'] == b['doi']:
                is_duplicate = True
                reason = "DOI Match"
            
            elif a['norm_title'] and b['norm_title']:
                sim = get_similarity(a['norm_title'], b['norm_title'])
                if sim >= threshold:
                    is_duplicate = True
                    reason = f"Title Sim {sim:.2f}"

            if is_duplicate:
                show_detailed_comparison(conn, a, b, reason)
                
                while True:
                    # アクション選択
                    prompt = "Action? Keep [A] / Keep [B] / [S]kip: "
                    choice = input(prompt).lower()
                    
                    if choice == 'a':
                        print(f"-> Merging B into A...")
                        merge_entries(conn, a['id'], b['id'])
                        processed.add(b['id'])
                        break
                    elif choice == 'b':
                        print(f"-> Merging A into B...")
                        merge_entries(conn, b['id'], a['id'])
                        processed.add(a['id'])
                        break
                    elif choice == 's':
                        print("-> Skipped.")
                        break

def main():
    parser = argparse.ArgumentParser(description="Find and merge duplicate entries in SQLite DB")
    parser.add_argument("--threshold", "-t", type=float, default=0.9, help="Similarity threshold (0.0-1.0)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    try:
        process_duplicates(conn, args.threshold)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
