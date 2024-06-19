import logging
import sys

from colorlog import ColoredFormatter


def get_logger(name=__name__, formatter=None, level=logging.DEBUG, stream=sys.stderr):
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create handlers
    c_handler = logging.StreamHandler(stream=stream)
    c_handler.setLevel(level)

    # Create formatters and add them to the handlers
    if formatter is None:
        c_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        c_handler.setFormatter(c_format)
    else:
        c_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(c_handler)

    return logger


def get_passed_logger(name=__name__, stream=sys.stderr):
    passed_formatter = ColoredFormatter(
        # "%(log_color)s%(levelname)-8s%(reset)s %(message)s",
        "%(log_color)s*** PASSED: %(reset)s %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            "INFO": "bold_green",
        },
        stream=stream,
    )

    return get_logger(
        name,
        level=logging.INFO,
        formatter=passed_formatter,
        stream=stream,
    )


def get_failed_logger(name=__name__, stream=sys.stderr):
    failed_formatter = ColoredFormatter(
        # "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "%(log_color)s*** FAILED: %(reset)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        reset=True,
        log_colors={
            "INFO": "bold_red",
        },
        stream=stream,
    )

    return get_logger(
        name,
        level=logging.INFO,
        formatter=failed_formatter,
        stream=stream,
    )
