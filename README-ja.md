# R6SSS Discord Bot

> **日本語 / Japanese** | [英語 / English](./README.md)

Discordのテキストチャンネルにレインボーシックス シージ エックスのサーバーステータスを送信してくれるBotです。


<img src="https://github.com/user-attachments/assets/e8c49ff2-32ad-49e2-ba60-85ba642fed07" width="40%" />

---

[**[Botをサーバーへ招待する]**](https://discord.com/oauth2/authorize?client_id=990497421488451615)

### 稼働状況
[![Status](http://status.milkeyyy.com/api/badge/21/status?style=for-the-badge)](https://status.milkeyyy.com/)

### サポート Discord サーバー
[![Discord](https://img.shields.io/discord/889239399550844978?style=for-the-badge&label=Discord&logo=discord&logoColor=white)](https://discord.gg/bMf9dDjndC)

### Discord 以外の Bot はこちら
[![Bluesky](https://badgen.org/img/bluesky/r6sss.milkeyyy.com/followers?style=for-the-badge&label=Bluesky)](https://bsky.app/profile/r6sss.milkeyyy.com)

[![Twitter](https://img.shields.io/badge/@R6SSS__JP-blue?style=for-the-badge&label=Twitter&labelColor=gray&logo=data:image/svg%2bxml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbDpzcGFjZT0icHJlc2VydmUiIHZpZXdCb3g9IjAgMCAyNDggMjA0Ij4KICA8cGF0aCBmaWxsPSIjMWQ5YmYwIiBkPSJNMjIxLjk1IDUxLjI5Yy4xNSAyLjE3LjE1IDQuMzQuMTUgNi41MyAwIDY2LjczLTUwLjggMTQzLjY5LTE0My42OSAxNDMuNjl2LS4wNGMtMjcuNDQuMDQtNTQuMzEtNy44Mi03Ny40MS0yMi42NCAzLjk5LjQ4IDggLjcyIDEyLjAyLjczIDIyLjc0LjAyIDQ0LjgzLTcuNjEgNjIuNzItMjEuNjYtMjEuNjEtLjQxLTQwLjU2LTE0LjUtNDcuMTgtMzUuMDcgNy41NyAxLjQ2IDE1LjM3IDEuMTYgMjIuOC0uODctMjMuNTYtNC43Ni00MC41MS0yNS40Ni00MC41MS00OS41di0uNjRjNy4wMiAzLjkxIDE0Ljg4IDYuMDggMjIuOTIgNi4zMkMxMS41OCA2My4zMSA0Ljc0IDMzLjc5IDE4LjE0IDEwLjcxYzI1LjY0IDMxLjU1IDYzLjQ3IDUwLjczIDEwNC4wOCA1Mi43Ni00LjA3LTE3LjU0IDEuNDktMzUuOTIgMTQuNjEtNDguMjUgMjAuMzQtMTkuMTIgNTIuMzMtMTguMTQgNzEuNDUgMi4xOSAxMS4zMS0yLjIzIDIyLjE1LTYuMzggMzIuMDctMTIuMjYtMy43NyAxMS42OS0xMS42NiAyMS42Mi0yMi4yIDI3LjkzIDEwLjAxLTEuMTggMTkuNzktMy44NiAyOS03Ljk1LTYuNzggMTAuMTYtMTUuMzIgMTkuMDEtMjUuMiAyNi4xNnoiLz4KPC9zdmc+)
](https://twitter.com/R6SSS_JP)


## コマンド

- `about`
  - このBotの情報を送信します。

- `ping`
  - このBotのレイテンシーを送信します。

- `status`
  - 現在のサーバーステータスを送信します。(自動更新はされません)

- `schedule`
  - 現在のメンテナンススケジュールを送信します。(自動更新はされません)


### 管理コマンド
これらのコマンドは、サーバーの管理者権限を持ったユーザーのみが実行できます。

- `create [テキストチャンネル]`
  - 指定したテキストチャンネルへ **2分ごとに自動更新される** サーバーステータスを作成します。
	- 送信されたサーバーステータスは、**メッセージが削除される** か、**`create` コマンドで新しいサーバーステータスが作成される** まで更新され続けます。
	- `テキストチャンネル` を設定しなかった場合は、コマンドを実行したチャンネルへ作成されます。

- `viewsettings`
  - 現在の設定内容を表示します。

- `setindicator <有効/無効>`
  - サーバーステータスのインジケーター(絵文字)をテキストチャンネルの名前の先頭に表示するかどうかを設定します。

- `setlanguage <言語>`
  - サーバーステータスの表示言語を設定します。
  - 指定できる言語
	- 日本語 / Japanese
	- 英語 / English

- `setnotification <有効/無効> [テキストチャンネル] [ロール] [自動削除]`
  - サーバーステータスに変化があった際に送信される通知を設定します。
	- `テキストチャンネル` を設定しなかった場合は、コマンドを実行したチャンネルへ送信されるように設定されます。
	- `ロール` を設定すると、通知メッセージの送信時に指定されたロールへメンションを行います。
	- `自動削除` を設定すると、指定された時間が経過すると通知メッセージが自動的に削除されるようになります。
	  - `自動削除` は `0` 秒に設定すると無効になります。 (初期値は `10` 秒です。)
  > 通知の例
  >
  > <img src="https://github.com/user-attachments/assets/baf3e13d-647b-4feb-a77d-88f28f074d32" width="40%" />


## 利用規約・プライバシーポリシー
- [利用規約](./TERMS-OF-SERVICE.md)
- [プライバシーポリシー](./PRIVACY-POLICY.md)
