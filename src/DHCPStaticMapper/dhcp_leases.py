import logging
from urllib.parse import urljoin

import httpx

from DHCPStaticMapper.types import (
    IPADDR,
    MACADDR,
    HOSTNAME,
    DESC,
    IFACE,
    LeaseType
)


def dhcp_dynamic_leases_table(
        http_client: httpx.Client,
        base_url: str,
        iface: str,
        exclude_hostname: str = None,
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

        if exclude_hostname and hostname == exclude_hostname:
            continue
        table.append((ipaddr, macaddr, hostname, description, interface, lease_type, end_time))

    if iface:
        table = list(filter(lambda _: _[4] == iface, table))

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
                f"[DHCPv4] Choosing lease for hostname:{dynamic_item[2]!r} "
                f"ip:{dynamic_item[0]!r} mac:{dynamic_item[1]!r}"
            )
        else:
            logging.critical(
                f"[DHCPv4] No leases for hostname:{item[2]!r} ip:{item[0]!r} mac:{item[1]!r}"
            )

    table = list(filter(lambda _: _[5] == LeaseType.DYNAMIC, table))
    return list(map(lambda _: (_[0], _[1], _[2], _[3], orig_iface), table))
