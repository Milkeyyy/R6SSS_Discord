import logging
import logging.handlers

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.ERROR)
logger = logging.getLogger("discord.app")
logger.setLevel(logging.DEBUG)

stream_formatter = logging.Formatter(
	fmt="[%(asctime)s.%(msecs)03d] %(levelname)s [%(thread)d] %(message)s",
)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(stream_formatter)

rotating_handler = logging.handlers.RotatingFileHandler(r"./logs//app.log", mode="a", maxBytes=100 * 1024, backupCount=10, encoding="utf-8")
rotating_handler.setLevel(logging.DEBUG)
rotating_handler.setFormatter(stream_formatter)

discord_logger.addHandler(rotating_handler)
logger.addHandler(rotating_handler)
logger.addHandler(stream_handler)
