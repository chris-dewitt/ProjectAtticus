"""Phase 8 placeholders — remaining OAuth surfaces beyond Gmail MVP."""


def gmail_status() -> str:
    return (
        "Gmail: use /gmail status|auth|inbox|read|draft|send when tools.enabled and "
        "tools.email.enabled are true (optional pip install -e \".[gmail]\"). "
        "Send always requires explicit confirmation."
    )


def calendar_status() -> str:
    return (
        "Calendar integration is not configured yet. Planned: read scopes first, "
        "writes always behind a confirmation gate."
    )


def browser_status() -> str:
    return (
        "Headless browsing with source tracking is not enabled yet. "
        "Use /open <https://...> for a single URL after confirmation when browser tools are on."
    )
