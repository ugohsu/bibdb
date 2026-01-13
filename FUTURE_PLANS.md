# 将来の拡張計画: ユーザーデータ管理の分離

## 1. 概要

現在の `fields` テーブルは BibTeX インポートによる「書誌情報（タイトル、著者など）」と、ユーザーが独自に追加する「付加情報（要約、ファイルパスなど）」が混在する可能性がある。
これを解決するため、ユーザー独自のデータを管理する専用テーブル `extras` を新設し、BibTeX 由来のデータとは明確にライフサイクルを分離する。

## 2. データベース定義の変更

### 2.1 新規テーブル: `extras`

BibTeX ファイルには含まれない、ユーザー固有の情報を格納する。

* **特徴**:
* `import` コマンドの影響を受けない（上書き・削除されない）。
* 同一 `entry_id` に対して、同じ `extra_key` を複数持てる（`UNIQUE` 制約なし）。
* 例: 複数の関連ファイルパス、追記型のメモなど。



```sql
CREATE TABLE IF NOT EXISTS extras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER,
    extra_key TEXT NOT NULL,  -- 例: 'summary', 'file_path', 'memo'
    extra_value TEXT,         -- 例: 要約本文, '/home/user/docs/ref.pdf'
    FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
    -- 注意: (entry_id, extra_key) のユニーク制約は設けない
);

```

### 2.2 運用方針

* 当面の間、専用の登録コマンドは実装しない。
* データの登録・編集は、SQLite クライアント等を用いた直接の SQL 実行、または外部スクリプトによる操作を想定する。

## 3. 機能改修の方針

### 3.1 重複整理 (`dedup`) の改修

Delete 側の `extras` レコードを Keep 側に移動する際、**「情報の最大保存（Lossless）」**を原則とする。

* **完全一致（Key と Value が共に同じ）の場合**:
* 重複とみなし、Delete 側のレコードは破棄する（統合）。


* **不一致（Key は同じだが Value が違う、または Key 自体がない）の場合**:
* 別の情報とみなし、Delete 側のレコードをそのまま Keep 側に移動する（追記）。
* 結果として、Keep 側には同名の Key が複数存在することになる。これは意図通りである (下の例のように、要約資料が複数になることは自然な減少である)。


#### マージ挙動の例

**統合前:**

* **Entry A (Keep)**
* `file`: `report_v1.pdf`
* `memo`: `重要`


* **Entry B (Delete)**
* `file`: `report_v1.pdf`  (Aと完全一致)
* `file`: `slide_draft.pptx` (Aにない値)
* `memo`: `要確認`         (Aと値が違う)



**統合後 (Entry A):**

* `file`: `report_v1.pdf`      (Bから来た重複は消滅)
* `file`: `slide_draft.pptx`   (Bから移動・追記)
* `memo`: `重要`               (元々あったもの)
* `memo`: `要確認`             (Bから移動・追記)

### 3.2 削除 (`delete`) の挙動

* 既存の `delete` コマンド（および SQL による `DELETE FROM entries ...`）を実行した際、対象文献に紐づく `extras` のデータも**自動的に全削除**される。
* これは `extras` テーブル定義の `ON DELETE CASCADE` 制約により、DB エンジン側で保証されるため、アプリ側の改修は不要である。
