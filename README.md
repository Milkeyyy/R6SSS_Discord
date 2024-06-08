# R6SSS
Discordのテキストチャンネルにレインボーシックス シージのサーバーステータスを送信してくれるBotです。

![Preview](https://github.com/Milkeyyy/R6SServerStatusBot/assets/59532514/2c1ee137-133c-470d-be9d-592b96b8602f)


[**🛡️ サポート Discord サーバー**](https://discord.gg/bMf9dDjndC)

[**📶 サービスステータス**](https://milkeyyy-services.cronitorstatus.com)

## Bot
### 稼働状況
![R6SSS Discord Bot](https://cronitor.io/badges/ncjpBt/production/HL2tEvnxU5AtBMfsEMI8O-smSZ0.svg)

[**[Botをサーバーに招待]**](https://discord.com/oauth2/authorize?client_id=990497421488451615)

## コマンド
- `create [テキストチャンネル]`
  - 指定したテキストチャンネルへ**5分ごとに自動更新される**サーバーステータスを作成します。
    - 送信されたサーバーステータスは、**メッセージが削除**されるか、**`create` コマンドで新しいサーバーステータスが作成**されるまで更新され続けます。
    - テキストチャンネルを指定しなかった場合は、コマンドを実行したチャンネルへ送信されます。
- `status`
  - 現在のサーバーステータスを送信します。(自動更新はされません)
- `setindicator <True/False>`
  - サーバーステータスのインジケーター(絵文字)をテキストチャンネルの名前の先頭に表示するかどうかを設定します。
- `setlanguage <言語>`
  - サーバーステータスの表示言語を設定します。
  - 指定できる言語
    - `en-GB` / `en-US` (English / 英語)
    - `ja` (日本語 / Japanese)
- `ping`
  - このBotのレイテンシーを送信します。
- `about`
  - このBotの情報を送信します。
