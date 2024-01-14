import logging
from enum import Enum
from typing import NewType
from urllib.parse import urljoin

import httpx
from apscheduler.schedulers.blocking import BlockingScheduler

from DHCPStaticMapper.config import load_env_config, Config
from DHCPStaticMapper.utils import parse_csrf

IPADDR = NewType("IPADDR", str)
MACADDR = NewType("MACADDR", str)
HOSTNAME = NewType("HOSTNAME", str)
DESC = NewType("DESC", str)
IFACE = NewType("IFACE", str)


class LeaseType(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"


def dhcp_dynamic_leases_table(
        http_client: httpx.Client,
        base_url: str,
        iface: str
) -> list[tuple[IPADDR, MACADDR, HOSTNAME, DESC, IFACE]] | None:
    logging.info("[DHCPv4] Getting list from DHCP")
    response = http_client.get(
        url=urljoin(base_url, "/api/dhcpv4/leases/searchLease"),
    )

    if response.is_error:
        logging.error("[DHCP] Failed to get list from DHCP")
        logging.error(response.text)
        return

    rows = response.json()["rows"]

    table = []
    for row in rows:
        ipaddr = row["address"]
        macaddr = row["mac"]
        hostname = row["hostname"]
        description = row["descr"]
        interface = row["if_descr"]
        orig_iface = row["if"]
        lease_type = LeaseType(row["type"])
        end_time = row.get("end_time")
        table.append((ipaddr, macaddr, hostname, description, interface, lease_type, end_time))

    if iface:
        table = list(filter(lambda item: item[4] == iface, table))

    for item in table:
        repeat_items = []
        for el in table:
            if item[2] == el[2]:
                repeat_items.append(el)

        if len(repeat_items) == 1:
            continue

        logging.info(
            f"[DHCPv4] Found repeat {len(repeat_items)} leases for mac:{item[1]!r} hostname:{item[2]!r}"
        )
        dynamic_item = None
        static_item = None
        for el in repeat_items:
            if el[5] == LeaseType.DYNAMIC:
                if dynamic_item:
                    logging.warning(
                        f"[DHCPv4] Multiple dynamic leases for hostname:{el[2]!r} ip:{el[0]!r} mac:{el[1]!r}"
                    )
                    if el[6] > dynamic_item[6]:
                        table.remove(dynamic_item)
                        dynamic_item = el
                        continue
                dynamic_item = el
            elif el[5] == LeaseType.STATIC:
                if static_item:
                    logging.warning(
                        f"[DHCPv4] Multiple static leases for hostname:{el[2]!r} ip:{el[0]!r} mac:{el[1]!r}"
                    )
                    table.remove(static_item)
                static_item = el

        if static_item and dynamic_item:
            table.remove(static_item)
            table.remove(dynamic_item)
        elif static_item and not dynamic_item:
            table.remove(static_item)
        elif not static_item and dynamic_item:
            logging.info(
                f"[DHCPv4] Choosing lease for hostname:{dynamic_item[2]!r} ip:{dynamic_item[0]!r} mac:{dynamic_item[1]!r}"
            )
        else:
            logging.critical(
                f"[DHCPv4] No leases for hostname:{item[2]!r} ip:{item[0]!r} mac:{item[1]!r}"
            )

    table = list(filter(lambda item: item[5] == LeaseType.DYNAMIC, table))
    return list(map(lambda item: (item[0], item[1], item[2], item[3], orig_iface), table))


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


def make_static_dhcp(http_client: httpx.Client, config: Config):
    logging.info("[StaticMapper] Making static DHCP records")

    # Check access
    if not check_access(http_client, urljoin(config.BASE_URL, "/services_dhcp.php")):
        if not auth(http_client, config.LOGIN, config.PASSWORD, config.BASE_URL):
            logging.error("[StaticMapper] Failed to authenticate")
            return
        if not check_access(http_client, urljoin(config.BASE_URL, "/services_dhcp.php")):
            logging.error("[StaticMapper] Failed to check access after authentication")
            return

    # Resources
    dhcp_leases = dhcp_dynamic_leases_table(http_client, config.BASE_URL, config.IFACE_NAME)

    for item in dhcp_leases:
        ipaddr = item[0]
        macaddr = item[1]
        hostname = item[2]
        description = item[3]
        iface = item[4]

        # Parse CSRF
        form_response = http_client.get(
            url=urljoin(config.BASE_URL, "/services_dhcp_edit.php"),
            params={"if": iface}
        )
        csrf = parse_csrf(form_response.text)
        if not csrf:
            logging.error("[StaticMapper] Failed to parse CSRF")
            return

        # Make static DHCP record
        http_client.headers.update({"X-CSRFToken": csrf[1]})
        make_response = http_client.post(
            url=urljoin(config.BASE_URL, "/services_dhcp_edit.php"),
            params={"if": iface},
            data={
                csrf[0]: csrf[1],
                "mac": macaddr,
                "ipaddr": ipaddr,
                "hostname": hostname,
                "descr": description,
                "if": iface,
            },
        )
        if make_response.is_error:
            logging.error("[StaticMapper] Failed to make static DHCP record")
            logging.error(make_response.text)
            return

        # Save static DHCP record
        http_client.headers.update({"X-CSRFToken": csrf[1]})
        apply_response = http_client.post(
            url=urljoin(config.BASE_URL, "/services_dhcp.php"),
            data={
                csrf[0]: csrf[1],
                "apply": "Apply changes",
                "if": iface,
            },
        )
        if apply_response.is_error:
            logging.error("[StaticMapper] Failed to save static DHCP record")
            logging.error(apply_response.text)
            return

        logging.info(f"[StaticMapper] Made static DHCP record for hostname:{hostname!r} ip:{ipaddr!r} mac:{macaddr!r}")
    logging.info("")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s %(levelname)s %(name)s] %(message)s",
    )

    config = load_env_config("../../.env")
    http_client = httpx.Client(
        auth=(config.CLIENT_ID, config.ACCESS_TOKEN),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        make_static_dhcp,
        args=(http_client, config),
        trigger="interval",
        seconds=config.SYNC_INTERVAL_SEC,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
