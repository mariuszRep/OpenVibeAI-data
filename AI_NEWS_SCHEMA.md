# AI News Data Contract

This document is the handoff spec for the website-side work on OpenVibeAI's AI
News feature. It describes what the publisher (a Projectflows workflow,
`ai-news-top-impact-publisher`, living outside this repo) now writes into
`data/ai-news/`, and what the website needs to build to consume it correctly.
See the workflow-side plan this came out of for the full "why":
`~/.claude/plans/for-the-new-workflow-encapsulated-tide.md` (on the machine
that ran this change).

## Where the publisher lives now

The publish script is **not** in this repo anymore. It lives alongside its
workflow definition (the Projectflows engine's storage convention changed to
nested per-workflow directories after this was first written — path updated
below):

```
~/.projectflows/workflows/ai-news-top-impact-publisher/
  workflow.json                (workflow definition)
  scripts/
    publish_ai_news.py         (writes into this repo via --repo)
    list_recent_headlines.py   (dedup helper, reads this repo via --repo)
```

Nobody should look in this repo for the publishing logic — it only ever
receives the JSON files below as output.

## `AiNewsStory` shape (as of workflow v2.3.1)

```ts
type AiNewsStory = {
  id: string
  slug: string
  title: string
  summary: string              // 2-3 sentences — the site's main article body
  sources: { url: string; name: string }[]   // 1-5 items, primary source always sources[0]
  sourceUrl: string             // duplicate of sources[0].url (kept for the dedupe key)
  sourceName: string            // duplicate of sources[0].name
  websiteUrl: string            // "https://www.openvibe.ai/ai-news/{slug}"
  publishedAt: string           // YYYY-MM-DD, date the primary source displayed
  selectedAt: string            // YYYY-MM-DD, date the workflow selected it
  category: string
  tags: string[]
  impactAnalysis: {
    summary: string             // 2-4 sentences on impact on the wider AI industry
    scope: "narrow" | "moderate" | "industry-wide"
    affectedAreas: string[]     // e.g. ["llm infrastructure", "ai regulation"]
  }
  confidence: number            // 0-1
  featured: boolean             // true for exactly one story in latest.json — the newest
  order: number                 // display order, newest-first, recomputed on every publish
  shareText: string             // platform-neutral, derived from the finished story
  xPost: string                 // links to websiteUrl, never sourceUrl
  linkedinPost: string          // links to websiteUrl, never sourceUrl
}
```

**What's new vs. the previous shape:** `sources[]` (replaces a single
implicit source), `websiteUrl`, `impactAnalysis`. `sourceUrl`/`sourceName`
are kept as duplicates of `sources[0]` — the dedupe key (`story_key()` in the
publish script) still hashes on `sourceUrl` first, so nothing about
deduping/merging changed.

**Ordering guarantee:** `data/ai-news/latest.json`'s `stories` array is now
always sorted newest-first by `publishedAt`, with `order`/`featured`
recomputed globally across the whole merged set on every publish run (not
just within one day's batch) — safe to render in array order without
re-sorting client-side, and `featured` is now guaranteed unique.

## Files

- `data/ai-news/latest.json` — `{updatedAt, stories}`. Rolling window,
  currently the last 7 days. Sorted newest-first (see above).
- `data/ai-news/archive/{YYYY-MM}.json` — `{updatedAt, stories}`. One file
  per month, for stories older than 7 days. Sorted newest-first within the
  month.
- `data/ai-news/archive/index.json` — **new**. `{updatedAt, months: [{month:
  "YYYY-MM", path: "archive/YYYY-MM.json", count}]}`, sorted newest-month-first.
  Fetch this first, then fetch only the month files you actually need — avoids
  downloading the entire history just to render an archive view or paginate
  by month.
- `data/ai-news/archive.json` (flat file) — **deprecated, do not read this
  anymore.** The publish script stopped writing it; it's frozen at whatever
  it last contained (2026-07-01) and will silently go stale. It's still
  present in the repo only because deleting it now would break the live site
  before the website switches to `archive/index.json` — delete it as part of
  the website migration once nothing reads it.

## URL scheme — social posts link to your own site

`xPost`/`linkedinPost` link to `story.websiteUrl`:
`https://www.openvibe.ai/ai-news/{slug}`.

**Status: built.** The website now serves `/ai-news` (listing) and
`/ai-news/[slug]` (per-story page with `generateMetadata` — title,
description, and a generated OG image) so LinkedIn/X unfurl bots get a real
preview card instead of the generic page. The website's own
`lib/ai-news-data.ts` deliberately **recomputes** the canonical story URL
from the slug rather than trusting the `websiteUrl` field verbatim — this
was found to matter in practice (see note below).

**Known transitional mismatch, already handled:** the route settled on
`/ai-news`, not `/open-vibe/ai-news` as originally speced in this doc. The
workflow was writing `websiteUrl` values pointing at `/open-vibe/ai-news/...`
during earlier test runs before that was caught — 6 already-published
stories in `latest.json` still carry those stale URLs. The website added a
redirect (`/open-vibe/ai-news(/:slug)` → `/ai-news`) to cover them, and the
workflow (`build_story_payload`, fixed as of v2.3.1) now writes
`/ai-news/{slug}` directly, so no more stale URLs will be produced going
forward. The redirect can stay indefinitely as a safety net or be removed
once nothing old-format remains in `latest.json`/the archive.

## Website side — status

All built, per the website team's report:
- Route: `/ai-news` (listing) + `/ai-news/[slug]` (per-story page,
  `generateMetadata`, generated OG image). Old `/products/ai-news` redirects
  here; `CONVENTIONS.md`'s "don't rename routes" rule was given a documented
  exception for this move.
- Renders `sources[]` (falls back gracefully for older stories published
  before this field existed) and `impactAnalysis` when present.
- Share buttons point at the site (`websiteUrl`, recomputed from slug); the
  separate source link still points at the original article.
- Day-grouped "Latest Stories" list, no client-side re-sorting (trusts the
  now-guaranteed server-computed order); archive UI backed by
  `archive/index.json` with lazy per-month fetching.
- `app/sitemap.ts` has dynamic per-story entries.

**Known gap on the website side:** roughly half of the stories already in
`latest.json` predate this schema (`sources`/`impactAnalysis`/`websiteUrl`
absent) — the website made these fields optional with fallbacks rather than
assuming they're always present. New stories published by workflow v2.3.1+
will always have them.
