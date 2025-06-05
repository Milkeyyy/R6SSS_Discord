import os

from discord import Bot

NAME = "R6SSS"
VERSION = (2, 1, 0)
VERSION_STRING = ".".join(map(str, VERSION))
COPYRIGHT = "Copyright (C) 2025 Milkeyyy"

GITHUB_REPO_URL = "https://github.com/Milkeyyy/R6SSS_Discord"
BLUESKY_BOT_URL = "https://bsky.app/profile/r6sss.milkeyyy.com"
TWITTER_BOT_URL = "https://twitter.com/R6SSS_JP"

DEVELOPER_NAME = "Milkeyyy"
DEVELOPER_WEBSITE_URL = "https://milkeyyy.com"
DEVELOPER_TWITTER_URL = "https://twitter.com/Milkeyyy_53"


# くらいあんと
intents = None
client = Bot(intents=intents)


def get_git_commit_hash() -> str:
	# Coolify
	commit_hash = os.getenv("SOURCE_COMMIT")
	if commit_hash is None or commit_hash == "":
		commit_hash = "Unknown"
	return commit_hash
