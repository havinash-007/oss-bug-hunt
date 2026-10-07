"""Watch tracked pull requests for new feedback and prepare replies.

For every PR in prs.json this reports, once per event:

* NEW_COMMENT      a comment or inline review comment from a human
* CHANGES          a review that requests changes
* CI_FAILED        one or more failing checks
* MERGED / CLOSED  the PR reached a final state (score +1 / -1)

Events are remembered in .pr_watch_state.json so each is reported once.
With --draft, a reply skeleton is written to replies/ for each human event.
Posting is always explicit: review the draft, then run
`python3 tools/pr_watch.py --post replies/<file>.md`.

Requires the GitHub CLI (`gh`), authenticated.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".pr_watch_state.json"
REPLIES = ROOT / "replies"
ME = "havinash-007"
BOT_RE = re.compile(r"(\[bot\]$|bot$|^codspeed|^cubic|^qodo|^vercel|^socket|^github-actions|^dependabot|^renovate)", re.I)
FAILING = {"FAILURE", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED"}


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def is_human(login: str | None) -> bool:
    return bool(login) and login != ME and not BOT_RE.search(login)


def load_state() -> dict:
    return json.loads(STATE.read_text()) if STATE.exists() else {}


def collect(repo: str, number: int) -> dict:
    """Fetch PR state, reviews, comments, inline comments and failing checks."""
    info = json.loads(
        gh("pr", "view", str(number), "-R", repo, "--json",
           "state,mergedAt,title,url,reviews,comments,statusCheckRollup")
    )
    inline = json.loads(gh("api", f"repos/{repo}/pulls/{number}/comments", "--paginate") or "[]")
    return {"info": info, "inline": inline}


def events_for(repo: str, number: int, data: dict) -> list[dict]:
    """Turn raw PR data into a list of events with stable ids."""
    info, out = data["info"], []
    key = f"{repo}#{number}"

    if info["mergedAt"]:
        out.append({"id": f"{key}:merged", "kind": "MERGED", "key": key, "text": "merged (+1)"})
    elif info["state"] == "CLOSED":
        out.append({"id": f"{key}:closed", "kind": "CLOSED", "key": key, "text": "closed without merge (-1)"})

    for c in info["comments"]:
        who = (c.get("author") or {}).get("login")
        if is_human(who):
            out.append({"id": f"{key}:c:{c['id']}", "kind": "NEW_COMMENT", "key": key,
                        "who": who, "text": c["body"]})
    for r in info["reviews"]:
        who = (r.get("author") or {}).get("login")
        if not is_human(who):
            continue
        kind = "CHANGES" if r["state"] == "CHANGES_REQUESTED" else "NEW_COMMENT"
        if r["state"] == "CHANGES_REQUESTED" or r["body"].strip():
            out.append({"id": f"{key}:r:{r['id']}", "kind": kind, "key": key,
                        "who": who, "text": r["body"] or f"({r['state']})"})
    for c in data["inline"]:
        who = c["user"]["login"]
        if is_human(who):
            out.append({"id": f"{key}:i:{c['id']}", "kind": "NEW_COMMENT", "key": key,
                        "who": who, "text": f"{c['path']}: {c['body']}"})

    failed = sorted({
        x.get("name") or x.get("context") or "?"
        for x in info["statusCheckRollup"] or []
        if (x.get("conclusion") or x.get("state")) in FAILING
    })
    if failed:
        out.append({"id": f"{key}:ci:{','.join(failed)}", "kind": "CI_FAILED", "key": key,
                    "text": "failing: " + ", ".join(failed)})
    return out


def write_draft(ev: dict, pr_url: str) -> Path:
    """Write a reply skeleton for a human event. The reply itself is written by a person."""
    REPLIES.mkdir(exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", ev["id"]).strip("_")
    path = REPLIES / f"{safe}.md"
    quoted = "\n".join("> " + line for line in ev["text"].splitlines()[:12])
    path.write_text(
        f"<!-- target: {ev['key']} | {pr_url} -->\n"
        f"<!-- {ev['who']} wrote: -->\n{quoted}\n\n"
        "<!-- Write the reply below this line, delete these comments, then post with --post -->\n"
    )
    return path


def post(path: Path) -> None:
    """Post a reviewed reply file as a PR comment (target is read from its first line)."""
    text = path.read_text()
    m = re.match(r"<!-- target: (\S+)#(\d+) ", text)
    if not m:
        sys.exit("no '<!-- target: repo#number | url -->' header found")
    body = re.sub(r"<!--.*?-->\n?", "", text, flags=re.S)
    body = "\n".join(line for line in body.splitlines() if not line.startswith(">")).strip()
    if not body:
        sys.exit("reply is empty: write your reply in the file first")
    gh("pr", "comment", m.group(2), "-R", m.group(1), "--body", body)
    print(f"posted to {m.group(1)}#{m.group(2)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prs", default=str(ROOT / "prs.json"))
    ap.add_argument("--draft", action="store_true", help="write reply skeletons for human events")
    ap.add_argument("--baseline", action="store_true", help="mark all current events as seen")
    ap.add_argument("--post", metavar="FILE", help="post a reviewed reply file and exit")
    args = ap.parse_args()

    if args.post:
        return post(Path(args.post))

    state, new_total = load_state(), 0
    for p in json.loads(Path(args.prs).read_text()):
        repo, number = p["repo"], p["number"]
        data = collect(repo, number)
        for ev in events_for(repo, number, data):
            if ev["id"] in state:
                continue
            state[ev["id"]] = True
            if args.baseline:
                continue
            new_total += 1
            who = f" {ev['who']}" if ev.get("who") else ""
            print(f"[{ev['kind']}] {ev['key']}{who}: {ev['text'][:200]!r}")
            if args.draft and ev["kind"] in {"NEW_COMMENT", "CHANGES"}:
                print(f"    draft: {write_draft(ev, data['info']['url'])}")
    STATE.write_text(json.dumps(state, indent=1))
    print("baseline saved" if args.baseline else f"{new_total} new event(s)")


if __name__ == "__main__":
    main()
