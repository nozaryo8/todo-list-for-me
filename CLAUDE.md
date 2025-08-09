# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

このプロジェクトは、FastAPIとPostgreSQLを使用したTodoリストアプリケーションです。Dockerを使用してコンテナ化されており、Alembicを使ってデータベースマイグレーションを管理しています。

## よく使用するコマンド

### Docker環境
- `docker compose up -d` - コンテナを起動
- `docker compose ps` - コンテナの状態確認
- `docker compose exec fastapi sh` - FastAPIコンテナに入る

### データベースマイグレーション
コンテナ内で実行：
- `alembic revision -m "説明"` - 新しいマイグレーションファイルを作成
- `alembic revision --autogenerate -m "説明"` - models.pyから自動でマイグレーションファイルを生成
- `alembic upgrade head` - マイグレーションを実行

### アプリケーション起動
- `uvicorn main:app --reload --host 0.0.0.0 --port 8000` - 開発サーバー起動（Docker外）

## アーキテクチャ

### ディレクトリ構成
```
fastapi/
├── main.py                 # FastAPIアプリケーションのエントリポイント
├── core/
│   └── config.py          # 環境変数設定とコンフィギュレーション
└── migration/
    ├── models.py          # SQLAlchemyモデル定義
    ├── env.py            # Alembic環境設定
    └── versions/         # マイグレーションファイル
```

### 主要コンポーネント
- **FastAPI**: WebAPIフレームワーク
- **SQLAlchemy**: ORM（バージョン1.3.22）
- **Alembic**: データベースマイグレーションツール
- **PostgreSQL**: データベース（Docker内）
- **Pydantic**: データバリデーションとシリアライゼーション

### データベース接続
- 環境変数 `database_url` でPostgreSQLに接続
- `.env` ファイルから設定を読み込み（`core/config.py`）

### モデル定義
現在定義されているモデル：
- `User`: ユーザーテーブル（id, name, login_id, password, created_at, updated_at）

## 開発環境設定

1. `.env` ファイルに `database_url` を設定
2. Docker Composeでサービスを起動
3. コンテナ内でAlembicマイグレーションを実行

## 注意事項

- Alembicの設定では日本時間（Asia/Tokyo）を使用
- マイグレーションファイル名は `YYYYMMDDHHMM_description` 形式
- SQLAlchemy 1.3.22を使用（古いバージョン）