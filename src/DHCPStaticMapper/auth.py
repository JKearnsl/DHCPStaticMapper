import logging

import httpx

from DHCPStaticMapper.utils import parse_csrf


def auth(http_client: httpx.Client, login: str, password: str, url: str) -> bool:
    logging.debug("[Auth] Authenticating")

    csrf_response = http_client.get(
        url=url,
    )
    csrf = parse_csrf(csrf_response.text)
    if not csrf:
        logging.error("[Auth] Failed to parse CSRF")
        return False
    http_client.headers.update({"X-CSRFToken": csrf[1]})
    auth_response = http_client.post(
        url=url,
        data={
            csrf[0]: csrf[1],
            "usernamefld": login,
            "passwordfld": password,
            "login": 1
        },
    )

    if auth_response.is_error:
        logging.error(f"[Auth] Failed to authenticate: {auth_response.status_code}")
        logging.debug(auth_response.text)
        return False

    logging.info("[Auth] Authenticated")
    return True


def check_access(http_client: httpx.Client, url: str, method: str = "get") -> bool:
    logging.debug("[Access] Checking access")

    response = http_client.request(
        method=method,
        url=url,
    )
    if response.is_error or response.text.count("page-login") > 0:
        logging.debug(f"[Access] Failed to check access: {response.status_code}")
        logging.debug(response.text)
        return False
    return True
