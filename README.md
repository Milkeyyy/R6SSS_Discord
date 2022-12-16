# R6SServerStatusBot
Discordのテキストチャンネルにレインボーシックス シージのサーバーステータスを送信してくれるBotです。

[**[Botをサーバーに招待]**](https://discord.com/api/oauth2/authorize?client_id=990497421488451615&permissions=76800&scope=bot%20applications.commands)

## コマンド
- `create [テキストチャンネル]` - 指定したテキストチャンネルへ**1分ごとに自動更新される**サーバーステータスを作成します。
	- ##### 送信されたサーバーステータスは、メッセージが削除されるか、`create` コマンドで新しいサーバーステータスが作成されるまで更新され続けます。
	- ##### テキストチャンネルを指定しなかった場合は、コマンドを実行したチャンネルへ送信されます。
- `status` - 現在のサーバーステータスを送信します。(自動更新はされません)
- `setlanguage <言語>` - サーバーステータスの表示言語を設定します。
	- 指定できる言語
		- `English` (英語)
		- `日本語 / Japanese` (日本語)
		- `한국어 / Korean` (韓国語)
- `about` - このBotの情報を送信します。
- `ping` - このBotのレイテンシーを送信します。

## API
URL: https://r6sss.milkeyyy.com/api

[**ドキュメント** (適当)](https://r6sss.milkeyyy.com/api/docs)

### 例
- `GET` - `https://r6sss.milkeyyy.com/api`
```json
{"PC":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS4":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS5":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"Stadia":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"XBOX SERIES X":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"XBOXONE":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}}}
```

- `GET` - `https://r6sss.milkeyyy.com/api?platform=PS4&platform=PS5`
```json
{"PS4":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS5":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}}}
```

#### パラメーターに指定できるプラットフォーム
プラットフォームを指定しない場合は、すべてのプラットフォームのサーバーステータスを取得できます。
- `PC`
- `Stadia`
- `PS4`
- `PS5`
- `XBOXONE`
- `XBOX SERIES X`