import os
import subprocess

from discord import Bot


NAME = "R6SSS"
VERSION = "2.0.0"
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

_git_commit_hash = None


def get_git_commit_hash() -> str:
	global _git_commit_hash
	try:
		if _git_commit_hash:
			return _git_commit_hash
		cwd = os.path.dirname(os.path.abspath(__file__))
		out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=cwd)
		_git_commit_hash = out.strip().decode("ascii")
		return _git_commit_hash
	except Exception:
		# Coolify
		hash = os.getenv("SOURCE_COMMIT")
		if hash:
			_git_commit_hash = hash
			return _git_commit_hash
		_git_commit_hash = "Unknown"
	return _git_commit_hash
