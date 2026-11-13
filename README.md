# task-track-v2

Zenn の技術書「実務で役立つAPI設計と実装 第2版」のサンプルコードです。

読者が章の途中から再現できるよう、学習の区切りごとに**独立した動作サンプル**を管理します。

| サンプル | ディレクトリ | 内容 |
|---|---|---|
| Phase 01 | [phase-01-basic](phase-01-basic/) | 単一`main.py`でタスク管理APIのCRUDの基本を学ぶ |
| Phase 02 | [phase-02-router](phase-02-router/) | 同じTask APIをRouter・Schema・依存性注入に分離 |
| Phase 03 | [phase-03-sqlmodel](phase-03-sqlmodel/) | SQLModel・Session・Repositoryを導入 |
| Phase 04 | [phase-04-alembic](phase-04-alembic/) | Alembicによるスキーマ変更 |
| 発展編 | [cognito-auth](cognito-auth/) | Amazon Cognitoのアクセストークン検証と認可 |
| 同期・非同期 | [sync-async-demo.py](sync-async-demo.py) | 標準ライブラリだけで動くasyncioのデモ |

Phase 01とPhase 02のAPIは`/health`と`/tasks`のCRUDを共有し、データはメモリ上に保存されます。永続化はPhase 03以降です。

## 動かし方

Python 3.14と[uv](https://docs.astral.sh/uv/)を用意してから、リポジトリを取得します。

```bash
git clone https://github.com/egg-seed/task-track-v2.git
cd task-track-v2
```

希望するフェーズへ移動してから、以下を実行してください。Phase 04ではアプリ起動前にAlembicの適用も必要です。

```bash
cd phase-01-basic
# または cd phase-02-router
uv sync --locked
uv run fastapi dev
```

`http://127.0.0.1:8000/docs`から試せます。

`cognito-auth` を起動するには、Cognito User Poolの環境変数が必要です。手順は [cognito-auth/README.md](cognito-auth/README.md) を参照してください。テストだけならAWSアカウントは不要です。

## テストと品質チェック

各フェーズには独立した`pyproject.toml`、`uv.lock`、テストがあります。Phase 01〜04では、次のコマンドで確認できます。

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

`cognito-auth` は `app.py` と `test_app.py` だけの構成なので、型チェックは `uv run mypy` で実行します。

GitHub ActionsはMatrixでPhase 01〜04を独立して検証します。Python 3.14環境で各フェーズのuv同期、Ruff、mypy、pytestを実行します。Phase 01のDockerビルドとヘルスチェック、Cognitoサンプルのオフラインテスト、asyncioデモもCI対象です。

各フェーズは書籍の完成時点のスナップショットとして維持し、不要な構成変更は行わず、必要な修正はすべてCIで確認します。

## ライセンス

[MIT License](LICENSE)
