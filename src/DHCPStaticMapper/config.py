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
IFACE_ID_ENV = "IFACE_ID"
SYNC_INTERVAL_SEC_ENV = "SYNC_INTERVAL_SEC"
EXCLUDE_HOSTNAME_ENV = "EXCLUDE_HOSTNAME"
RABBITMQ_HOST_ENV = "RABBITMQ_HOST"
RABBITMQ_PORT_ENV = "RABBITMQ_PORT"
RABBITMQ_USER_ENV = "RABBITMQ_USER"
RABBITMQ_PASSWORD_ENV = "RABBITMQ_PASSWORD"
RABBITMQ_QUEUE_ENV = "RABBITMQ_QUEUE"
RABBITMQ_EXCHANGE_ENV = "RABBITMQ_EXCHANGE"
RABBITMQ_VH_ENV = "RABBITMQ_VH"
SEND_DATA_TO_RABBITMQ_ENV = "SEND_DATA_TO_RABBITMQ"


class ConfigParseError(ValueError):
    pass


@dataclass
class Config:
    ACCESS_TOKEN: str
    CLIENT_ID: str
    LOGIN: str
    PASSWORD: str
    BASE_URL: str
    IFACE_ID: str
    SYNC_INTERVAL_SEC: int

    RABBITMQ_HOST: str | None
    RABBITMQ_PORT: str | None
    RABBITMQ_USER: str | None
    RABBITMQ_PASSWORD: str | None
    RABBITMQ_QUEUE: str | None
    RABBITMQ_EXCHANGE: str | None
    RABBITMQ_VH: str | None
    SEND_DATA_TO_RABBITMQ: bool

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

    is_rabbitmq = to_bool(os.getenv(SEND_DATA_TO_RABBITMQ_ENV, "false"))

    return Config(
        ACCESS_TOKEN=get_str_env(ACCESS_TOKEN_ENV),
        CLIENT_ID=get_str_env(CLIENT_ID_ENV),
        LOGIN=get_str_env(LOGIN_ENV),
        PASSWORD=get_str_env(PASSWORD_ENV),
        BASE_URL=get_str_env(BASE_URL_ENV),
        IFACE_ID=get_str_env(IFACE_ID_ENV),
        SYNC_INTERVAL_SEC=get_int_env(SYNC_INTERVAL_SEC_ENV),
        EXCLUDE_HOSTNAME=get_str_env(EXCLUDE_HOSTNAME_ENV, optional=True),

        SEND_DATA_TO_RABBITMQ=is_rabbitmq,
        RABBITMQ_HOST=get_str_env(RABBITMQ_HOST_ENV, optional=not is_rabbitmq),
        RABBITMQ_PORT=get_str_env(RABBITMQ_PORT_ENV, optional=not is_rabbitmq),
        RABBITMQ_USER=get_str_env(RABBITMQ_USER_ENV, optional=not is_rabbitmq),
        RABBITMQ_PASSWORD=get_str_env(RABBITMQ_PASSWORD_ENV, optional=not is_rabbitmq),
        RABBITMQ_QUEUE=get_str_env(RABBITMQ_QUEUE_ENV, optional=not is_rabbitmq),
        RABBITMQ_EXCHANGE=get_str_env(RABBITMQ_EXCHANGE_ENV, optional=not is_rabbitmq),
        RABBITMQ_VH=get_str_env(RABBITMQ_VH_ENV, optional=not is_rabbitmq),
    )
