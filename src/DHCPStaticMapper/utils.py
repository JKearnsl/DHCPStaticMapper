from bs4 import BeautifulSoup


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
