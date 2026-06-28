import os

import uvicorn


def port_from_environment() -> int:
    value = os.getenv("PORT", "8000").strip()
    try:
        port = int(value)
    except ValueError as exc:
        raise RuntimeError(f"PORT must be an integer, received {value!r}") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError(f"PORT must be between 1 and 65535, received {port}")
    return port


def main() -> None:
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port_from_environment(),
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
