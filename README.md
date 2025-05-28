# R6SSS Discord Bot
Discordのテキストチャンネルにレインボーシックス シージのサーバーステータスを送信してくれるBotです。


[**[Botをサーバーへ招待する]**](https://discord.com/oauth2/authorize?client_id=990497421488451615)

### 稼働状況
[![Status](http://status.milkeyyy.com/api/badge/13/status?style=for-the-badge)](https://status.milkeyyy.com/)


![Preview](https://github.com/Milkeyyy/R6SServerStatusBot/assets/59532514/2c1ee137-133c-470d-be9d-592b96b8602f)


### Discord 以外の Bot はこちら
[![Bluesky](https://badgen.org/img/bluesky/r6sss.milkeyyy.com/followers?style=for-the-badge&label=Bluesky)](https://bsky.app/profile/r6sss.milkeyyy.com)

### サポート
[![Discord](https://img.shields.io/discord/889239399550844978?style=for-the-badge&label=Discord&logo=discord&logoColor=white)](https://discord.gg/bMf9dDjndC)

## コマンド
- `create [テキストチャンネル]`
  - 指定したテキストチャンネルへ**5分ごとに自動更新される**サーバーステータスを作成します。
    - 送信されたサーバーステータスは、**メッセージが削除**されるか、**`create` コマンドで新しいサーバーステータスが作成**されるまで更新され続けます。
    - テキストチャンネルを指定しなかった場合は、コマンドを実行したチャンネルへ送信されます。
- `status`
  - 現在のサーバーステータスを送信します。(自動更新はされません)
- `setindicator <有効/無効>`
  - サーバーステータスのインジケーター(絵文字)をテキストチャンネルの名前の先頭に表示するかどうかを設定します。
- `setlanguage <言語>`
  - サーバーステータスの表示言語を設定します。
  - 指定できる言語
    - `en-GB` / `en-US` (English / 英語)
    - `ja` (日本語 / Japanese)
- `setnotification <有効/無効> [テキストチャンネル] [ロール]`
  - サーバーステータスに変化があった際に送信される通知を設定します。
    - テキストチャンネルを指定しなかった場合は、コマンドを実行したチャンネルへ送信されます。
- `ping`
  - このBotのレイテンシーを送信します。
- `about`
  - このBotの情報を送信します。
