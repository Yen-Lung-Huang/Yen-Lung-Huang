# README card maintenance

The README displays committed SVG snapshots, not live Vercel responses. Colors
and upstream query parameters are defined in `scripts/refresh_readme_cards.py`.
No PAT belongs in this repository: the existing Vercel deployments retain their
own credentials. Published SVGs are public, including any aggregated private
activity displayed by those deployments.

## Refresh

`Refresh README cards` runs at minutes 17 and 47 each hour and can also be run
manually in GitHub Actions. Scheduled runs may be delayed by GitHub.

Each image is downloaded with a timeout and up to three attempts. Only HTTP 200
SVG responses with valid XML, positive dimensions, expected card labels, numeric
data, and no recognized error messages replace the previous file. Replacement
is atomic. One failed image does not block publishing other successful images.
If any image still fails, the workflow ends in failure after publishing the
successful updates; consult its summary and refresh logs. Enable GitHub Actions
failure notifications in your GitHub notification settings for alerts.

Old images remain visible during upstream outages or PAT expiry. This protects
availability, not freshness: check failed workflows and renew deployment tokens
when needed. GitHub hosting outages are outside this mechanism's protection.

## Local verification

```sh
python -m unittest discover -s tests -v
python scripts/refresh_readme_cards.py
git diff -- assets/readme-cards
```

This document is separate from the profile README and is not embedded on the
profile page. It remains publicly readable in the repository.
