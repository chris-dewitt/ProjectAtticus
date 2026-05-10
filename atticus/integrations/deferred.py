"""Phase 8 placeholders — OAuth and provider APIs are not wired in this build."""


def gmail_status() -> str:
    return (
        "Gmail integration is not configured yet. Planned: OAuth to Google, draft-only send flow, "
        "and explicit Boss confirmation before any message leaves the machine."
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
