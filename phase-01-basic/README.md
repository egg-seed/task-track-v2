# Phase 01: 単一ファイルから始めるTask API

初学者向けに、`app/main.py` にFastAPI、Pydanticの入出力モデル、メモリ上のCRUDをまとめた段階です。後のPhase 02で同じAPIをRouter・Schemaへ分割します。データは再起動で消えます。

```bash
cd phase-01-basic
uv sync --locked
uv run fastapi dev
# 別のターミナルで
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

`http://127.0.0.1:8000/docs` から操作できます。永続化・認証・デプロイはまだ扱いません。
