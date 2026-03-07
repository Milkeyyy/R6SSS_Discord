@echo off

REM ディレクトリ移動
cd /d ".."

REM 環境変数の設定
call .venv\Scripts\activate

REM 依存関係のインストール
uv sync

REM uv-upx のインストール
uv tool install uv-upx

REM 依存関係の更新
uv-upgrade --profile with_pinned

REM requirements.txt の更新
uv export -o requirements.txt --no-hashes --no-dev

REM 環境変数の解除
call deactivate

echo 依存関係の更新完了

pause
