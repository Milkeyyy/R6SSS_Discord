# R6SSS Discord Bot
Discordのテキストチャンネルにレインボーシックス シージのサーバーステータスを送信してくれるBotです。


<img src="https://github.com/user-attachments/assets/f65b79d4-a494-426d-a969-79df679309f8" width="40%" />
<img src="https://github.com/user-attachments/assets/e09cd902-1807-4781-8c83-96613592938b" width="40%" />

---

[**[Botをサーバーへ招待する]**](https://discord.com/oauth2/authorize?client_id=990497421488451615)

### 稼働状況
[![Status](http://status.milkeyyy.com/api/badge/13/status?style=for-the-badge)](https://status.milkeyyy.com/)

### サポート Discord サーバー
[![Discord](https://img.shields.io/discord/889239399550844978?style=for-the-badge&label=Discord&logo=discord&logoColor=white)](https://discord.gg/bMf9dDjndC)

### Discord 以外の Bot はこちら
[![Bluesky](https://badgen.org/img/bluesky/r6sss.milkeyyy.com/followers?style=for-the-badge&label=Bluesky)](https://bsky.app/profile/r6sss.milkeyyy.com)


## コマンド

- `about`
  - このBotの情報を送信します。

- `ping`
  - このBotのレイテンシーを送信します。

- `status`
  - 現在のサーバーステータスを送信します。(自動更新はされません)

### 管理コマンド
これらのコマンドは、サーバーの管理者権限を持ったユーザーのみが実行できます。

- `create [テキストチャンネル]`
  - 指定したテキストチャンネルへ**5分ごとに自動更新される**サーバーステータスを作成します。
    - 送信されたサーバーステータスは、**メッセージが削除**されるか、**`create` コマンドで新しいサーバーステータスが作成**されるまで更新され続けます。
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
