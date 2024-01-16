from enum import Enum
from typing import NewType

IPADDR = NewType("IPADDR", str)
MACADDR = NewType("MACADDR", str)
HOSTNAME = NewType("HOSTNAME", str)
DESC = NewType("DESC", str)
IFACE = NewType("IFACE", str)


class LeaseType(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
