from urllib.parse import urlparse

from .generic import GenericHandler
from .greenhouse import GreenhouseHandler
from .lever import LeverHandler
from .linkedin import LinkedInHandler
from .workday import WorkdayHandler


HANDLERS = {
    "greenhouse": GreenhouseHandler,
    "lever": LeverHandler,
    "workday": WorkdayHandler,
    "linkedin": LinkedInHandler,
    "generic": GenericHandler,
}


def portal_key(portal: str | None, url: str | None) -> str:
    value = f"{portal or ''} {url or ''}".lower()
    if "greenhouse" in value:
        return "greenhouse"
    if "lever" in value:
        return "lever"
    if "workday" in value or "myworkdayjobs" in value:
        return "workday"
    if "linkedin" in value:
        return "linkedin"
    return "generic"


def portal_domain(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()
    parts = hostname.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname


def build_handler(portal: str | None, url: str, **kwargs):
    key = portal_key(portal, url)
    return key, HANDLERS[key](**kwargs)
