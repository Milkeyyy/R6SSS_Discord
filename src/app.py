import tomllib
from os import getenv
from pathlib import Path


class App:
	NAME: str
	VERSION: tuple[int, int, int]
	VERSION_STRING: str
	COPYRIGHT: str = "Copyright (C) 2025 Milkeyyy"

	GITHUB_REPO_URL: str = "https://github.com/Milkeyyy/R6SSS_Discord"
	BLUESKY_BOT_URL: str = "https://bsky.app/profile/r6sss.milkeyyy.com"
	TWITTER_BOT_URL: str = "https://twitter.com/R6SSS_JP"

	DEVELOPER_NAME: str = "Milkeyyy"
	DEVELOPER_WEBSITE_URL: str = "https://milkeyyy.com"
	DEVELOPER_TWITTER_URL: str = "https://twitter.com/Milkeyyy_53"

	@classmethod
	def get_git_commit_hash(cls) -> str:
		# Coolify
		commit_hash = getenv("SOURCE_COMMIT")
		if commit_hash is None or commit_hash == "":
			commit_hash = "Unknown"
		return commit_hash

	@classmethod
	def load_pyproject(cls) -> None:
		"""pyproject.toml からアプリの情報を読み込む"""
		with Path("./pyproject.toml").open("rb") as f:
			d = tomllib.load(f)
		cls.NAME = d["project"]["description"]
		cls.VERSION = d["project"]["version"].split(".")
		cls.VERSION_STRING = d["project"]["version"]


App.load_pyproject()
