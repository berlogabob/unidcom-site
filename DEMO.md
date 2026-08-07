# Presentation runbook

Three demos showing one pipeline: **ORCID → admin app → database → website.**

| | |
|---|---|
| Researcher portal | https://berlogabob.github.io/Unidcom-IADE/ (sign in first — everything but the Welcome pack needs a session) |
| Website | https://berlogabob.github.io/unidcom-site/ |
| Actions | https://github.com/berlogabob/unidcom-site/actions |
| ORCID | https://orcid.org/0009-0009-8585-0074 |

---

## Preconditions — last verified 29 July, 09:00

⚠️ These ticks are from 29 July and the database has moved since. **Re-check them
before you present**; they are a checklist, not a guarantee.

| | |
|---|---|
| Both Saras still unmerged | ✅ demo 2 is primed |
| Address still the old one in both files | ✅ demo 5 is primed |
| ORCID bio still matches the database | ✅ — so `Auto-fill` says "already up to date" **until you edit ORCID**, which is the point |
| Supabase secrets + sync workflow | ✅ proven end to end |
| Database backup | ✅ `Unidcom-IADE/scripts/out/` |

Site state: **105 of 183 portraits**, 112 biographies, 9 events, 25 projects, 76
publications. The site went **live on 6 August**: the preview banner is gone, `robots.txt`
reads `Allow: /` with a sitemap, and only approved records are published.

**One gap to consider closing first:** Rui Ramos, Executive Direction, has no photo — the most
visible blank on the site. So do you, on the profile you are about to demo.

---

## 60-second pre-flight

Run these before you present. Each should pass without thinking about it.

- [x] Admin app loads and you are signed in.
- [x] Website loads.
- [x] Actions tab open in a third browser tab, ready to click.
- [x] Terminal open at `~/Documents/GitHub/unidcom-site` — the fallback.
- [x] The new campus address is on your clipboard.
- [x] Andrey's bio in the admin app is still the **old** text (so tomorrow's change shows).
- [x] ORCID biography visibility is **Public** — if it is not, the app cannot read it.

```sh
# Confirms what the app will see. Should print the OLD bio right now.
curl -s -H "Accept: application/json" \
  https://pub.orcid.org/v3.0/0009-0009-8585-0074/person \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['biography']['content'])"
```

---

## Running order

Trigger the sync (step 4) **before** the address demo (step 5). The ~2 minutes of sync and
deploy then elapse while you are talking, instead of in silence.

| # | Step | Where | ~Time |
|---|---|---|---|
| 1 | Change the bio on ORCID | orcid.org | 1 min |
| 2 | Merge the duplicate person | admin app | 1 min |
| 3 | Pull the bio into the admin app | admin app | 1 min |
| 4 | **Trigger the sync** | GitHub Actions | click, leave it |
| 5 | Change the campus address | terminal | 2 min |
| 6 | Show everything live | website | 1 min |

---

## 1 — Change the bio on ORCID

> *"This is my own ORCID record. I control it — not the university, not an administrator."*

On https://orcid.org, edit **Biography**, paste your new text, save.

Then **verify it has propagated** before touching the admin app. The public API lags the
ORCID website by a minute or two:

```sh
curl -s -H "Accept: application/json" \
  https://pub.orcid.org/v3.0/0009-0009-8585-0074/person \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['biography']['content'])"
```

**Expect:** your new text.
**If it still prints the old text:** wait. Do not click Auto-fill yet — the app reads this
exact endpoint, so it will see the old text too and tell you there is nothing to update.

---

## 2 — Merge the duplicate person

> *"The database has the same researcher twice. The app finds these itself."*

**Admin → Merge → People**

The candidate group appears automatically — no search needed. The app groups names by token
containment, and `Sara Gancho` is a subset of `Sara Patrícia Martins Gancho`.

1. Click **Review & merge** on the Sara group.
2. The **Merge people** matrix opens: one column per record, one row per field.
3. Pick the **Sara Gancho** column for every field. It is the one with an ORCID, an email,
   47 publications, and a lab membership. The other row has none of those.
4. Click through the **Merge records?** confirmation → **Continue**.

**Expect:** a snackbar confirming the merge, and the Sara group disappears from the candidate
list.

> Worth saying out loud: the matrix is per-field, so a merge can take the best value from each
> record rather than blindly picking one. That is the point of reviewing rather than
> auto-merging.

**If it fails:** the backup is at `Unidcom-IADE/scripts/out/` (taken tonight);
`scripts/restore.py` puts it back. Don't attempt a restore on stage — move on to demo 3.

---

## 3 — Pull the bio into the admin app

> *"I updated my ORCID. I never touched the university's database. Watch."*

**People → Andrey Dyakov → Auto-fill**

(The button is labelled **Auto-fill**, next to *Edit* and *ORCID sync*.)

1. The app fetches your live ORCID record.
2. A matrix opens: **Current** value versus **ORCID** value, per field. Only fields where
   ORCID differs are listed — so you should see **Bio**, and nothing else.
3. Tick the ORCID side for **Bio**. Apply.

**Expect:** the bio on the person page updates to your new text.

**If it says "Already up to date with ORCID":** ORCID has not propagated yet. Go back to the
curl in step 1. This is the single most likely thing to go wrong — hence the check.

**If it says "No ORCID profile found to pull from":** the biography visibility on orcid.org is
not Public.

---

## 4 — Trigger the sync

> *"The website is static — it doesn't talk to the database. It's rebuilt from it."*

**Actions → Sync content from Supabase → Run workflow** (leave *preview* **unticked**) → **Run**.

> The site went live on 6 August. Ticking *preview* republishes unapproved records and puts
> `noindex` back on the whole site — do not tick it during a demo.

Leave it running and go straight to step 5. It commits the changed data and then dispatches
the deploy, so watch for **two** runs in the Actions tab — the sync, then the deploy. Together
they take about three minutes.

**Fallback, if the workflow errors:**

```sh
cd ~/Documents/GitHub/unidcom-site
set -a && . ~/Documents/GitHub/Unidcom-IADE/scripts/.env && set +a
uv run --project scripts scripts/sync.py
git add -A && git commit -m "Sync content from Supabase" && git push
```

---

## 5 — Change the campus address

> *"Not everything belongs in a database. The address is editorial content, so it lives in
> the site's own repository — versioned, reviewable, with a history."*

Two files. Open them in the editor so the change is *visible* — this is the demo where your
audience can see plain text becoming a website.

### `hugo.toml`, line 17 — drives the footer on every page

Replace:

```toml
  address = "Av. D. Carlos I, 4, 1200-649 Lisboa, Portugal"
```

with:

```toml
  address = "Rua Adão Manuel Ramos Barata 3, Moscavide, 1886-502 Lisboa"
```

### `content/contact.md`, lines 6–9 — the Contact page

Replace:

```markdown
UNIDCOM/IADE  
Av. D. Carlos I, 4  
1200-649 Lisboa  
Portugal
```

with:

```markdown
UNIDCOM/IADE  
Rua Adão Manuel Ramos Barata 3  
Moscavide  
1886-502 Lisboa  
Portugal
```

> **Keep the two trailing spaces** at the end of every line except the last. That is what makes
> Markdown render them as separate lines instead of one run-on paragraph.

Then:

```sh
cd ~/Documents/GitHub/unidcom-site
hugo --gc --quiet && echo BUILD-OK     # catches a typo before it ships
git add -A && git commit -m "Update the campus address" && git push
```

**Expect:** `BUILD-OK`, then a deploy starting in the Actions tab.

Worth mentioning while it builds: the address also goes into the page's structured data, so
search engines and maps pick up the move without anyone editing them separately.

**If you'd rather not hand-edit on stage**, this does both files in one paste:

```sh
cd ~/Documents/GitHub/unidcom-site
python3 - <<'EOF'
import pathlib
p = pathlib.Path('hugo.toml')
p.write_text(p.read_text(encoding='utf-8').replace(
    'Av. D. Carlos I, 4, 1200-649 Lisboa, Portugal',
    'Rua Adão Manuel Ramos Barata 3, Moscavide, 1886-502 Lisboa'), encoding='utf-8')
p = pathlib.Path('content/contact.md')
p.write_text(p.read_text(encoding='utf-8').replace(
    "Av. D. Carlos I, 4  \n1200-649 Lisboa  \nPortugal",
    "Rua Adão Manuel Ramos Barata 3  \nMoscavide  \n1886-502 Lisboa  \nPortugal"), encoding='utf-8')
print("address updated")
EOF
hugo --gc --quiet && echo BUILD-OK
git add -A && git commit -m "Update the campus address" && git push
```

Both paths are rehearsed — the accented `ã` renders correctly in the footer, on the Contact
page and in the structured data.

---

## 6 — Show everything live

Give the deploy a moment, then **hard-reload** (⌘⇧R) — GitHub's CDN will otherwise serve you
the old page.

| Page | What to point at |
|---|---|
| `/people/` | One Sara, not two |
| `/people/andrey-dyakov/` | The bio you wrote on ORCID |
| Any page, footer | The new address |
| `/contact/` | The new address |

> *"One ORCID edit, one merge, one commit — three different paths into the same site, and none
> of them needed a web developer."*

**If a page still looks stale:** open it in a private window. That bypasses the cache without
you having to explain what a CDN is.

---

## Questions you are likely to get

**Why do some people have no photo?**
105 of 183 have one: 51 recovered from the old UNIDCOM site, 54 from the official IADE staff
directory. The remaining 78 are almost all collaborators and external affiliates that neither
institution ever published a page for — **42 of your 46 integrated researchers do have a
photo.** The rest get added through the admin app, or by asking people directly.

**Why are the photos black and white?**
They arrive from two sources in two styles, so the site renders them all greyscale. It matches
the identity and means the grid reads as one set rather than a patchwork.

**Are the events real?**
Yes — DRIW '21 through 2024, the International Congress on Past and Present Slaveries, the AI
Workshop with Leonel Moura, European Researchers' Night and Italian Design Day. Text and
artwork came from the old site; the dates come from the source pages.

The ninth, **PixelFrames 2027**, sorts to the top as the upcoming event and is the one to
expect a question about: it is a real conference with its own site at
pixelframe2027.unidcom-iade.pt, but its listing here is still placeholder copy and a
placeholder date until the call for papers is out. Say so rather than being caught by it.

**Is everything in the database on the site?**
No — only what has been approved. The sync publishes a person once their profile is approved
and publicly visible, and a publication once its record is approved; 183 people, 25 projects
and 76 publications qualify today. Unapproved records simply do not appear. Until 6 August the
site ran in preview mode, which bypassed that gate and carried a "Preview — work in progress"
banner with `noindex`; that mode still exists as an opt-in for rehearsals.

**Is the old site still running?**
Yes. This replaces it when the content is signed off. Old URLs already redirect — the
researcher pages, the agenda, vision and mission, and ethics.

**Where does the publication list come from?**
The same database. The site shows journal articles and books; the database also holds internal
reporting records — thesis juries, management activity — which are deliberately never
published.

---

## Reset after rehearsing

So the change is actually visible tomorrow:

1. In the admin app, set Andrey's bio back to the old text.
2. On orcid.org, set the biography back to the old text.
3. Re-run the sync so the site matches.

**Do not complete the Sara merge while rehearsing** — a merge cannot be undone from the UI, and
you would arrive tomorrow with nothing to show.

The database has exactly **two** duplicate pairs:

| Pair | Use it for |
|---|---|
| `Paulo Bago D’Uva` ↔ `Paulo Uva` | **rehearsal** — merge this one for real tonight |
| `Sara Gancho` ↔ `Sara Patrícia Martins Gancho` | **the demo** — leave untouched |

Rehearsing on Paulo exercises the identical code path and fixes a genuine duplicate, so the
practice run does real work. For Paulo, keep **`Paulo Uva`** — it has the email
(`paulo.b.uva@gmail.com`) and the lab membership; `Paulo Bago D’Uva` has neither, nor any
publications.

After merging Paulo, only the Sara group remains in the candidate list — which makes
tomorrow's screen cleaner, with exactly one thing on it.
