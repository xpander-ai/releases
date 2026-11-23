import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".github", "scripts"))
import notify_dev as nd  # noqa: E402

GOOD = {"pr_url": "https://github.com/xpander-ai/xpander/pull/340", "title": "Release 13: develop to main (#330 fix x)",
        "goes_up": "2 changes: #330 fix x, #331 add y", "tested": "staging deploy + smoke tests on abcdef1234",
        "proof_url": "https://github.com/xpander-ai/xpander/actions/runs/45100000000"}


def test_renders_ready_goes_up_tested_and_how_to_approve():
    text = nd.render(GOOD)
    assert text.startswith(":rocket: *Release 13 is ready for approval:* <https://github.com/xpander-ai/xpander/pull/340|")
    assert "*What goes up:* 2 changes: #330 fix x, #331 add y" in text
    assert "*What was tested:* staging deploy + smoke tests on abcdef1234 (<https://github.com/xpander-ai/xpander/actions/runs/45100000000|staging run>)" in text
    assert "One approval from David, Moriel or Ran" in text


@pytest.mark.parametrize("field,value", [
    ("pr_url", "https://github.com/xpander-ai/other/pull/1"), ("pr_url", "https://evil.example/pull/1"),
    ("title", "Hotfix: anything"), ("proof_url", "https://github.com/xpander-ai/xpander/actions/runs/1/x"),
])
def test_refuses_a_payload_that_is_not_a_release_pr(field, value):
    with pytest.raises(ValueError):
        nd.render({**GOOD, field: value})


def test_escapes_mentions_and_links_and_flattens_lines():
    text = nd.render({**GOOD, "goes_up": "<!channel> <https://x.example|click>\nline two", "tested": "a & b"})
    assert "<!channel>" not in text and "&lt;!channel&gt;" in text and "&lt;https://x.example|click&gt; line two" in text
    assert "a &amp; b" in text


def test_main_posts_to_dev_and_fails_loudly(monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(nd, "slack", lambda method, payload: sent.append((method, payload)) or {"ok": True, "ts": "1.2"})
    monkeypatch.setenv("PAYLOAD", json.dumps(GOOD))
    assert nd.main() == 0 and sent[0][0] == "chat.postMessage" and sent[0][1]["channel"] == "C0617LQBDMF"
    monkeypatch.setattr(nd, "slack", lambda method, payload: None)
    assert nd.main() == 1 and "did not take" in capsys.readouterr().out
    monkeypatch.setenv("PAYLOAD", json.dumps({**GOOD, "title": "x"}))
    assert nd.main() == 1
