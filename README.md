# R6SServerStatusBot
Discordのテキストチャンネルにレインボーシックス シージのサーバーステータスを送信してくれるBotです。

[**[Botをサーバーに招待]**](https://discord.com/api/oauth2/authorize?client_id=990497421488451615&permissions=3072&scope=bot%20applications.commands)

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
### URL
- `https://r6sss.milkeyyy.com/api`
- `https://r6sss.milkeyyy.com/api?platforms=[取得するプラットフォーム]`

#### 指定できるプラットフォーム
- `PC`
- `Stadia`
- `PS4`
- `PS5`
- `XBOXONE`
- `XBOX SERIES X`

### 例
- `GET` - `https://r6sss.milkeyyy.com/api`
##### パラメーターを指定しない場合は、全てのプラットフォームのステータスを取得できます。
```json
{"PC":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS4":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS5":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"Stadia":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"XBOX SERIES X":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"XBOXONE":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"_update_date":"Thu, 15 Dec 2022 15:26:58 GMT"}
```

- `GET` - `https://r6sss.milkeyyy.com/api?platforms=PS4,PS5`
##### 複数指定する場合は `,` で区切ります。
```json
{"PS4":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}},"PS5":{"ImpactedFeatures":null,"Maintenance":null,"Status":{"Authentication":"Operational","Connectivity":"Operational","Leaderboard":"Operational","Matchmaking":"Operational","Purchase":"Operational"}}}
```