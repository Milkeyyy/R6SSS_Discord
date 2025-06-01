import logging


discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.ERROR)
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()

stream_formatter = logging.Formatter(
	fmt="[%(asctime)s.%(msecs)03d] %(levelname)s [%(thread)d] %(message)s"
)
stream_handler.setFormatter(stream_formatter)

logger.addHandler(stream_handler)
