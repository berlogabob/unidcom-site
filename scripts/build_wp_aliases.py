#!/usr/bin/env python3
"""Build data/wp_aliases.json — old WordPress person URLs -> current slugs.

Run once, commit the output. The old unidcom-iade.pt site is frozen, so the map
does not change; this script exists so the file is reproducible and the
collision rule is written down rather than decided by hand.

    uv run --project scripts scripts/build_wp_aliases.py \
        --wp ../Unidcom-IADE/scripts/out/wp_profiles_review.json

The input is a scrape of the old site that lives in the sibling portal repo
under scripts/out/, which is gitignored (it carries names and photo URLs), so
this cannot run in CI. That is fine: the output is committed.

Why it matters: without these aliases every inbound link, citation and bookmark
to a researcher's page on the old site 404s after cutover. Slugs really did
move — amadeu-quelhas-martins -> amadeu-martins.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent


def old_path(url: str) -> str:
    """The path part of an old URL, normalised to a single trailing slash."""
    path = urlparse(url or "").path.strip("/")
    return f"/{path}/" if path else ""


def richness(person: dict) -> tuple:
    """How substantive a record is. Used only to break alias collisions.

    Two people can claim the same old URL when the old site had one page and
    the database still holds an unmerged duplicate — the two Saras. An alias is
    1:1, so one has to win, and it should be the record a visitor would rather
    land on: the one with an identity and a body of work.
    """
    return (
        bool((person.get("orcid") or "").strip()),
        len(person.get("publications") or []),
        len(person.get("projects") or []),
        len((person.get("bio") or "").strip()),
    )


def build(wp_rows: list[dict], people: list[dict]) -> tuple[dict, list[str]]:
    by_id = {p["id"]: p for p in people}
    claims: dict[str, list[dict]] = {}

    for row in wp_rows:
        person = by_id.get(row.get("person_id"))
        path = old_path(row.get("old_url", ""))
        if not person or not path:
            continue
        if path == f"/people/{person['slug']}/":
            continue  # already the live URL; an alias would collide with it
        claims.setdefault(path, []).append(person)

    aliases: dict[str, list[str]] = {}
    notes: list[str] = []
    for path, candidates in sorted(claims.items()):
        winner = max(candidates, key=richness)
        if len(candidates) > 1:
            losers = [c["slug"] for c in candidates if c is not winner]
            notes.append(f"{path}: kept {winner['slug']}, dropped {', '.join(losers)}")
        aliases.setdefault(winner["slug"], [])
        if path not in aliases[winner["slug"]]:
            aliases[winner["slug"]].append(path)

    return dict(sorted(aliases.items())), notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wp", required=True, help="wp_profiles_review.json")
    parser.add_argument("--people", default="data/generated/people.json")
    parser.add_argument("--out", default="data/wp_aliases.json")
    args = parser.parse_args()

    wp_rows = json.loads(Path(args.wp).read_text())
    people = json.loads((REPO_ROOT / args.people).read_text())
    aliases, notes = build(wp_rows, people)

    total = sum(len(v) for v in aliases.values())
    print(f"{len(wp_rows)} old profiles -> {total} aliases over {len(aliases)} people")
    for note in notes:
        print(f"  collision  {note}")

    out = REPO_ROOT / args.out
    out.write_text(json.dumps(aliases, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out.relative_to(REPO_ROOT)}")


def self_check() -> None:
    people = [
        {"id": "a", "slug": "rich", "orcid": "0000-0001", "publications": [1, 2], "bio": "x"},
        {"id": "b", "slug": "thin", "orcid": "", "publications": [], "bio": ""},
    ]
    wp = [
        {"person_id": "a", "old_url": "https://old/centre/people/shared/"},
        {"person_id": "b", "old_url": "https://old/centre/people/shared/"},
    ]
    aliases, notes = build(wp, people)
    assert aliases == {"rich": ["/centre/people/shared/"]}, aliases
    assert notes and "dropped thin" in notes[0], notes

    # An old URL identical to the live one must not become a self-alias.
    same = build(
        [{"person_id": "a", "old_url": "https://old/people/rich/"}], people
    )[0]
    assert same == {}, same
    print("self-check passed")


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        self_check()
    else:
        main()
