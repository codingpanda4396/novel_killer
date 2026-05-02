# NovelOps v2

NovelOps v2 is a clean CLI workflow for producing and reviewing the serial novel project `life_balance`.

The v1 workflow has been retired. First volume chapters are now treated as read-only corpus under `projects/life_balance/corpus/volume_01/`, while story bible, outlines, and continuity state live inside the project directory.

## Commands

```bash
make check
make status PROJECT=life_balance
make review-chapter PROJECT=life_balance CH=1
make review-range PROJECT=life_balance START=1 END=50
make publish-check PROJECT=life_balance START=1 END=50
make plan-next PROJECT=life_balance CH=51
make generate PROJECT=life_balance CH=51
make generate PROJECT=life_balance CH=51 NO_LLM=1
make scout PROJECT=life_balance
```

All core commands run without a network dependency. `generate` and `review-chapter` auto-detect live LLM configuration; if no usable API key, SDK, or endpoint is available they fall back to deterministic mock/rule output instead of crashing.

Equivalent direct CLI examples:

```bash
python3 -m novelops.cli --project life_balance generate 51 --no-llm
python3 -m novelops.cli --project life_balance review-chapter 51 --no-llm
```

## LLM Configuration

Copy `config/models.example.json` to `config/models.json` for local use. `config/models.json` is ignored by git and may contain local endpoint settings.

Configuration is merged by stage:

```text
defaults -> planner/generator/reviewer/scout -> exact stage
```

Exact generation stages are `chapter_intent`, `scene_chain`, `draft_v1`, `commercial_rewrite`, `humanize`, and `revision`. Environment fallback is used when fields are absent:

```text
API key:  NOVELOPS_API_KEY -> OPENAI_API_KEY -> API_KEY
Base URL: NOVELOPS_BASE_URL -> OPENAI_BASE_URL -> BASE_URL
Model:    NOVELOPS_MODEL -> OPENAI_MODEL -> MODEL
```

The live path uses the official `openai` Python SDK against OpenAI-compatible Chat Completions. Install dependencies with:

```bash
python3 -m pip install -r requirements.txt
```

To verify live LLM behavior after setting `config/models.json` or environment variables:

```bash
python3 -m novelops.cli --project life_balance generate 51
python3 -m novelops.cli --project life_balance review-chapter 51
```

## Structure

```text
novel0/
├── novelops/                         # v2 CLI package
├── projects/
│   └── life_balance/
│       ├── project.json
│       ├── bible/
│       ├── outlines/
│       ├── corpus/volume_01/
│       ├── state/
│       ├── generation/
│       ├── reviews/
│       ├── intelligence/
│       └── publish/
├── config/
│   ├── models.example.json
│   └── novelops.example.json
├── tests/
├── Makefile
└── README.md
```

## Gates

- Chapter review writes JSON reports into `projects/life_balance/reviews/`.
- Chapters below the configured threshold enter `reviews/revision_queue/`.
- `generate` writes candidates into `generation/chapter_XXX/` only.
- Generation writes staged artifacts `01_chapter_plan.json` through `08_review_gate.json`, then up to two revision rounds `09`-`12` if review asks for changes.
- No command automatically writes generated text into `publish/ready/`.
