import os
from dataclasses import dataclass
from logging import getLogger
from dotenv import load_dotenv

logger = getLogger(__name__)

ACCESS_TOKEN_ENV = "ACCESS_TOKEN"
CLIENT_ID_ENV = "CLIENT_ID"
LOGIN_ENV = "LOGIN"
PASSWORD_ENV = "PASSWORD"
DHCP_DOMAIN_ENV = "DHCP_DOMAIN"
BASE_URL_ENV = "BASE_URL"
IFACE_NAME_ENV = "IFACE_NAME"
SYNC_INTERVAL_SEC_ENV = "SYNC_INTERVAL_SEC"
EXCLUDE_HOSTNAME_ENV = "EXCLUDE_HOSTNAME"


class ConfigParseError(ValueError):
    pass


@dataclass
class Config:
    ACCESS_TOKEN: str
    CLIENT_ID: str
    LOGIN: str
    PASSWORD: str
    BASE_URL: str
    IFACE_NAME: str
    SYNC_INTERVAL_SEC: int
    EXCLUDE_HOSTNAME: str = None


def to_bool(value) -> bool:
    return str(value).strip().lower() in ("yes", "true", "t", "1")


def get_str_env(key: str, optional: bool = False) -> str:
    val = os.getenv(key)
    if not val and not optional:
        logger.error("%s is not set", key)
        raise ConfigParseError(f"{key} is not set")
    return val


def get_int_env(key: str, optional: bool = False) -> int:
    val = os.getenv(key)
    if not val and not optional:
        logger.error("%s is not set", key)
        raise ConfigParseError(f"{key} is not set")

    try:
        val = int(val)
    except ValueError:
        logger.error("%s is not a valid integer", key)
        raise ConfigParseError(f"{key} is not a valid integer")
    return val


def load_env_config(env_file: str | os.PathLike = None) -> Config:
    if not env_file:
        env_file = ".env"

    if os.path.exists(env_file):
        logger.info(f"Loading env from {env_file!r}")

        load_dotenv(env_file)
    else:
        logger.info("Loading env from os.environ")

    return Config(
        ACCESS_TOKEN=get_str_env(ACCESS_TOKEN_ENV),
        CLIENT_ID=get_str_env(CLIENT_ID_ENV),
        LOGIN=get_str_env(LOGIN_ENV),
        PASSWORD=get_str_env(PASSWORD_ENV),
        BASE_URL=get_str_env(BASE_URL_ENV),
        IFACE_NAME=get_str_env(IFACE_NAME_ENV),
        SYNC_INTERVAL_SEC=get_int_env(SYNC_INTERVAL_SEC_ENV),
        EXCLUDE_HOSTNAME=get_str_env(EXCLUDE_HOSTNAME_ENV, optional=True),
    )
