def detect_portal(url: str) -> str:
    value = (url or "").lower()
    if "greenhouse.io" in value:
        return "greenhouse"
    if "lever.co" in value:
        return "lever"
    if "ashbyhq" in value:
        return "ashby"
    if "workday" in value:
        return "workday"
    return "generic"

def detect_blocker(page) -> str | None:
    text = page.locator("body").inner_text(timeout=3000).lower()
    if "captcha" in text or "verify you are human" in text:
        return "NEEDS_CAPTCHA"
    if "sign in" in text or "log in" in text or "login" in text:
        return "NEEDS_LOGIN"
    return None
