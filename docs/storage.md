# NovelOps Storage

NovelOps now uses one main database at `runtime/novelops.sqlite3` by default. Set
`NOVELOPS_DB_URL` to any SQLAlchemy URL to point SQLModel at another database,
for example `postgresql+psycopg://user:password@host:5432/novelops`.

The SQLite MVP keeps Markdown and JSON source files as the authority for long
form content:

- Chapter text stays in `corpus/` or `generation/`; `chapters.content_path`
  stores the file path.
- Chapter plans stay in generation JSON artifacts; `chapter_plans.plan_path`
  stores the file path and selected query fields.
- Review reports stay in `reviews/`; `reviews.report_path` stores the file
  path plus score and status fields.
- Radar collection and analysis write to unified `hot_items` and
  `market_reports` tables in the main database.

Compatibility tables such as `projects`, `raw_signals`, `analyzed_signals`, and
`topic_opportunities` are still created for existing Web views, tests, and
scripts while callers migrate to the SQLModel models.

Useful commands:

```bash
novelops index
novelops db-status
python -m novelops.radar run-sample
```
