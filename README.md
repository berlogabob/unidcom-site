# unidcom-site

Public website for UNIDCOM/IADE. Hugo static site, generated from the UNIDCOM research
database — the same Supabase project the [Unidcom-IADE](https://github.com/berlogabob/Unidcom-IADE)
researcher portal curates.

This repository is the **public face**; the portal is where researchers sign in with ORCID to
confirm their profile, manage selected publications and file support requests. Everything
there except the login screen and the Welcome pack needs a session. The site links into it
from the nav, the footer, every person page, and `/researchers/`.

For how the two fit together — the data flow, and the two separate privacy boundaries — see
[ARCHITECTURE.md](https://github.com/berlogabob/Unidcom-IADE/blob/main/ARCHITECTURE.md) in the
portal repository.

**Live:** https://berlogabob.github.io/unidcom-site/ — publishing approved records and
indexable since 6 August 2026. Preview builds are still available on demand
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
| A researcher's name, bio, photo, ORCID, roles | **Researcher portal** → Supabase | next sync |
| A project's title, dates, funding, members | **Researcher portal** → Supabase | next sync |
| A publication, or who authored it | **Researcher portal** → Supabase | next sync |
| Clusters, labs, objectives | **Researcher portal** → Supabase | next sync |
| An event / conference / DRIW page | `content/events/*.md` **here** | next push |
| The PixelFrames 2027 conference site | `pixelframes/content/_index.md` | **manual FTP deploy** |
| About, Vision & Mission, Ethics, Contact, Opportunities | `content/*.md` **here** | next push |
| Section intro text (e.g. the blurb above the people list) | `content/<section>/_index.md` | next push |
| Navigation menu | `hugo.toml` → `[[menu.main]]` | next push |
| Where the portal lives (login / Welcome pack links) | `hugo.toml` → `params.portal_url` | next push |
| The "For researchers" page | `content/researchers.md` **here** | next push |
| Colours, type, spacing | `themes/unidcom/assets/css/tokens.css` | next push |

Events are Markdown rather than database rows because there is no `events` table — the old
site's Agenda, Conferences and DRIW pages have no home in Supabase. If events become
frequent enough to hurt, that is the signal to add the table.

### Links into the portal

`params.portal_url` is the single place the portal's host is written down. Templates append
the route (`#/login`, `#/app/welcome/start`); content files use the shortcode instead, e.g.
`[Welcome pack]({{< portal "/app/welcome/start" >}})`. Menu entries can't carry these — Hugo
pipes `.URL` through `relURL`, which mangles an absolute URL — so the nav link is written
out longhand in `partials/nav.html`.

Person pages show a sign-in invitation **only when the person has an ORCID iD on file**
(26 of 183 today). The portal's sign-in broker rejects any iD not already in `people.orcid`,
so the other 157 get a "contact the office" note instead of a link that cannot work.

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

Automatic: `.github/workflows/sync.yml` runs nightly at 04:00 UTC, commits any
changes, and then **explicitly dispatches** `deploy.yml`.

That last step is not decoration. A push made with `GITHUB_TOKEN` does not
trigger other workflows — GitHub suppresses it to prevent recursion — so the
sync commit never deployed on its own. Between 2026-07-28 and 2026-08-07 five
nightly sync commits landed on `main` and none of them published; the site only
updated when a human happened to push afterwards. Fixed 2026-08-07.

Manually, from the repo:

```sh
export SUPABASE_URL=…  SUPABASE_SERVICE_KEY=…
uv run --project scripts scripts/sync.py
```

**The service key is required.** An earlier version of this README said the publishable (anon)
key worked too. It did — because `anon` had been granted `select` on every table, which is the
exposure closed by `20260806150100_revoke_anon_public_schema.sql` in the portal repo. `anon` now
has no access to the database at all, so the sync will fail with `permission denied for table
people` if you give it anything but the service key.

Useful flags:

```sh
--dry-run      # print the counts, write nothing
--preview      # bypass the approval gate (see below)
--self-check   # run the built-in tests, no database access
```

It prints a one-line summary you can sanity-check against the portal:

```
people 183  projects 25  publications 76  clusters 5  labs 5  objectives 12
```

Or trigger the workflow from GitHub: **Actions → Sync content from Supabase → Run workflow**.

---

## Why isn't my record on the site?

Every record passes **two independent gates**. Almost every "it's in the database but not on
the site" question is one of these.

### Gate 1 — approval

Respects the curation state set in the portal:

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
- **publications** ship only when `macro_type` is `Artigos em revistas` or `Livros`. Of 365
  `outputs` rows, 76 qualify; the other 289 are activity records, not publications.

Both allowlists are **fail-closed** — a category nobody has seen before is excluded, not
included. If a legitimately public category is added in the portal, add it to
`PROJECT_CATEGORIES` or `PUBLICATION_MACRO_TYPES` in `scripts/sync.py`.

### Field whitelists

There are two independent privacy boundaries, and they are not the same filter.

Row-level security decides which **rows** an unauthenticated caller may read at all — since
`20260805120000_approval_visibility.sql`, only approved and publicly visible ones. On top of
that, **`scripts/sync.py` decides which fields ever leave the database.** Every record is
built by explicit `pick()`, and a write-time assertion fails the run if a record carries a key
outside its declared whitelist. `email`, `legal_name`, `auth_user_id`, `notes`, `total_budget`
and `risk` are never even fetched.

The whitelist matters independently of RLS: the nightly workflow authenticates with the
service key, which bypasses row-level security entirely.

Adding a field to the site means adding it in three places in `sync.py`: the `SELECTS` query,
the `WHITELISTS` set, and the template that renders it.

---

## Preview mode

The live site is **not** in preview mode. Preview exists for rehearsing content that has not
been approved yet — it bypasses the approval gate and marks the whole site not-for-indexing.

Run one with `--preview` locally, or by ticking *preview* on the workflow input. When
`data/generated/_meta.json` has `"preview": true`:

- every page emits `<meta name="robots" content="noindex, nofollow">`
- `robots.txt` emits `Disallow: /`
- a black banner reads *Preview build — content is unapproved and not indexed*

`noindex` keeps the site out of search engines. It does **not** make the site private — the
pages are on the public internet and anyone with the URL can read them.

⚠️ **Do not commit a preview build.** The site is live: pushing `preview: true` republishes
unapproved records and re-`noindex`es a site that search engines have already begun crawling.
The nightly sync publishes only approved records, which is what you want by default.

**Going live was done on 6 August 2026** — the approval gate cost exactly one profile
(184 → 183 people, projects and publications unchanged). If you ever re-run it, confirm the
counts don't collapse to near-zero; that would mean curation isn't done.

### Why the workflow input is compared against `'true'`

This looks like a nitpick and is not. The expression used to read:

```yaml
PREVIEW: ${{ github.event.inputs.preview != 'false' }}
```

A `schedule` trigger sends **no inputs at all**, so `inputs.preview` is empty, `!= 'false'` is
true, and the nightly run was pinned to preview no matter what. While the site was genuinely
in preview that was intentional and harmless — four bot syncs ran under it between 28 July and
6 August, all correctly noindexed.

The hazard was the exit. Going live meant editing the workflow, and if anyone had gone live
without that edit, **the 04:00 run the next morning would have silently put the site back to
unapproved content and `noindex`** — with nothing in the commit to suggest a revert had
happened. Comparing against `'true'` makes preview strictly opt-in and the cron unable to
re-enter it.

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
committed JSON — so **renaming a person in the portal shows up as a URL change in a diff**
rather than silently breaking links. Old WordPress URLs redirect via Hugo `aliases`.

---

## Deploying

Push to `main`. `.github/workflows/deploy.yml` builds and publishes to GitHub Pages; it needs
no secrets.

That covers **this site only.** `deploy.yml` runs a bare `hugo --minify --gc` and never passes
`--source pixelframes`, so pushing does *not* update the conference site. That one goes out by
FTP mirror, by hand:

```sh
hugo --source pixelframes --minify --gc
FTP_USER='…' FTP_PASS='…' ./scripts/deploy_pixelframes.sh
```

It is a separate host (`pixelframe2027.unidcom-iade.pt`) precisely because GitHub Pages allows
only one custom domain per repository — see below.

`baseURL` in `hugo.toml` carries the `/unidcom-site/` subpath, so **never hardcode a
root-relative path** in a template — use `.RelPermalink`, `relURL` or `resources.Get`, or
assets will 404.

### Attaching a custom domain

1. Add `static/CNAME` containing the hostname, e.g. `unidcom-iade.pt`.
2. Set `baseURL` in `hugo.toml` to match.
3. DNS: `CNAME → berlogabob.github.io` for a subdomain, or A records to
   `185.199.108.153`, `.109.153`, `.110.153`, `.111.153` for an apex domain.

GitHub issues the certificate. **One custom domain per repository** — a `beta.` staging
domain and an apex cutover are mutually exclusive. That constraint is why the conference site
in `pixelframes/` is hosted by FTP on its own domain rather than as a second Pages site here.

---

## Known gaps

- **Photos and bios.** 105 of 183 people have a photo and 112 have a bio; the rest fall back
  to initials. The remainder are mostly collaborators and external affiliates neither
  institution ever published a page for — 42 of the 46 integrated researchers do have one.
- **Portuguese labels on an English site.** Real data, not a bug: `funding: "Outro"`, author
  roles like `"Único autor"`, objective names like `"UNID.2: Inter e transdisciplinaridade"`.
  The recurring ones want a label map in the theme; the objective names want editing in the
  portal.
- **No per-publication pages.** Publications are bibliography entries linking out to their
  DOI. Add detail pages when there is an abstract or PDF to put on them.
- **No search.** Deferred until the filters prove insufficient.
- **English only.** The old site has a Portuguese side; Hugo multilingual is not set up.
- **Placeholder copy is live.** `content/events/pixelframes-2027.md` is `draft: false` with a
  `[One-line description TBD]` summary and a placeholder date that drives its upcoming/past
  styling, and `pixelframes/content/_index.md` carries eleven more `TBD` markers. The site is
  indexable now, so these are public. They want replacing once the call for papers is out.

## Repository layout

```
content/                     editorial Markdown + content adapters (_content.gotmpl)
data/generated/              committed output of sync.py — do not hand-edit
scripts/sync.py              Supabase → JSON, and the project's privacy boundary
scripts/deploy_pixelframes.sh  FTP deploy for the conference subsite (manual)
themes/unidcom/              layouts, CSS, JS — shared by both sites
pixelframes/                 a SECOND Hugo site (own hugo.toml, own hostname)
.github/workflows/           sync.yml (nightly, commits) · deploy.yml (on push)
```

`pixelframes/` is the PixelFrames 2027 conference site. It reuses this theme
(`themesDir = "../themes"`) but is otherwise independent, and **it is not built or
deployed by CI** — see [Deploying](#deploying).
