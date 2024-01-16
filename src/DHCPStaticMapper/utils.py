from bs4 import BeautifulSoup

from DHCPStaticMapper.type import IPADDR


def parse_csrf(html: str) -> tuple[str, str] | None:
    soup = BeautifulSoup(html, "html.parser")
    csrf_token = soup.find("input", {"type": "hidden"})

    if not csrf_token:
        return None

    csrf_key = csrf_token.attrs.get("name")
    csrf_value = csrf_token.attrs.get("value")
    if not csrf_key or not csrf_value:
        return None

    return csrf_key, csrf_value


def parse_ntp(html: str) -> tuple[IPADDR | None, IPADDR | None] | None:
    soup = BeautifulSoup(html, "html.parser")
    ntp_1 = soup.find("input", {"name": "ntp1"})
    ntp_2 = soup.find("input", {"name": "ntp2"})

    if not ntp_1 or not ntp_1:
        return None

    return ntp_1.attrs.get("value"), ntp_2.attrs.get("value")


def parse_dns(html: str) -> tuple[IPADDR | None, IPADDR | None] | None:
    soup = BeautifulSoup(html, "html.parser")
    dns_1 = soup.find("input", {"name": "dns1"})
    dns_2 = soup.find("input", {"name": "dns2"})

    if not dns_1 or not dns_1:
        return None

    return dns_1.attrs.get("value"), dns_2.attrs.get("value")
