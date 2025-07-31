# 環境構築

## コンテナ起動
docker compose up -d

## コンテナが立ち上がっているか確認
docker compose ps

## アプリコンテナに入る
docker compose exec fastapi sh

### alembic initでmigration環境の作成
alembic init migration

### migrationファイルを作成
alembic revision -m "create users table"

### migrationファイルの生成
### --autogenerateオプションをつけることで、models.pyを元にすでにあるmigrationファイルとの差分のmigrationファイルを作成してくれる。
alembic revision --autogenerate -m "add columns"

### migrationの実行
alembic upgrade head
