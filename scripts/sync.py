#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

Row = dict[str, Any]
REPO_ROOT = Path(__file__).resolve().parent.parent

# Public content gates are fail-closed: unknown database values never reach Hugo.
PROJECT_CATEGORIES = frozenset({"Labs", "Eventos"})
PUBLICATION_MACRO_TYPES = frozenset({"Artigos em revistas", "Livros"})

WHITELISTS = {
    "people": frozenset(
        {
            "id", "slug", "preferred_name", "bio", "photo_url", "membership_type",
            "status", "orcid", "ciencia_id", "phd", "integration_year", "roles",
            "publications", "projects", "labs",
        }
    ),
    "projects": frozenset(
        {
            "id", "slug", "title", "acronym", "description", "status", "start_date",
            "end_date", "funding", "category", "members", "clusters", "labs",
            "objectives",
        }
    ),
    "publications": frozenset(
        {
            "id", "title", "year", "type", "macro_type", "doi", "url",
            "full_reference", "authors",
        }
    ),
    "clusters": frozenset(
        {"id", "slug", "code", "name", "concern", "projects", "objectives"}
    ),
    "labs": frozenset(
        {"id", "slug", "code", "name", "overview", "members", "projects", "objectives"}
    ),
    "objectives": frozenset(
        {"id", "slug", "code", "name", "description", "clusters", "labs", "projects"}
    ),
}

SELECTS = {
    "people": (
        "id,preferred_name,bio,photo_url,membership_type,status,orcid,ciencia_id,"
        "phd,integration_year,profile_status,public_visibility,merged_into,featured_outputs"
    ),
    "projects": (
        "id,title,acronym,description,status,start_date,end_date,funding,category,"
        "approval_status,public_visibility"
    ),
    "outputs": (
        "id,title,reporting_year,type,macro_type,doi,url,full_reference,"
        "approval_status,merged_into"
    ),
    "clusters": "id,code,name,concern",
    "labs": "id,code,name,overview",
    "objectives": "id,code,name,description",
    # status is fetched only to gate on it — it is stripped before write, see
    # the person_roles loop. The service key bypasses RLS, so pr_read's
    # "status = 'approved'" gate never applies to this query.
    "person_roles": "person_id,kind,label,year,status",
    "output_authors": "output_id,person_id,role,author_position",
    "project_members": "project_id,person_id,role",
    "lab_members": "lab_id,person_id,is_coordinator",
    "project_clusters": "project_id,cluster_id",
    "project_labs": "project_id,lab_id",
    "project_objectives": "project_id,objective_id",
    "objective_clusters": "cluster_id,objective_id",
    "lab_objectives": "lab_id,objective_id",
}


def pick(row: Mapping[str, Any], keys: Iterable[str]) -> Row:
    return {key: row.get(key) for key in keys}


def slugify(value: Any, fallback: Any = "") -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:80].rstrip("-")
    return slug or str(fallback)[:8]


def assign_slugs(
    rows: Sequence[Mapping[str, Any]], source_key: str, *, warn: bool = True
) -> dict[Any, str]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[slugify(row.get(source_key), row["id"])].append(row)

    result: dict[Any, str] = {}
    for base, colliding in groups.items():
        for number, row in enumerate(sorted(colliding, key=lambda item: str(item["id"])), 1):
            slug = base if number == 1 else f"{base}-{number}"
            result[row["id"]] = slug
            if number > 1 and warn:
                print(
                    f"slug collision: {base!r}, {row['id']} assigned {slug!r}",
                    file=sys.stderr,
                )
    return result


def project_passes(row: Mapping[str, Any], preview: bool) -> bool:
    approved = preview or (
        row.get("approval_status") == "approved"
        and row.get("public_visibility") is True
    )
    return approved and row.get("category") in PROJECT_CATEGORIES


def person_passes(row: Mapping[str, Any], preview: bool) -> bool:
    return row.get("merged_into") is None and (
        preview
        or (
            row.get("profile_status") == "approved"
            and row.get("public_visibility") is True
        )
    )


def publication_passes(row: Mapping[str, Any], preview: bool) -> bool:
    approved = preview or row.get("approval_status") == "approved"
    return (
        row.get("merged_into") is None
        and approved
        and row.get("macro_type") in PUBLICATION_MACRO_TYPES
    )


def assert_whitelist(
    entity: str, records: Sequence[Mapping[str, Any]], allowed: frozenset[str]
) -> None:
    for record in records:
        stray = set(record) - allowed
        assert not stray, f"{entity} record {record.get('id')} has forbidden keys: {sorted(stray)}"


def grouped(rows: Sequence[Row], key: str) -> dict[Any, list[Row]]:
    result: dict[Any, list[Row]] = defaultdict(list)
    for row in rows:
        result[row.get(key)].append(row)
    return result


def text_key(value: Any) -> str:
    return str(value or "").casefold()


def publication_sort_key(row: Mapping[str, Any]) -> tuple[bool, int, str, str]:
    year = row.get("year")
    try:
        numeric_year = int(year)
    except (TypeError, ValueError):
        numeric_year = 0
    return year is None, -numeric_year, text_key(row.get("title")), str(row.get("id"))


def build(raw: Mapping[str, list[Row]], preview: bool) -> dict[str, list[Row]]:
    people_rows = [row for row in raw["people"] if person_passes(row, preview)]
    project_rows = [row for row in raw["projects"] if project_passes(row, preview)]
    publication_rows = [
        row for row in raw["outputs"] if publication_passes(row, preview)
    ]
    cluster_rows = raw["clusters"]
    lab_rows = raw["labs"]
    objective_rows = raw["objectives"]

    person_slugs = assign_slugs(people_rows, "preferred_name")
    project_slug_inputs = [
        {**pick(row, ("id", "title")), "slug_source": row.get("acronym") or row.get("title")}
        for row in project_rows
    ]
    project_slugs = assign_slugs(project_slug_inputs, "slug_source")
    cluster_slug_inputs = [
        {**pick(row, ("id", "name")), "slug_source": row.get("code") or row.get("name")}
        for row in cluster_rows
    ]
    cluster_slugs = assign_slugs(cluster_slug_inputs, "slug_source")
    lab_slug_inputs = [
        {**pick(row, ("id", "name")), "slug_source": row.get("code") or row.get("name")}
        for row in lab_rows
    ]
    lab_slugs = assign_slugs(lab_slug_inputs, "slug_source")
    objective_slug_inputs = [
        {**pick(row, ("id", "name")), "slug_source": row.get("code") or row.get("name")}
        for row in objective_rows
    ]
    objective_slugs = assign_slugs(objective_slug_inputs, "slug_source")

    people = []
    for row in people_rows:
        record = pick(row, WHITELISTS["people"] - {"slug", "roles", "publications", "projects", "labs"})
        record.update(
            slug=person_slugs[row["id"]], roles=[], publications=[], projects=[], labs=[]
        )
        people.append(record)

    projects = []
    for row in project_rows:
        record = pick(row, WHITELISTS["projects"] - {"slug", "members", "clusters", "labs", "objectives"})
        record.update(
            slug=project_slugs[row["id"]], members=[], clusters=[], labs=[], objectives=[]
        )
        projects.append(record)

    publications = []
    for row in publication_rows:
        record = pick(row, WHITELISTS["publications"] - {"year", "authors"})
        record.update(year=row.get("reporting_year"), authors=[])
        publications.append(record)

    clusters = []
    for row in cluster_rows:
        record = pick(row, WHITELISTS["clusters"] - {"slug", "projects", "objectives"})
        record.update(slug=cluster_slugs[row["id"]], projects=[], objectives=[])
        clusters.append(record)

    labs = []
    for row in lab_rows:
        record = pick(row, WHITELISTS["labs"] - {"slug", "members", "projects", "objectives"})
        record.update(slug=lab_slugs[row["id"]], members=[], projects=[], objectives=[])
        labs.append(record)

    objectives = []
    for row in objective_rows:
        record = pick(row, WHITELISTS["objectives"] - {"slug", "clusters", "labs", "projects"})
        record.update(
            slug=objective_slugs[row["id"]], clusters=[], labs=[], projects=[]
        )
        objectives.append(record)

    people_by_id = {row["id"]: row for row in people}
    projects_by_id = {row["id"]: row for row in projects}
    publications_by_id = {row["id"]: row for row in publications}
    clusters_by_id = {row["id"]: row for row in clusters}
    labs_by_id = {row["id"]: row for row in labs}
    objectives_by_id = {row["id"]: row for row in objectives}

    for join in raw["person_roles"]:
        # A researcher can type any role onto their own profile; the
        # protect_person_roles trigger forces it to 'pending' precisely so an
        # admin sees it first. Without this check the nightly run published it
        # anyway — someone could put "Director of UNIDCOM" on the institutional
        # website overnight. This is the only place the approval workflow was
        # bypassed.
        if join.get("status") != "approved":
            continue
        person = people_by_id.get(join.get("person_id"))
        if person:
            person["roles"].append(pick(join, ("kind", "label", "year")))
    for person in people:
        person["roles"].sort(
            key=lambda row: (
                text_key(row["kind"]),
                text_key(row["label"]),
                text_key(row["year"]),
            )
        )

    authors_by_person = grouped(raw["output_authors"], "person_id")
    featured = {row["id"]: row.get("featured_outputs") or [] for row in people_rows}
    for person in people:
        linked = []
        for join in authors_by_person.get(person["id"], []):
            publication = publications_by_id.get(join.get("output_id"))
            if publication:
                linked.append(
                    {
                        **pick(publication, ("id", "title", "year", "doi", "url")),
                        **pick(join, ("role", "author_position")),
                    }
                )
        featured_order = {
            output_id: position
            for position, output_id in enumerate(featured[person["id"]])
        }
        person["publications"] = sorted(
            linked,
            key=lambda row: (
                0,
                featured_order[row["id"]],
            )
            if row["id"] in featured_order
            else (1, publication_sort_key(row)),
        )

    project_members = grouped(raw["project_members"], "project_id")
    projects_by_person = grouped(raw["project_members"], "person_id")
    role_rank = {"pi": 0, "responsible": 1, "member": 2}
    for project in projects:
        for join in project_members.get(project["id"], []):
            person = people_by_id.get(join.get("person_id"))
            if person:
                project["members"].append(
                    {"slug": person["slug"], "name": person["preferred_name"], "role": join.get("role")}
                )
        project["members"].sort(
            key=lambda row: (
                role_rank.get(str(row["role"] or "").lower(), 3),
                text_key(row["name"]),
                text_key(row["slug"]),
            )
        )
    for person in people:
        for join in projects_by_person.get(person["id"], []):
            project = projects_by_id.get(join.get("project_id"))
            if project:
                person["projects"].append(
                    {"slug": project["slug"], "title": project["title"], "role": join.get("role")}
                )
        person["projects"].sort(
            key=lambda row: (text_key(row["title"]), text_key(row["slug"]))
        )

    lab_members = grouped(raw["lab_members"], "lab_id")
    labs_by_person = grouped(raw["lab_members"], "person_id")
    for lab in labs:
        for join in lab_members.get(lab["id"], []):
            person = people_by_id.get(join.get("person_id"))
            if person:
                lab["members"].append(
                    {"slug": person["slug"], "name": person["preferred_name"]}
                )
        lab["members"].sort(
            key=lambda row: (text_key(row["name"]), text_key(row["slug"]))
        )
    for person in people:
        for join in labs_by_person.get(person["id"], []):
            lab = labs_by_id.get(join.get("lab_id"))
            if lab:
                person["labs"].append(
                    {
                        "slug": lab["slug"],
                        "name": lab["name"],
                        "is_coordinator": join.get("is_coordinator"),
                    }
                )
        person["labs"].sort(
            key=lambda row: (text_key(row["name"]), text_key(row["slug"]))
        )

    for join in raw["output_authors"]:
        publication = publications_by_id.get(join.get("output_id"))
        person = people_by_id.get(join.get("person_id"))
        if publication and person:
            publication["authors"].append(
                {
                    "slug": person["slug"],
                    "name": person["preferred_name"],
                    **pick(join, ("role", "author_position")),
                }
            )
    for publication in publications:
        publication["authors"].sort(
            key=lambda row: (
                row["author_position"] is None,
                row["author_position"] if row["author_position"] is not None else 0,
                text_key(row["name"]),
                text_key(row["slug"]),
            )
        )

    relationships = (
        ("project_clusters", projects_by_id, clusters_by_id, "project_id", "cluster_id", "clusters", "projects", "title"),
        ("project_labs", projects_by_id, labs_by_id, "project_id", "lab_id", "labs", "projects", "title"),
        ("project_objectives", projects_by_id, objectives_by_id, "project_id", "objective_id", "objectives", "projects", "title"),
        ("objective_clusters", clusters_by_id, objectives_by_id, "cluster_id", "objective_id", "objectives", "clusters", "name"),
        ("lab_objectives", labs_by_id, objectives_by_id, "lab_id", "objective_id", "objectives", "labs", "name"),
    )
    for table, left_index, right_index, left_key, right_key, left_field, right_field, left_label in relationships:
        for join in raw[table]:
            left = left_index.get(join.get(left_key))
            right = right_index.get(join.get(right_key))
            if left and right:
                left[left_field].append({"slug": right["slug"], "name": right["name"]})
                right[right_field].append(
                    {"slug": left["slug"], left_label: left[left_label]}
                )

    for records in (projects, clusters, labs, objectives):
        for record in records:
            for field in ("clusters", "labs", "objectives", "projects"):
                if field in record:
                    label = "title" if field == "projects" else "name"
                    record[field].sort(
                        key=lambda row: (text_key(row[label]), text_key(row["slug"]))
                    )

    return {
        "people": sorted(people, key=lambda row: (text_key(row["slug"]), str(row["id"]))),
        "projects": sorted(projects, key=lambda row: (text_key(row["slug"]), str(row["id"]))),
        "publications": sorted(publications, key=publication_sort_key),
        "clusters": sorted(clusters, key=lambda row: (text_key(row["slug"]), str(row["id"]))),
        "labs": sorted(labs, key=lambda row: (text_key(row["slug"]), str(row["id"]))),
        "objectives": sorted(objectives, key=lambda row: (text_key(row["slug"]), str(row["id"]))),
    }


def fetch_all(url: str, key: str) -> dict[str, list[Row]]:
    from supabase import create_client

    client = create_client(url, key)
    result = {}
    for table, columns in SELECTS.items():
        rows = client.table(table).select(columns).execute().data or []
        assert len(rows) != 1000, f"{table} returned exactly 1000 rows; possible PostgREST truncation"
        result[table] = rows
    return result


def write_json(path: Path, value: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


# Fixtures for the self-check: an empty raw payload with every key build()
# reads, and one person who passes the publish gate.
_EMPTY_RAW: dict[str, list[Row]] = {
    "people": [], "projects": [], "outputs": [], "clusters": [], "labs": [],
    "objectives": [], "person_roles": [], "output_authors": [],
    "project_members": [], "lab_members": [], "project_clusters": [],
    "project_labs": [], "project_objectives": [], "objective_clusters": [],
    "lab_objectives": [],
}
_SELF_CHECK_PERSON: Row = {
    "id": "p1", "preferred_name": "Test Person", "merged_into": None,
    "profile_status": "approved", "public_visibility": True,
}


def self_check() -> None:
    assert slugify("João, D'Ávila!") == "joao-d-avila"
    assert slugify("!!!", "123456789") == "12345678"
    assert slugify("a" * 100) == "a" * 80
    rows = [{"id": "b", "name": "Same"}, {"id": "a", "name": "Same"}]
    expected = {"a": "same", "b": "same-2"}
    assert assign_slugs(rows, "name", warn=False) == expected
    assert assign_slugs(list(reversed(rows)), "name", warn=False) == expected
    assert pick({"public": 1, "private": 2}, ("public",)) == {"public": 1}
    try:
        assert_whitelist("test", [{"id": "1", "stray": True}], frozenset({"id"}))
    except AssertionError:
        pass
    else:
        raise AssertionError("whitelist assertion accepted a stray key")
    assert not project_passes(
        {"approval_status": "approved", "public_visibility": True, "category": "Operação"},
        preview=True,
    )

    # An unapproved role must never reach the site — see the person_roles loop.
    assert build(
        {**_EMPTY_RAW, "people": [_SELF_CHECK_PERSON], "person_roles": [
            {"person_id": "p1", "kind": "role", "label": "Director", "year": 2026,
             "status": "pending"},
        ]},
        preview=True,
    )["people"][0]["roles"] == []
    assert build(
        {**_EMPTY_RAW, "people": [_SELF_CHECK_PERSON], "person_roles": [
            {"person_id": "p1", "kind": "role", "label": "Researcher", "year": 2026,
             "status": "approved"},
        ]},
        preview=True,
    )["people"][0]["roles"] == [{"kind": "role", "label": "Researcher", "year": 2026}]

    # Collapse guard: growth is fine, a >20% drop is not.
    assert check_no_collapse({"people": 183}, {"people": 184}) == []
    assert check_no_collapse({"people": 300}, {"people": 184}) == []
    assert check_no_collapse({"people": 10}, {"people": 184}) == ["people: 184 -> 10"]
    assert check_no_collapse({"people": 0}, {"people": 184}) == ["people: 184 -> 0"]
    assert check_no_collapse({"people": 5}, {}) == []

    print("self-check passed")


def check_no_collapse(
    counts: Mapping[str, int], previous: Mapping[str, int], tolerance: float = 0.2
) -> list[str]:
    """Entity counts that fell by more than `tolerance` since the last run.

    The nightly sync commits and deploys without a human in the loop, so a
    change that silently empties an entity — a bad approval sweep, a renamed
    column, a partial fetch — would publish a near-empty site and nobody would
    know until a researcher noticed their page was gone. Growth is never
    suspicious; only collapse is.
    """
    return [
        f"{name}: {previous[name]} -> {count}"
        for name, count in sorted(counts.items())
        if (was := previous.get(name, 0)) and count < was * (1 - tolerance)
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument(
        "--allow-collapse",
        action="store_true",
        help="write even if an entity count dropped >20%% (use after a deliberate purge)",
    )
    parser.add_argument("--out", default="data/generated")
    args = parser.parse_args()

    if args.self_check:
        self_check()
        return

    missing = [
        name for name in ("SUPABASE_URL", "SUPABASE_SERVICE_KEY") if not os.environ.get(name)
    ]
    if missing:
        parser.error(f"missing required environment variable(s): {', '.join(missing)}")

    raw = fetch_all(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    entities = build(raw, args.preview)
    counts = {name: len(records) for name, records in entities.items()}
    print("  ".join(f"{name} {count}" for name, count in counts.items()))
    if args.dry_run:
        return

    out = Path(args.out)
    if not out.is_absolute():
        out = REPO_ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    meta_path = out / "_meta.json"
    if meta_path.exists() and not args.allow_collapse:
        previous = json.loads(meta_path.read_text()).get("counts", {})
        # Preview and production select different sets, so comparing across a
        # mode switch is meaningless — the 2026-08-06 go-live legitimately
        # dropped one person.
        if previous and json.loads(meta_path.read_text()).get("preview") == args.preview:
            collapsed = check_no_collapse(counts, previous)
            if collapsed:
                raise SystemExit(
                    "refusing to write: entity counts collapsed since the last run\n  "
                    + "\n  ".join(collapsed)
                    + "\nRe-run with --allow-collapse if this is a deliberate purge."
                )

    for entity, records in entities.items():
        assert_whitelist(entity, records, WHITELISTS[entity])
        write_json(out / f"{entity}.json", records)
    write_json(
        out / "_meta.json",
        {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "preview": args.preview,
            "counts": counts,
        },
    )


if __name__ == "__main__":
    main()
