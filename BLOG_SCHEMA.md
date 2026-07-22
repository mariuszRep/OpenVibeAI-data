# OpenVibe Blog Data Contract

Blog posts are evergreen OpenVibe articles. Blog and News are now discovered
through the combined `data/blog_and_news/index.jsonl` feed.

## Files

- `data/blog_and_news/index.jsonl` contains one compact card record per post.
- `data/blog_and_news/blog/{slug}.json` contains each full blog article.
- `data/blog_and_news/news/{slug}.json` contains each full news article.

## Post shape

```ts
type BlogPost = {
  slug: string
  title: string
  excerpt: string
  publishedAt: string // YYYY-MM-DD
  updatedAt?: string
  tags: string[]
  readingTime: string
  author: string
  relatedProduct?: "voice-typer"
  content: string[] // ordered paragraphs
}
```

## News documents

Each `data/blog_and_news/news/{slug}.json` file uses the existing AI News
story shape from `AI_NEWS_SCHEMA.md`, with one additional field:

```ts
type NewsDocument = AiNewsStory & { type: "news" }
```

The index carries only card metadata; the full document retains `sources`,
`impactAnalysis`, tags, and social fields so the individual news page keeps
its source and sharing UI.

Every `index.jsonl` line must contain `type` (`blog` or `news`), `slug`,
`title`, `excerpt`, `publishedAt`, and a relative `path`, such as
`blog/my-guide.json` or `news/my-story.json`. Newest entries come first.
