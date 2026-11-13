# Phase 02: Router・Schemaに分割したTask API

Phase 01と同じTask APIを題材に、`main.py` をアプリケーションの初期化だけにして、`api/routes/` と `schemas/` を切り出したスナップショットです。

- `app/main.py`: アプリ生成とRouter登録
- `app/api/routes/`: HTTPエンドポイント
- `app/api/dependencies.py`: メモリ上のストアを注入する依存関係
- `app/schemas/task.py`: Pydanticスキーマ
- `tests/unit/`: スキーマ単体テスト
- `tests/api/`: HTTP契約テスト（依存関係の差し替えを含む）

```bash
cd phase-02-router
uv sync --locked
uv run fastapi dev
# 別ターミナルで
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

データはメモリ上にのみ保存します。永続化はPhase 03で扱います。
