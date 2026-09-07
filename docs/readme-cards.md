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

Productive Time receives a one-shot 0.6-second bar-growth animation, starting
after a 0.3-second delay, after each
successful download. Its static geometry and colors remain unchanged. Reduced
motion users see the full chart immediately. Animation decoration is idempotent;
unexpected upstream bar structure retains the previous snapshot.
The title, axis paths, tick marks, tick labels and footer fade in on the same
timeline as the bars. The background remains visible throughout.
The README uses `productive-time-animated-v2.svg` to avoid the earlier image cache;
GitHub's raw redirect stripped the former query version. The previous
`productive-time.svg` is retained for older cached READMEs, but no longer updated.
The delay improves visibility but cannot synchronize
separate images or restart an animation on viewport entry.

Separate README images have independent load/animation timelines. Equal CSS
delays cannot guarantee simultaneous starts. A single composed SVG with embedded
card geometry and scoped CSS could share one timeline, but would change the
current independent links and responsive layout; it is not implemented here.

```sh
python -m unittest discover -s tests -v
python scripts/refresh_readme_cards.py
git diff -- assets/readme-cards
```

This document is separate from the profile README and is not embedded on the
profile page. It remains publicly readable in the repository.
