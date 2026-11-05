"""設定表示埋め込み (embeds.Settings) のユニットテスト"""

import embeds


async def test_settings_embed_renders_sections() -> None:
	embed = await embeds.Settings.settings(
		title="Current Settings",
		sections=[
			{
				"icon": ":gear:",
				"name": "Section",
				"value": "Value",
				"items": [
					{"name": "Child", "value": "Child Value"},
				],
			},
			{"name": "Plain", "value": "Plain Value", "inline": True},
		],
	)

	assert embed.title == ":gear: Current Settings"
	assert embed.fields[0].name == ":gear: Section"
	assert embed.fields[0].value == "Value\n> `Child`: Child Value"
	assert embed.fields[0].inline is False
	assert embed.fields[1].name == "Plain"
	assert embed.fields[1].value == "Plain Value"
	assert embed.fields[1].inline is True
