"""Phase 8 status strings for remaining / partial integrations."""


def gmail_status() -> str:
    return (
        "Gmail: /gmail status|auth|inbox|read|draft|send when tools.email.enabled "
        '(optional pip install -e ".[gmail]"). Send requires explicit confirmation.'
    )


def calendar_status() -> str:
    return (
        "Calendar: /cal status|auth|list|create|delete when tools.calendar.enabled "
        '(same Google API extra as Gmail: pip install -e ".[gmail]"). '
        "Writes require y/N plus CREATE/DELETE."
    )


def browser_status() -> str:
    return (
        "Browser: /open opens a URL; /browse fetches https/http pages into local citations "
        "(/citations lists them) when tools.browser.enabled. Host allowlist optional."
    )
