from enum import Enum


class R6SSS(Enum):
	ICON = "<:R6SSS:1263902541238763621>"


class Indicator(Enum):
	OPERATIONAL = "🟢"
	INTERRUPTED = "🟡"
	DEGRADED = "🔴"
	MAINTENANCE = "🔧"
	UNKNOWN = "⬜"


class Platform(Enum):
	PC = "<:PC_Color:1263902627096428604>"
	PLAYSTATION = "<:PlayStation_Color:1263902647346266112>"
	XBOX = "<:Xbox_Color:1263902679092953132>"


class Status(Enum):
	OPERATIONAL = "<:Operational:1263909314343604254>"
	INTERRUPTED = "<:Interrupted:1263909332936818802>"
	DEGRADED = "<:Degraded:1263909344542461962>"
	UNKNOWN = "<:Unknown:1263909355632463943>"
	MAINTENANCE = "<:Maintenance:1263909369133662228>"
