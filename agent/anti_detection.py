"""Human-paced interaction helpers used for visible, reliable local automation.

These helpers do not bypass CAPTCHAs, access controls, or portal challenges.
"""

import random
import time


def random_sleep(minimum: float = 0.5, maximum: float = 2.5) -> None:
    time.sleep(random.uniform(minimum, maximum))


def type_with_delay(locator, value: str) -> None:
    if value in (None, ""):
        return
    locator.fill("")
    locator.type(str(value), delay=random.randint(35, 110))


def random_mouse_movement(page) -> None:
    viewport = page.viewport_size or {"width": 1200, "height": 800}
    page.mouse.move(
        random.randint(20, max(21, viewport["width"] - 20)),
        random.randint(20, max(21, viewport["height"] - 20)),
        steps=random.randint(3, 8),
    )


def click_with_pacing(page, locator) -> None:
    random_mouse_movement(page)
    random_sleep(0.2, 0.8)
    locator.click()


def randomized_scroll(page) -> None:
    page.mouse.wheel(0, random.randint(180, 520))
    random_sleep(0.3, 1.0)
