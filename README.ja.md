# A5:DB Document for AI agent

データベースのスキーマ定義（DDL）を Markdown ファイルとして出力する CLI ツールです。
生成したファイルを Claude Code などの AI エージェントに渡すことで、正確な SQL を書いてもらいやすくなります。

SQLAlchemy が対応するすべてのデータベース（PostgreSQL, MySQL, SQLite, SQL Server, Oracle, Db2 など）に対応しています。

[English](README.md)

## インストール

```bash
pip install -e .
```

データベースドライバは別途インストールしてください。

```bash
pip install -e ".[db2]"     # Db2 (ibm-db-sa)
pip install -e ".[pg]"      # PostgreSQL (psycopg2)
pip install -e ".[mysql]"   # MySQL (PyMySQL)
pip install -e ".[mssql]"   # SQL Server (pyodbc)
pip install -e ".[oracle]"  # Oracle (cx_Oracle)
```

## 使い方

### スキーマを Markdown にエクスポート

```bash
a5dbdoc export <接続URL>
```

`export` を実行すると、カレントディレクトリに `DB_LAYOUT.md` が生成されます。出力ファイルはこれだけです。

```bash
# SQLite
a5dbdoc export sqlite:///./myapp.db

# PostgreSQL
a5dbdoc export postgresql://user:pass@localhost/mydb

# MySQL
a5dbdoc export mysql+pymysql://user:pass@localhost/mydb

# SQL Server
a5dbdoc export "mssql+pyodbc://user:pass@server/mydb?driver=ODBC+Driver+17+for+SQL+Server"

# Db2
a5dbdoc export "db2+ibm_db://user:pass@host:50000/database"

# スキーマを指定（PostgreSQL など）
a5dbdoc export postgresql://user:pass@localhost/mydb --schema public

# テーブル名で絞り込み（glob パターン）
a5dbdoc export postgresql://user:pass@localhost/mydb --table "order*" --table "customer*"
```

**オプション一覧:**

| オプション | 短縮 | 説明 |
|-----------|------|------|
| `--schema` | `-s` | 対象スキーマ名。複数指定可。省略時は全スキーマ。 |
| `--table` | `-t` | テーブル名の glob パターン。複数指定可。省略時は全テーブル。 |

### エージェント設定ファイルの更新

`CLAUDE.md` または `AGENTS.md` に `DB_LAYOUT.md` への参照を追加します（ファイルがない場合は作成）。

```bash
a5dbdoc update-claude-md          # → ./CLAUDE.md
a5dbdoc update-agents-md          # → ./AGENTS.md

# パスを指定する場合
a5dbdoc update-claude-md --path ./docs/CLAUDE.md
```

どちらのコマンドも冪等です。すでに `DB_LAYOUT.md` への言及がある場合は何も変更しません。

### スキーマ一覧を確認

```bash
a5dbdoc list-schemas postgresql://user:pass@localhost/mydb
```

### テーブル一覧を確認

```bash
a5dbdoc list-tables postgresql://user:pass@localhost/mydb --schema public
```

## 出力形式

カレントディレクトリに `DB_LAYOUT.md` が生成されます。全テーブルの DDL が1つの SQL コードブロックにまとめられます。

````markdown
# DB Layout

- **Database:** PostgreSQL 15.3
- **Exported:** 2026-04-04

```sql
CREATE TABLE public.customers (
  id INTEGER NOT NULL,
  name VARCHAR(120) NOT NULL,
  email VARCHAR(255) NOT NULL,
  CONSTRAINT pk_customers PRIMARY KEY (id),
  CONSTRAINT uq_customers_email UNIQUE (email)
);

CREATE TABLE public.orders (
  id INTEGER NOT NULL,
  customer_id INTEGER NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  total_amount NUMERIC(12, 2) NOT NULL,
  notes TEXT, -- 備考
  CONSTRAINT pk_orders PRIMARY KEY (id),
  CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
    REFERENCES public.customers (id)
);

CREATE INDEX ix_orders_customer_id ON public.orders (customer_id);
```
````

## AI エージェントとの連携

プロジェクトルートで以下の2コマンドを実行します。

```bash
a5dbdoc export <接続URL>          # DB_LAYOUT.md を生成
a5dbdoc update-claude-md          # CLAUDE.md に DB_LAYOUT.md への参照を追加
# または
a5dbdoc update-agents-md          # OpenAI Codex など AGENTS.md を使うエージェント向け
```

`update-claude-md` は `CLAUDE.md` に以下のセクションを追加します（既にある場合は変更なし）。

```markdown
## Database
Database schema is documented in DB_LAYOUT.md.
Read it when working on SQL, migrations, or ORM models.
```

## 開発・テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## 接続 URL について

パスワードに `@` や `#` などの特殊文字が含まれる場合は URL エンコードしてください。

```
# @ → %40
postgresql://user:p%40ssword@localhost/mydb
```

SQLAlchemy の接続 URL 形式の詳細は [SQLAlchemy ドキュメント](https://docs.sqlalchemy.org/en/20/core/engines.html) を参照してください。
