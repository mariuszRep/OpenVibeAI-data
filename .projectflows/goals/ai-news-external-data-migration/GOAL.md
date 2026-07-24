---
name: ai-news-external-data-migration
title: AI News External Data Repo Migration
description: Migrate AI News JSON data from the committed OpenVibeAI website repo to the separate GitHub Pages data repo (OpenVibeAI-data), update the website to fetch from the external URLs, and update/supersede the OpenDora workflow publisher to target the data repo.
status: cancelled
type: migration
scope: /home/mariusz/projects/OpenVibeAI-data/data/ai-news/**, /home/mariusz/projects/OpenVibeAI/app/products/ai-news/**, /home/mariusz/projects/OpenVibeAI/components/**, /home/mariusz/projects/opendora/.projectflows/goals/ai-news-workflow-data-publisher/GOAL.md
attempt: 0
max_attempts: 5
last_result: none
next_action: Copy AI News JSON files to OpenVibeAI-data repo, update website fetch, update OpenDora workflow goal, verify builds, commit/push, verify live.
success_criteria:
  - AI News JSON (latest.json, archive.json) exists in OpenVibeAI-data/data/ai-news/ and is valid.
  - OpenVibeAI-data GitHub Pages exposes the JSON files at public URLs.
  - Website no longer imports local OpenVibeAI/data/ai-news/latest.json as its primary fresh content source.
  - Website fetches AI News JSON from the GitHub Pages URL with proper loading, error, and stale-data handling.
  - OpenDora workflow publisher goal is updated to target OpenVibeAI-data instead of OpenVibeAI.
  - Website build passes (npm run build exits 0).
  - Data repo changes are committed and pushed.
  - Live GitHub Pages URLs return valid JSON.
  - No backend, database, CMS, or auth is added.
source: user
---

# AI News External Data Repo Migration

## Goal
Migrate the AI News JSON data pipeline from the OpenVibeAI website repository (where JSON files are committed and imported at build time) to the separate OpenVibeAI-data GitHub Pages repository. After migration, the website fetches AI News data at runtime from the public GitHub Pages URLs, enabling fresh content updates without website redeployments. The OpenDora workflow publisher that generates the JSON is updated to write/commit/push to the data repo instead. This establishes a reusable pattern for hosting multiple product data sets on GitHub Pages.

## Source Requirements
- AI News JSON data moves out of `/home/mariusz/projects/OpenVibeAI/data/ai-news/` and into `/home/mariusz/projects/OpenVibeAI-data/data/ai-news/`.
- The OpenVibeAI-data GitHub Pages site serves the JSON files at predictable public URLs.
- The website page at `app/products/ai-news/page.tsx` fetches from the GitHub Pages URLs instead of importing local JSON.
- Fetch behavior must handle loading states, fetch errors, and fallback to stale/cached data when the GitHub Pages URL is unavailable.
- The OpenDora workflow at `opendora/.projectflows/goals/ai-news-workflow-data-publisher/GOAL.md` is updated so the next execution writes JSON to OpenVibeAI-data and commits/pushes there.
- No backend, database, CMS, or authentication is added.
- Schema compatibility with existing `lib/ai-news-types.ts` is preserved.

## Problem / Motivation
The current AI News pipeline commits JSON data directly into the OpenVibeAI website repository. Every data update requires a website rebuild and redeploy. By moving the data to a separate GitHub Pages data repo, the live website can fetch fresh content immediately after a data push without any website redeployment. This pattern is also reusable for future products (e.g., Color Vibes palettes, UI Vibes components) that need data hosted outside the main app repo. It decouples content publishing from application deployment.

## Vision Alignment
- **Relevant product/project context**: OpenVibeAI site is static/frontend-only (Next.js static generation). No backend, databases, or auth. The VISION.md states "no user accounts, authentication, or backend persistence." Fetching from a public GitHub Pages JSON URL maintains this constraint — no backend is introduced. The data repo (OpenVibeAI-data) is established with GitHub Pages enabled and is the canonical location for all products data.
- **Product/non-goal constraints**: No backend, database, CMS, or auth added. Data is served via static JSON over HTTPS. The website must handle URL unavailability gracefully. The AI News schema (AiNewsStory, AiNewsData) is preserved from the existing `lib/ai-news-types.ts`.

## Convention Constraints
- **Relevant technical/project constraints**: Next.js 16 App Router, TypeScript, Tailwind CSS 4, shadcn/ui primitives. Static data lives in `data/` as JSON files. No backend dependencies. The OpenVibeAI-data repo has GitHub Pages enabled on the `main` branch serving from the repository root.
- **Required stack/patterns**: Client-side fetch from public HTTPS URLs. Loading state handled via React state (useState/useEffect or a simple client component pattern). Error state: show a user-friendly message with a retry option, fall back to cached data if previously loaded. The data files in `OpenVibeAI/data/ai-news/` may remain as build-time fallbacks or be removed — the primary content source becomes the GitHub Pages URL.
- **Forbidden patterns/libraries**: No backend, database, CMS, auth, API routes, or server-side data fetching that requires a server runtime. No JavaScript runtime dependencies added beyond the existing stack. Do not modify the ai-news-types.ts schema without a documented compatibility issue.
- **Verification commands**: `npm run build` (type-check + production build, must exit 0). `curl` or browser fetch to GitHub Pages URLs must return valid JSON.

## Scope
1. **Create data repo directory structure** — Create `data/ai-news/` in OpenVibeAI-data if not present.
2. **Copy AI News JSON** — Copy `latest.json` and `archive.json` from OpenVibeAI to OpenVibeAI-data, preserving the exact schema and content.
3. **Commit and push data repo** — Commit the JSON files, push to `origin/main` on OpenVibeAI-data so GitHub Pages serves them.
4. **Verify GitHub Pages URLs** — Confirm `https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/latest.json` and `archive.json` resolve.
5. **Update website page** — Change `app/products/ai-news/page.tsx` from static JSON imports to client-side fetch from the GitHub Pages URLs with loading, error, and fallback handling.
6. **Update OpenDora workflow goal** — Edit `opendora/.projectflows/goals/ai-news-workflow-data-publisher/GOAL.md` scope to target `OpenVibeAI-data/data/ai-news/**` instead of `OpenVibeAI/data/ai-news/**`.
7. **Verify website build** — Run `npm run build` to confirm no TypeScript or build errors.
8. **Document remaining risks** — Note GitHub Pages cache delay, CORS behavior, and the workflow push credential requirement.

## Out of Scope
- Backend, database, CMS, authentication, or API routes.
- Creating a reusable library/component for GitHub Pages data fetching (future products can copy the pattern).
- Changing the AI News story schema (`AiNewsStory`, `AiNewsData`).
- Modifying other product data (Color Vibes, UI Vibes, Projectflows).
- Creating a manifest.json or any new data files beyond latest.json and archive.json.
- Modifying the OpenDora workflow JSON itself (the workflow goal is updated; the workflow implementation is a separate execution).
- Changing website navigation, layout, or design language.
- Setting up GitHub Actions or CI/CD for the data repo (manual commit/push for now).

## Acceptance Criteria

### Data Migration
- A1. `OpenVibeAI-data/data/ai-news/latest.json` exists and contains valid JSON matching the `AiNewsData` schema.
- A2. `OpenVibeAI-data/data/ai-news/archive.json` exists and contains valid JSON matching the `AiNewsData` schema.
- A3. JSON content matches the source files from OpenVibeAI (same stories, same schema, no data loss).

### GitHub Pages Availability
- A4. `https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/latest.json` returns a 200 response with valid JSON.
- A5. `https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/archive.json` returns a 200 response with valid JSON.
- A6. Both URLs serve `Content-Type: application/json` or equivalent.

### Website Data Fetch
- A7. The website page at `/products/ai-news` fetches story data from the GitHub Pages URLs at runtime.
- A8. While data is loading, the page shows a loading indicator (not a blank or broken page).
- A9. If the fetch fails (network error, non-200 response), the page shows a user-friendly error message with a retry mechanism.
- A10. If data has been loaded previously (session cache), the page may show cached/stale data while refreshing.
- A11. The page does not depend on local `data/ai-news/latest.json` import for its primary fresh content (the local file may remain as a fallback but is not the primary source).

### OpenDora Workflow Goal Update
- A12. The workflow goal at `opendora/.projectflows/goals/ai-news-workflow-data-publisher/GOAL.md` has its scope updated to target `OpenVibeAI-data/data/ai-news/**` instead of `OpenVibeAI/data/ai-news/**`.
- A13. The goal's acceptance criteria reflect the new target path.

### Build & Verification
- A14. `npm run build` in OpenVibeAI exits 0 with no TypeScript errors.
- A15. No backend, database, CMS, or auth is added.

## Judgment Rubric
- **Done**: All acceptance criteria A1–A15 satisfied. GitHub Pages URLs return valid JSON. Website builds and shows news from the external URL. Workflow goal is updated.
- **Partial/Continue**: Data is copied to the data repo and URLs are verified (A1–A6), but the website fetch update has issues (A7–A11) that need a follow-up attempt.
- **Blocked**: GitHub Pages is not serving the files (A4–A5 fail), website build fails (A14), or the schema must change for compatibility (A3 fails).
- **Risk-based block**: If GitHub Pages has a significant cache delay (>30 minutes) that prevents live verification, note it as a risk and proceed with the website changes verified against a local alternative.

## Implementation Guidance
- **Fetch approach**: Use a client component with `useEffect` + `fetch`. Store fetched data in state. Show loading skeleton while fetching. On error, show a message with a "Retry" button and fall back to cached data from previous successful fetches (stored in a ref or sessionStorage).
- **Fallback strategy**: Keep the existing local JSON files in `OpenVibeAI/data/ai-news/` as a build-time fallback. The page can import them at build time for SSR/SSG, but the primary data source at runtime is the GitHub Pages URL. On the client, try to fetch from the external URL first; if it fails, fall back to the build-time data. This ensures the page always renders something.
- **Cache handling**: GitHub Pages may cache files for up to 10 minutes. The website should note that data may have a short delay. No aggressive caching headers are needed on the fetch side since the data is public.
- **URL constants**: Define the GitHub Pages base URL and paths as constants for maintainability.
- **No new dependencies**: Use native `fetch` and React built-ins. No need for SWR, React Query, or similar — the fetch pattern here is simple enough for `useEffect` + `useState`.
- **Pattern reuse**: Keep the fetch logic self-contained in the page or a dedicated component so future products can copy the pattern. Do not over-engineer into a shared library yet.
- **OpenDora workflow goal**: The goal file at `opendora/.projectflows/goals/ai-news-workflow-data-publisher/GOAL.md` currently targets `OpenVibeAI/data/ai-news/**`. Update the scope field and any related path references to target `OpenVibeAI-data/data/ai-news/**`. Also update acceptance criteria that reference writing paths to reflect the new data repo.

### URL Contract
```
https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/latest.json
https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/archive.json
```

### JSON Schema (Preserved)
```typescript
interface AiNewsStory {
  id: string;
  slug: string;
  title: string;
  summary: string;
  sourceUrl: string;
  sourceName: string;
  publishedAt: string;
  selectedAt: string;
  category: string;
  tags: string[];
  shareText: string;
  linkedinPost?: string;
  xPost?: string;
  confidence?: number;
  featured?: boolean;
  order?: number;
}

interface AiNewsData {
  generatedAt: string;
  sourceRun: string;
  stories: AiNewsStory[];
}
```

## Risks / Unknowns
- **GitHub Pages cache delay**: After pushing new JSON to the data repo, GitHub Pages may take up to 10 minutes to reflect changes. The live website may show stale data during this window. This is acceptable — the key improvement is that no website redeploy is needed.
- **CORS behavior**: GitHub Pages serves with permissive CORS headers by default for public repos, but this should be verified live. If CORS blocks the fetch, GitHub Pages settings may need adjustment, or the website may need a different approach.
- **Bad JSON from workflow**: If the workflow produces invalid JSON, the website fetch will fail. Defensive JSON parsing (`try/catch` around `response.json()`) handles this gracefully with an error state.
- **Workflow git credentials**: The OpenDora workflow's bash tool node needs git credentials to commit and push to OpenVibeAI-data. This is a future concern for when the workflow is executed, but the goal update notes it.
- **Existing local imports**: The current page imports JSON directly (`import latestData from "@/data/ai-news/latest.json"`). After the migration, this import may still work at build time but the primary source should be the external URL. The local files can remain as fallbacks.
- **Website reload for fresh data**: Since the fetch happens on the client, users need to reload the page to see fresh data (or the page could auto-refresh periodically — out of scope for now).
- **Vercel deployment**: The website deploys on Vercel. No configuration changes should be needed since there are no new environment variables or build settings.

## Verification Expectations
1. `curl https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/latest.json` returns 200 and valid JSON.
2. `curl https://mariuszRep.github.io/OpenVibeAI-data/data/ai-news/archive.json` returns 200 and valid JSON.
3. `npm run build` in OpenVibeAI exits 0.
4. Manual browser review: `/products/ai-news` page loads and displays news stories.
5. Manual browser review: disconnect network (DevTools offline mode) and confirm error state is shown.
6. Verify the JSON content matches between old and new locations (schema and data integrity).

## Attempts
No attempts yet.

## Do Not Repeat
None yet.

## Verification Log
No verification yet.

## Final Outcome
Cancelled. The data has been migrated from `data/ai-news` to `data/blog_and_news`. The RSS publisher workflow now writes directly to `data/blog_and_news/news/{slug}.json` and `data/blog_and_news/index.jsonl`, following the BLOG_SCHEMA.md structure. This legacy goal is superseded by the new blog-and-news export flow.

## Ready For Execution
- Status: no (cancelled)
- Reason: Superseded by the blog-and-news export migration.
