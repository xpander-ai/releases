"""Post the #dev notice for a develop -> main release PR of xpander-ai/xpander (repository_dispatch release-pr-ready).

David, 23 Nov 2026: "a notification for approval in #dev ... a short summary of what is ready, what goes up and what was
tested". xpander-ai/xpander's release-pr.yml sends the PR link, its title and the summary lines when it opens a release PR;
the Release Manager bot (a member of #dev) posts them. Anyone who may dispatch to this repository can send a payload, so it
is checked: a pull request URL of xpander-ai/xpander, a "Release N: develop to main" title, a run URL of xpander-ai/xpander,
and plain-text lines with Slack's control characters escaped (no mention, link or formatting can be injected).
"""

import json
import os
import re
import sys

from release_slack import slack

DEV_CHANNEL = "C0617LQBDMF"  # #dev
PR_URL = re.compile(r"^https://github\.com/xpander-ai/xpander/pull/([1-9][0-9]{0,6})$")
RUN_URL = re.compile(r"^https://github\.com/xpander-ai/xpander/actions/runs/([1-9][0-9]{0,15})$")
TITLE = re.compile(r"^Release ([1-9][0-9]{0,4}): develop to main\b")
MAX_LINE = 600


def plain(text) -> str:
    """One line of plain text, Slack-escaped (&, <, > are its only control characters), at most MAX_LINE characters."""
    text = " ".join(str(text or "").split())
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:MAX_LINE]


def render(payload: dict) -> str:
    url, title, run = str(payload.get("pr_url", "")), str(payload.get("title", "")), str(payload.get("proof_url", ""))
    if not PR_URL.match(url):
        raise ValueError(f"not a pull request of xpander-ai/xpander: {url[:120]!r}")
    number = TITLE.match(title)
    if not number:
        raise ValueError(f"not a release PR title: {title[:120]!r}")
    if run and not RUN_URL.match(run):
        raise ValueError(f"not a run of xpander-ai/xpander: {run[:120]!r}")
    tested = plain(payload.get("tested")) or "see the PR"
    if run:
        tested += f" (<{run}|staging run>)"
    return (f":rocket: *Release {number.group(1)} is ready for approval:* <{url}|{plain(title)}>\n"
            f"• *What goes up:* {plain(payload.get('goes_up')) or 'see the PR'}\n"
            f"• *What was tested:* {tested}\n"
            "*To release:* open the PR, then *Files changed → Review changes → Approve*. One approval from David, Moriel or "
            "Ran merges it, and production deploys by itself. The customer release stays manual.")


def main() -> int:
    try:
        text = render(json.loads(os.environ.get("PAYLOAD") or "{}"))
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"::error title=notify-dev::{exc}")
        return 1
    posted = slack("chat.postMessage", {"channel": DEV_CHANNEL, "text": text, "unfurl_links": False})
    if not posted:
        print("::error title=notify-dev::Slack did not take the notice (is Release Manager still in #dev?)")
        return 1
    print(f"posted to #dev at {posted.get('ts')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
