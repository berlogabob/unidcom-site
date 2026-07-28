# unidcom-site

Public website for [UNIDCOM/IADE](https://www.unidcom-iade.pt/). Hugo static site, content
generated from the UNIDCOM Supabase database (the same DB the
[Unidcom-IADE](https://github.com/BerlogaBob/Unidcom-IADE) Flutter admin app curates).

```
Supabase ──scripts/sync.py──► data/generated/*.json ──content adapters──► Hugo ──► GitHub Pages
```

Supabase is the source of truth. This site never talks to it at runtime — the generated
JSON is committed, so a deploy needs no database credentials.

## Develop

```sh
hugo server            # http://localhost:1313/unidcom-site/
```

## Refresh content from the database

```sh
export SUPABASE_URL=... SUPABASE_SERVICE_KEY=...
uv run --project scripts scripts/sync.py --preview   # writes data/generated/
```

Also runs nightly via `.github/workflows/sync.yml`, which commits any changes.

## Preview mode

`--preview` ignores the database's approval gates so the site has content to show while
curation is still in progress. It sets `preview: true` in `data/generated/_meta.json`,
which makes every page emit `<meta name="robots" content="noindex">` and show a banner.

Drop the flag to build only approved, publicly-visible records. Do that before launch.
