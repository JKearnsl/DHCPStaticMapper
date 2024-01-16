import logging
from urllib.parse import urljoin

import httpx
from apscheduler.schedulers.blocking import BlockingScheduler

from DHCPStaticMapper.auth import check_access, auth
from DHCPStaticMapper.config import load_env_config, Config
from DHCPStaticMapper.dhcp_leases import dhcp_dynamic_leases_table
from DHCPStaticMapper.utils import parse_csrf, parse_ntp, parse_dns


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
    dhcp_leases = dhcp_dynamic_leases_table(http_client, config.BASE_URL, config.IFACE_ID, config.EXCLUDE_HOSTNAME)

    if not dhcp_leases:
        logging.info("Nothing to do ")
        return

    # Parse NTP and DNS
    form_response = http_client.get(
        url=urljoin(config.BASE_URL, "/services_dhcp.php"),
        params={"if": config.IFACE_ID}
    )
    ntp = parse_ntp(form_response.text)
    dns = parse_dns(form_response.text)

    if not ntp:
        logging.error("[StaticMapper] Failed to parse NTP")
        return

    if ntp and not ntp[0] and not ntp[1]:
        logging.error("[StaticMapper] NTP is not set")
        return

    if not dns:
        logging.error("[StaticMapper] Failed to parse DNS")
        return

    if dns and not dns[0] and not dns[1]:
        logging.error("[StaticMapper] DNS is not set")
        return

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
                "ntp1": ntp[1],
                "ntp2": ntp[0],
                "dns1": dns[1],
                "dns2": dns[0],
            }
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
