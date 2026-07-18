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
workflow definition:

```
~/.projectflows/workflows/ai-news-top-impact-publisher.json   (workflow definition)
~/.projectflows/workflows/ai-news-top-impact-publisher/scripts/
  publish_ai_news.py          (writes into this repo via --repo)
  list_recent_headlines.py    (dedup helper, reads this repo via --repo)
```

Nobody should look in this repo for the publishing logic — it only ever
receives the JSON files below as output.

## `AiNewsStory` shape (as of workflow v2.3.0)

```ts
type AiNewsStory = {
  id: string
  slug: string
  title: string
  summary: string              // 2-3 sentences — the site's main article body
  sources: { url: string; name: string }[]   // 1-5 items, primary source always sources[0]
  sourceUrl: string             // duplicate of sources[0].url (kept for the dedupe key)
  sourceName: string            // duplicate of sources[0].name
  websiteUrl: string            // "https://www.openvibe.ai/open-vibe/ai-news/{slug}"
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

## URL scheme change — social posts now link to your own site

`xPost`/`linkedinPost` used to embed the raw source URL. As of v2.3.0 they
link to `story.websiteUrl` instead:
`https://www.openvibe.ai/open-vibe/ai-news/{slug}`.

**This requires a real per-story page at that path with story-specific
`generateMetadata`** (title/description/OG image) — the current AI News page
(`app/products/ai-news/page.tsx`) is 100% client-side fetched with no
per-story metadata, so LinkedIn/X link-preview unfurl bots (which don't
execute JS) would only ever see the generic page card, not the specific
story. A same-page anchor (`#slug`) will not fix this. Building
`/open-vibe/ai-news/[slug]` with server-rendered metadata is the whole point
of pointing links back at the site instead of the source article — without
it, the change is functionally a no-op for social sharing.

## Also needed on the website side (not covered by this doc's data contract, listed for completeness)

- Route move: `/products/ai-news` → `/open-vibe/ai-news` (note:
  `CONVENTIONS.md` in the website repo says "do not remove or rename existing
  routes" — this needs either a redirect from the old path or an explicit
  exception noted there)
- Render up to 5 entries from `sources[]` per story (was previously a single
  source link)
- Render `impactAnalysis` alongside `summary`
- Day-grouped "last 7 days" list (data already arrives newest-first) plus an
  archive view backed by `archive/index.json`
- Update the share-button `href` construction in `ai-news-card.tsx` to use
  `story.websiteUrl` (the data now matches; the buttons still need the
  code change)
