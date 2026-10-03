"""
Dry run the clue chain before it costs anything.

This is not the authority on whether a clue works - `pin_clue` on chain is, and
it is the only thing that can be, because the digest depends on what GenVM's
renderer makes of a page rather than on what this script's HTTP client makes of
it. What this catches is the cheap class of mistakes: an anchor that is not on
the page at all, a window that runs off the end before reaching the material, an
answer that does not match its own pattern, an anchor that gives the answer away.

Catching those here costs nothing. Catching them on chain costs a transaction
each, and catching them after a race has opened costs the race.

    python3 scripts/dryrun_clues.py clues/race-01.json

Needs ordinary outbound network access.
"""

import json
import re
import sys
import urllib.request

sys.path.insert(0, "contracts")

# The canonicalisation below is duplicated from the contract on purpose.
# Intelligent Contracts are single files, so the contract cannot import a shared
# module, and a shared module here that the contract does not use would be a lie
# about what runs on chain. The duplication is checked by test_canon_parity.
_WS = re.compile(r"\s+")
_KEEP = re.compile(r"[^a-z0-9 .,;:!?'\"()\[\]{}<>/\\|@#$%&*+=~^`_-]")
MAX_PAGE_CHARS = 400000
MIN_WINDOW_CHARS = 200


def canonicalise(raw: str) -> str:
    if len(raw) > MAX_PAGE_CHARS:
        raw = raw[:MAX_PAGE_CHARS]
    out = raw.lower()
    out = _WS.sub(" ", out)
    out = _KEEP.sub("", out)
    return out.strip()


def cut_window(canon: str, anchor: str, window_chars: int) -> str:
    if anchor == "":
        return canon[:window_chars]
    at = canon.find(anchor.lower())
    if at < 0:
        return ""
    return canon[at : at + window_chars]


def normalise_answer(answer: str) -> str:
    out = answer.strip().lower()
    out = _WS.sub(" ", out)
    return out


def strip_tags(html: str) -> str:
    """
    A crude stand-in for the renderer's text mode.

    It will not agree with GenVM character for character and is not meant to.
    It only has to be close enough that "is the anchor on this page" and "does
    the window reach the material" give the right answers.
    """
    html = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<!--.*?-->", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    for ent, ch in (
        ("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&rsquo;", "'"), ("&lsquo;", "'"),
        ("&ldquo;", '"'), ("&rdquo;", '"'), ("&mdash;", "-"), ("&ndash;", "-"),
    ):
        html = html.replace(ent, ch)
    return html


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "proof-of-hunt-dryrun/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read().decode("utf-8", errors="replace")
    if "<" in body[:2000] and ">" in body[:2000]:
        body = strip_tags(body)
    return body


def report(ok, label, detail=""):
    mark = "ok  " if ok else "FAIL"
    line = f"  {mark} {label}"
    if detail:
        line += f"  ({detail})"
    print(line)
    return ok


def main(path):
    with open(path, encoding="utf-8") as source:
        spec = json.load(source)
    failures = 0

    for i, c in enumerate(spec["clues"]):
        print(f"\n[{i:02d}] {c['title']}")
        good = True

        expected = c.get("expected", "")
        norm_expected = normalise_answer(expected)

        # The answer must satisfy its own pattern. A clue that rejects its own
        # answer is unwinnable and there is no reason to discover that on chain.
        if expected:
            good &= report(
                re.fullmatch(c["answer_pattern"], norm_expected) is not None,
                "the expected answer matches the answer pattern",
                f"{norm_expected!r} vs /{c['answer_pattern']}/",
            )

        # An anchor is public. One that contains the answer is a giveaway.
        anchor = c["anchor"].lower()
        if norm_expected:
            good &= report(
                norm_expected not in anchor,
                "the anchor does not leak the answer",
            )

        try:
            raw = fetch(c["source_url"])
        except Exception as e:
            report(False, "source reachable", str(e)[:80])
            failures += 1
            continue
        report(True, "source reachable", f"{len(raw)} chars")

        canon = canonicalise(raw)
        good &= report(anchor in canon, "anchor found on the page", repr(anchor))

        window = cut_window(canon, anchor, int(c["window_chars"]))
        good &= report(
            len(window) >= MIN_WINDOW_CHARS,
            "window is long enough to judge against",
            f"{len(window)} chars",
        )

        # The window has to actually contain the material. If it does not, the
        # tribunal has been handed a passage that cannot settle the question and
        # every honest answer comes back UNDETERMINED.
        if norm_expected and window:
            good &= report(
                norm_expected in window
                or norm_expected.replace("-", "") in window.replace("-", ""),
                "the answer is inside the window",
            )

        # Anchor uniqueness. If the anchor appears more than once the window is
        # decided by which occurrence comes first, which is stable but easy to
        # get wrong when the page is edited.
        occurrences = canon.count(anchor)
        good &= report(
            occurrences == 1,
            "anchor is unique on the page",
            f"{occurrences} occurrence(s), the first is used",
        )

        if not good:
            failures += 1

    print()
    if failures:
        print(f"{failures} clue(s) need work before pinning")
        return 1
    print(f"all {len(spec['clues'])} clues look ready to pin")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "clues/race-01.json"))
