# R6SSS Discord Bot

> [日本語 / Japanese](./README.ja.md) | **English**

> This README was translated using Google Gemini.

A Discord bot that sends the server status for Rainbow Six Siege to a text channel.

You can also create a server status message that updates periodically.

<img src="https://github.com/user-attachments/assets/e8c49ff2-32ad-49e2-ba60-85ba642fed07" width="40%" />

---

### [**[Invite Bot to Server]**](https://discord.com/oauth2/authorize?client_id=990497421488451615)

### Status

[![Status](http://status.milkeyyy.com/api/badge/21/status?style=for-the-badge)](https://status.milkeyyy.com/)

### Support Discord Server

[![Discord](https://img.shields.io/discord/889239399550844978?style=for-the-badge&label=Discord&logo=discord&logoColor=white)](https://discord.gg/bMf9dDjndC)

### Other Bots
These bots automatically post updates when the server status changes, such as at the start of maintenance.

[![Bluesky](https://badgen.org/img/bluesky/r6sss.milkeyyy.com/followers?style=for-the-badge&label=Bluesky)](https://bsky.app/profile/r6sss.milkeyyy.com)

[![Twitter](https://img.shields.io/badge/@R6SSS__JP-blue?style=for-the-badge&label=Twitter&labelColor=gray&logo=data:image/svg%2bxml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbDpzcGFjZT0icHJlc2VydmUiIHZpZXdCb3g9IjAgMCAyNDggMjA0Ij4KICA8cGF0aCBmaWxsPSIjMWQ5YmYwIiBkPSJNMjIxLjk1IDUxLjI5Yy4xNSAyLjE3LjE1IDQuMzQuMTUgNi41MyAwIDY2LjczLTUwLjggMTQzLjY5LTE0My42OSAxNDMuNjl2LS4wNGMtMjcuNDQuMDQtNTQuMzEtNy44Mi03Ny40MS0yMi42NCAzLjk5LjQ4IDggLjcyIDEyLjAyLjczIDIyLjc0LjAyIDQ0LjgzLTcuNjEgNjIuNzItMjEuNjYtMjEuNjEtLjQxLTQwLjU2LTE0LjUtNDcuMTgtMzUuMDcgNy41NyAxLjQ2IDE1M3IDEuMTYgMjIuOC0uODctMjMuNTYtNC43Ni00MC41MS0yNS40Ni00MC41MS00OS41di0uNjRjNy4wMiAzLjkxIDE0Ljg4IDYuMDggMjIuOTIgNi4zMkMxMS41OCA2My4zMSA0Ljc0IDMzLjc5IDE4LjE0IDEwLjcxYzI1LjY0IDMxLjU1IDYzLjQ3IDUwLjczIDEwNC4wOCA1Mi43Ni00LjA3LTE3LjU0IDEuNDktMzUuOTIgMTQuNjEtNDguMjUgMjAuMzQtMTkuMTIgNTIuMzMtMTguMTQgNzEuNDUgMi4xOSAxMS4zMS0yLjIzIDIyLjE1LTYuMzggMzIuMDctMTIuMjYtMy43NyAxMS42OS0xMS42NiAyMS42Mi0yMi4yIDI3LjkzIDEwLjAxLTEuMTggMTkuNzktMy44NiAyOS03Ljk1LTYuNzggMTAuMTYtMTUuMzIgMTkuMDEtMjUuMiAyNi4xNnoiLz4KPC9zdmc+)
](https://twitter.com/R6SSS_JP)

## Commands

- `about`
  - Sends information about this bot.

- `ping`
  - Sends the bot's latency.

- `status`
  - Sends the current server status. (This message does not auto-update)

- `schedule`
  - Sends the current maintenance schedule. (This message does not auto-update)

### Admin Commands
These commands can only be run by users with administrator permissions.

- `create [text_channel]`
  - Creates a server status message in the specified text channel that **automatically updates every 2 minutes**.
    - The sent server status will continue to be updated until **the message is deleted** or **a new server status is created with the `create` command**.
    - If `text_channel` is not specified, it will be created in the channel where the command was executed.

- `viewsettings`
  - Displays the current settings.

- `setindicator <enable/disable>`
  - Sets whether to display the server status indicator (emoji) at the beginning of the text channel's name.

- `setlanguage <language>`
  - Sets the display language for the server status.
  - Available languages
    - 日本語 / Japanese
    - 英語 / English

- `setscheduledisplay <enable/disable>`
  - Sets whether to display the maintenance schedule in the server status message.

- `setnotification <enable/disable> [text_channel] [role] [auto_delete_seconds]`
  - Configures notifications to be sent when the server status changes.
    - If `text_channel` is not specified, notifications will be sent to the channel where the command was executed.
    - If a `role` is specified, it will be mentioned when the notification message is sent.
    - If `auto_delete_seconds` is set, the notification message will be automatically deleted after the specified time has passed.
      - Setting `auto_delete_seconds` to `0` disables this feature. (Default is `10` seconds.)
  > Example Notification
  >
  > <img src="https://github.com/user-attachments/assets/baf3e13d-647b-4feb-a77d-88f28f074d32" width="40%" />

## Terms of Service & Privacy Policy
- [Terms of Service](./TERMS-OF-SERVICE.md)
- [Privacy Policy](./PRIVACY-POLICY.md)
