# unidcom-site

Public website for UNIDCOM/IADE. Hugo static site, generated from the UNIDCOM research
database — the same Supabase project the [Unidcom-IADE](https://github.com/berlogabob/Unidcom-IADE)
Flutter admin app curates.

**Live:** https://berlogabob.github.io/unidcom-site/ — currently a **preview build**
(see [Preview mode](#preview-mode)).

Intended to replace the WordPress site at [unidcom-iade.pt](https://www.unidcom-iade.pt/).

---

## How it works

```
Supabase                    scripts/sync.py            Hugo                GitHub Pages
(source of truth)  ───────► data/generated/*.json ───► content adapters ─► static HTML
                            (committed to git)         + themes/unidcom
```

Three things follow from that shape, and they explain most of what feels unusual here:

- **The site never talks to the database.** The generated JSON is committed, so a deploy
  needs no credentials and a build is reproducible from the repo alone.
- **No Markdown is generated.** Hugo builds a page per person, project, cluster, lab and
  objective directly from the JSON, via content adapters (`content/*/_content.gotmpl`).
  There are no hundreds of stub files to review.
- **Data changes are commits.** The nightly sync commits to `data/generated/`, so every
  content change is visible in `git log` and revertible.

---

## Where to change what

This is the part worth reading. **Almost nothing about people, projects or publications is
edited in this repo.**

| To change | Edit | Appears after |
|---|---|---|
| A researcher's name, bio, photo, ORCID, roles | **Flutter admin app** → Supabase | next sync |
| A project's title, dates, funding, members | **Flutter admin app** → Supabase | next sync |
| A publication, or who authored it | **Flutter admin app** → Supabase | next sync |
| Clusters, labs, objectives | **Flutter admin app** → Supabase | next sync |
| An event / conference / DRIW page | `content/events/*.md` **here** | next push |
| About, Vision & Mission, Ethics, Contact, Opportunities | `content/*.md` **here** | next push |
| Section intro text (e.g. the blurb above the people list) | `content/<section>/_index.md` | next push |
| Navigation menu | `hugo.toml` → `[[menu.main]]` | next push |
| Colours, type, spacing | `themes/unidcom/assets/css/tokens.css` | next push |

Events are Markdown rather than database rows because there is no `events` table — the old
site's Agenda, Conferences and DRIW pages have no home in Supabase. If events become
frequent enough to hurt, that is the signal to add the table.

### Adding an event

Create `content/events/my-event.md`:

```yaml
---
title: "Design Research and Innovation Week 2027"
date: 2027-05-04T09:00:00+00:00      # start; a future date makes it "upcoming"
end_date: 2027-05-08T18:00:00+00:00
event_type: "Conference"             # Conference | Workshop | Seminar | …
venue: "IADE"
city: "Lisboa"
registration_url: "https://…"        # optional, leave "" if none
summary: "One sentence for the listing."
draft: false
---

Body copy in Markdown.
```

Upcoming events sort to the top of `/events/` and carry the signal colour. Past events group
by year below.

---

## Refreshing content from the database

Automatic: `.github/workflows/sync.yml` runs nightly at 04:00 UTC and commits any changes.

Manually, from the repo:

```sh
export SUPABASE_URL=…  SUPABASE_SERVICE_KEY=…
uv run --project scripts scripts/sync.py --preview
```

Useful flags:

```sh
--dry-run      # print the counts, write nothing
--preview      # bypass the approval gate (see below)
--self-check   # run the built-in tests, no database access
```

It prints a one-line summary you can sanity-check against the admin app:

```
people 184  projects 25  publications 76  clusters 5  labs 5  objectives 12
```

Or trigger the workflow from GitHub: **Actions → Sync content from Supabase → Run workflow**.

---

## Why isn't my record on the site?

Every record passes **two independent gates**. Almost every "it's in the database but not on
the site" question is one of these.

### Gate 1 — approval

Respects the curation state set in the admin app:

- people: `profile_status = 'approved'` **and** `public_visibility = true`
- projects: `approval_status = 'approved'` **and** `public_visibility = true`
- publications: `approval_status = 'approved'`

`--preview` bypasses this gate entirely.

### Gate 2 — content type

**Never bypassed, not even by `--preview`.** The database doubles as UNIDCOM's internal FCT
reporting tool, so it holds rows that must not appear on a public website whatever their
approval state — thesis-jury records naming students, internal governance planning, and so
on.

- **projects** ship only when `category` is `Labs` or `Eventos`. This excludes `Operação`
  and `Estratégia` rows such as `FCT Report | Outputs | BD + narrativa`.
- **publications** ship only when `macro_type` is `Artigos em revistas` or `Livros`. Of 361
  `outputs` rows, 76 qualify; the other 285 are activity records, not publications.

Both allowlists are **fail-closed** — a category nobody has seen before is excluded, not
included. If a legitimately public category is added in the admin app, add it to
`PROJECT_CATEGORIES` or `PUBLICATION_MACRO_TYPES` in `scripts/sync.py`.

### Field whitelists

Row-level security on the Supabase project is currently open for the review period, so
**`scripts/sync.py` — not the database — is the privacy boundary.** Every record is built by
explicit `pick()`, and a write-time assertion fails the run if a record carries a key outside
its declared whitelist. `email`, `legal_name`, `auth_user_id`, `notes`, `total_budget` and
`risk` are never even fetched.

Adding a field to the site means adding it in three places in `sync.py`: the `SELECTS` query,
the `WHITELISTS` set, and the template that renders it.

---

## Preview mode

Nothing in the database is approved yet, so the site runs with `--preview`: the approval gate
is off and the whole site is marked not-for-indexing.

When `data/generated/_meta.json` has `"preview": true`:

- every page emits `<meta name="robots" content="noindex, nofollow">`
- `robots.txt` emits `Disallow: /`
- a black banner reads *Preview build — content is unapproved and not indexed*

`noindex` keeps the site out of search engines. It does **not** make the site private — the
pages are on the public internet and anyone with the URL can read them.

**To go live properly**, set `preview: false` on the workflow input (or drop `--preview`
locally), and confirm the counts don't collapse to near-zero — that means curation isn't done.

---

## Local development

Needs [Hugo extended](https://gohugo.io/installation/) ≥ 0.164 and [uv](https://docs.astral.sh/uv/).

```sh
hugo server              # http://localhost:1313/unidcom-site/
hugo --gc                # one-off build into public/
```

Before pushing anything structural:

```sh
hugo --gc --printPathWarnings                  # no ERROR, no duplicate paths
uv run --project scripts scripts/sync.py --self-check
```

---

## Theme

`themes/unidcom/` — hand-written CSS, no framework, no build step beyond Hugo Pipes.

The design comes from the UNIDCOM mark: a monogram inside a square. Collections render as an
edge-to-edge **lattice** whose cells share one continuous black line, built with the gap
trick so there is no double-border arithmetic:

```css
.lattice { display: grid; gap: 1px; background: var(--ink); border: 1px solid var(--ink); }
.lattice > * { background: var(--paper); }
```

Cell inversion on hover and focus is the theme's entire accent system. **`--signal`
(`#ff3b0f`) is reserved for temporal state** — an upcoming event, an active project — so
colour on this site always means *this is live now*. Don't spend it on decoration.

Type is one variable superfamily (Archivo, self-hosted in `static/fonts/`) used as two
voices via its width axis: expanded and heavy for display, normal for body, condensed for
utility labels.

CSS loads in order: `tokens → base → typography → layout → components`. Start at
`tokens.css`.

### Slugs and URLs

There is no `slug` column in the database. Slugs are derived in `sync.py` from
`preferred_name` / `acronym` / `code`, deduplicated deterministically, and written into the
committed JSON — so **renaming a person in the admin app shows up as a URL change in a diff**
rather than silently breaking links. Old WordPress URLs redirect via Hugo `aliases`.

---

## Deploying

Push to `main`. `.github/workflows/deploy.yml` builds and publishes to GitHub Pages; it needs
no secrets.

`baseURL` in `hugo.toml` carries the `/unidcom-site/` subpath, so **never hardcode a
root-relative path** in a template — use `.RelPermalink`, `relURL` or `resources.Get`, or
assets will 404.

### Attaching a custom domain

1. Add `static/CNAME` containing the hostname, e.g. `unidcom-iade.pt`.
2. Set `baseURL` in `hugo.toml` to match.
3. DNS: `CNAME → berlogabob.github.io` for a subdomain, or A records to
   `185.199.108.153`, `.109.153`, `.110.153`, `.111.153` for an apex domain.

GitHub issues the certificate. **One custom domain per repository** — a `beta.` staging
domain and an apex cutover are mutually exclusive.

---

## Known gaps

- **Photos and bios.** 0 of 184 people have a photo and 1 has a bio in the database, so
  person pages fall back to initials. The old WordPress site has both, at
  `/centre/people/{slug}/`; migrating them into Supabase is unstarted.
- **Portuguese labels on an English site.** Real data, not a bug: `funding: "Outro"`, author
  roles like `"Único autor"`, objective names like `"UNID.2: Inter e transdisciplinaridade"`.
  The recurring ones want a label map in the theme; the objective names want editing in the
  admin app.
- **No per-publication pages.** Publications are bibliography entries linking out to their
  DOI. Add detail pages when there is an abstract or PDF to put on them.
- **No search.** Deferred until the filters prove insufficient.
- **English only.** The old site has a Portuguese side; Hugo multilingual is not set up.

## Repository layout

```
content/            editorial Markdown + content adapters (_content.gotmpl)
data/generated/     committed output of sync.py — do not hand-edit
scripts/sync.py     Supabase → JSON, and the project's privacy boundary
themes/unidcom/     layouts, CSS, JS
static/             wordmark, self-hosted fonts
.github/workflows/  sync.yml (nightly, commits) · deploy.yml (on push)
```
