# TikHub Feishu Creator Monitor Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build and publicly release one installable Codex Skill that monitors Douyin and Xiaohongshu creators through TikHub, persists deduplicated history in Feishu Base, produces reports and analysis documents, and is invoked by Codex scheduled tasks.

**Architecture:** A single `creator-monitor` Skill routes seven deterministic CLI commands. Python code owns API calls, normalization, idempotency, snapshots, budget enforcement, retries, and Feishu CLI orchestration. Feishu remains the collaborative data product layer; Codex automations only invoke versioned commands and report outcomes.

**Tech Stack:** Python 3.11+, stdlib-first HTTP/JSON/subprocess code, Pydantic for contracts, Typer for CLI, pytest for tests, official `lark-cli`, TikHub REST APIs, Codex local cron automations, GitHub Actions.

---

## Intent and boundaries

- Deliver a public repository, a user-owned rewritten Feishu tutorial, and a verified live MVP.
- Preserve the source article's account library, content library, six views, dashboard, battle report, analysis document, and failure handling.
- Replace Coze/n8n/Dify node workflows with one Skill and deterministic modules.
- Keep TikHub credentials, Feishu tokens, real private data, and unredacted responses out of Git history.
- Cap live TikHub spend at USD 0.50 for the entire MVP and requests at 20 per run.
- Use one public Douyin account and one public Xiaohongshu account for initial proof.
- Generate explanatory raster diagrams with the built-in ImageGen tool; keep real product screenshots as explicit user capture slots.

## Storage contract

- `SKILL.md`, `agents/`, `references/`, `scripts/`, and `src/`: maintained Skill and runtime code.
- `tests/`: unit, contract, and integration verification; committed fixtures must be synthetic or redacted.
- `docs/`: maintained architecture, data dictionary, operations, troubleshooting, and implementation notes.
- `docs/images/`: final generated explanatory images used by README and the Feishu tutorial.
- `templates/`: versioned Feishu schemas, cards, dashboards, and analysis document templates.
- `runtime/`, `logs/`, `tmp/`: local mutable state, caches, live response excerpts, and scratch files; never committed.
- Existing `work/` and `outputs/`: historical local research only; ignored and never published.

## Task 1: Repository and Skill contract

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `SKILL.md`
- Create: `agents/openai.yaml`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_skill_contract.py`

**Steps:**
1. Write failing tests for Skill frontmatter, required references, executable entrypoint, and absence of scaffold placeholders.
2. Run the focused test and confirm failure.
3. Add the minimal Skill entrypoint, package metadata, public README, MIT license, and CI workflow.
4. Run the skill validator and focused tests.
5. Scan staged content for secrets.
6. Commit with `chore: initialize creator monitor skill`.

## Task 2: Configuration, secrets, and budget guard

**Files:**
- Create: `src/creator_monitor/config.py`
- Create: `src/creator_monitor/budget.py`
- Create: `src/creator_monitor/errors.py`
- Create: `tests/unit/test_config.py`
- Create: `tests/unit/test_budget.py`

**Steps:**
1. Write tests for environment loading, redaction, per-run request caps, cumulative USD cap, and fail-closed behavior.
2. Verify tests fail.
3. Implement immutable configuration and a persistent local spend ledger.
4. Ensure no secret value appears in exceptions or logs.
5. Run unit tests and commit `feat: add safe configuration and budget guard`.

## Task 3: Domain models, normalization, and idempotency

**Files:**
- Create: `src/creator_monitor/domain/models.py`
- Create: `src/creator_monitor/domain/identity.py`
- Create: `src/creator_monitor/domain/dedup.py`
- Create: `src/creator_monitor/domain/metrics.py`
- Create: `tests/unit/test_identity.py`
- Create: `tests/unit/test_dedup.py`
- Create: `tests/unit/test_metrics.py`

**Steps:**
1. Write failing tests for `platform:account_id`, `platform:content_id`, `platform:comment_id`, and time-bucket snapshot keys.
2. Add fixtures covering duplicate pages, edited captions, unchanged metrics, increasing metrics, missing fields, and cross-platform ID collisions.
3. Implement normalized account, content, comment, snapshot, run, and dead-letter models.
4. Implement within-batch deduplication and deterministic metric deltas.
5. Verify conservation counts and commit `feat: add normalized creator monitoring domain`.

## Task 4: TikHub client and platform adapters

**Files:**
- Create: `src/creator_monitor/tikhub/client.py`
- Create: `src/creator_monitor/tikhub/douyin.py`
- Create: `src/creator_monitor/tikhub/xiaohongshu.py`
- Create: `references/tikhub-endpoints.md`
- Create: `tests/contract/test_douyin_adapter.py`
- Create: `tests/contract/test_xiaohongshu_adapter.py`

**Steps:**
1. Record selected current TikHub endpoints, parameters, pagination fields, billing warnings, and response fields from official docs.
2. Write contract tests against redacted fixtures before live calls.
3. Implement a retrying client with request IDs, timeout classification, `Retry-After`, caching, and budget checks.
4. Implement Douyin account, posts, detail, and comments normalization.
5. Implement Xiaohongshu account, notes, detail, and comments normalization.
6. Run fixture contract tests and commit `feat: add tikhub platform adapters`.
7. Only after all offline tests pass, make the minimum live calls needed to refresh fixtures and record spend.

## Task 5: Feishu Base provisioning through lark-cli

**Files:**
- Create: `templates/base-schema.yaml`
- Create: `templates/views.yaml`
- Create: `templates/formulas.yaml`
- Create: `src/creator_monitor/feishu/cli.py`
- Create: `src/creator_monitor/feishu/bootstrap.py`
- Create: `tests/unit/test_feishu_commands.py`

**Steps:**
1. Read the current lark-base field, formula, record, view, and dashboard references before constructing payloads.
2. Define two main tables: `账号库` and `内容库`.
3. Define system tables: `指标快照`, `运行日志`, `失败队列`, plus a supporting `评论库` for sampled comment insight.
4. Write tests for generated lark-cli commands and JSON payloads without calling Feishu.
5. Implement idempotent bootstrap that records every returned real Base/table/field/view ID.
6. Create the live Base with `--as user`, then read back all tables and fields.
7. Commit `feat: provision feishu creator monitoring base`.

## Task 6: Base record synchronization

**Files:**
- Create: `src/creator_monitor/feishu/records.py`
- Create: `src/creator_monitor/services/sync_accounts.py`
- Create: `src/creator_monitor/services/sync_content.py`
- Create: `src/creator_monitor/services/refresh_metrics.py`
- Create: `tests/integration/test_sync_idempotency.py`

**Steps:**
1. Write failing tests for candidate-key lookup, split create/update, unchanged records, serial batches, snapshots, and failed writes.
2. Implement candidate-only lookup rather than full-table scans.
3. Implement batches of at most 200 and serialize writes per table.
4. Advance cursors only after all relevant writes succeed.
5. Run offline integration tests.
6. Execute live first sync and read back inserted records.
7. Execute live second sync and prove zero duplicates.
8. Commit `feat: sync creator data idempotently to feishu`.

## Task 7: Media archive, comments, and analysis documents

**Files:**
- Create: `src/creator_monitor/services/archive_media.py`
- Create: `src/creator_monitor/services/sync_comments.py`
- Create: `src/creator_monitor/services/analyze_content.py`
- Create: `templates/analysis-document.md`
- Create: `tests/unit/test_comment_selection.py`
- Create: `tests/integration/test_analysis_pipeline.py`

**Steps:**
1. Test comment selection for new, high-growth, and manually flagged content.
2. Test fallback behavior for expiring media, upload errors, empty ASR, and document creation errors.
3. Implement Feishu attachment upload and source URL fallback.
4. Implement one-page comment sampling with deduplication.
5. Implement analysis document creation, folder placement, status transitions, and link writeback.
6. Run one live content analysis and read back the resulting Feishu document.
7. Commit `feat: archive media and generate analysis documents`.

## Task 8: Reports, six views, and dashboard

**Files:**
- Create: `templates/report-card.json`
- Create: `templates/dashboard.yaml`
- Create: `src/creator_monitor/services/report.py`
- Create: `src/creator_monitor/feishu/dashboard.py`
- Create: `tests/unit/test_report_rankings.py`

**Steps:**
1. Test ranking rules for growth Top 10, save-rate Top 3, stalled growth, and threshold labels.
2. Create six views: all content, inbox, breakout ranking, knowledge ranking, inspiration gallery, and remake kanban.
3. Create KPI, trend, distribution, and ranking dashboard blocks serially.
4. Run the supported smart arrangement once for the new dashboard.
5. Read back dashboard blocks and computed data; compare the rendered interface with the source article.
6. Send one live Feishu report card and verify delivery.
7. Commit `feat: add feishu reports views and dashboard`.

## Task 9: CLI, health checks, and Codex scheduled tasks

**Files:**
- Create: `src/creator_monitor/cli.py`
- Create: `scripts/creator-monitor`
- Create: `src/creator_monitor/services/doctor.py`
- Create: `references/operations.md`
- Create: `tests/integration/test_cli.py`

**Steps:**
1. Add CLI tests for `bootstrap`, `account-sync`, `content-sync`, `media-archive`, `metrics-refresh`, `content-analyze`, `doctor`, `scheduled-sync`, and `daily-report`.
2. Implement structured JSON summaries and stable exit codes.
3. Run `doctor` against live TikHub/Feishu configuration within the budget guard.
4. Create a project-level Codex cron automation for periodic sync and one for the 09:00 report.
5. Wait for one real scheduled execution, then verify Base records and run logs.
6. Pause the MVP automations after proof to protect remaining TikHub credit.
7. Commit `feat: add operational cli and codex automations`.

## Task 10: Generated explanatory images

**Files:**
- Create: `docs/images/skill-system-architecture.png`
- Create: `docs/images/five-capabilities-loop.png`
- Create: `docs/images/data-flow-and-dedup.png`
- Create: `docs/images/skill-vs-workflow.png`

**Steps:**
1. Read ImageGen prompting guidance.
2. Generate each bitmap separately with the built-in ImageGen tool in a clean hand-drawn editorial style inspired by, but not copied from, the source article.
3. Inspect every image for Chinese text accuracy, diagram direction, visual hierarchy, and absence of unrelated brands.
4. Iterate only the failed dimension, then copy final assets into `docs/images/`.
5. Reference the assets from README and the rewritten Feishu tutorial.
6. Commit `docs: add skill architecture illustrations`.

## Task 11: Rewritten Feishu tutorial

**Files:**
- Create: `docs/tutorial-draft.md`
- Create: `docs/screenshot-checklist.md`

**Steps:**
1. Rewrite the full source article around Codex Skill + TikHub + Feishu while preserving its business story and observable outcomes.
2. Replace every Coze workflow explanation with the implemented Skill command and verified behavior.
3. Insert generated diagrams and explicit product screenshot placeholders with capture instructions.
4. Create a user-owned Feishu Docx with `--as user` and upload the complete content.
5. Insert generated images into the document.
6. Read back the full document and preview all inserted media.
7. Commit `docs: publish skill based feishu monitoring tutorial`.

## Task 12: Release and end-to-end acceptance

**Files:**
- Update: `README.md`
- Update: `docs/troubleshooting.md`
- Create: `docs/acceptance-report.md`

**Steps:**
1. Run unit, contract, integration, Skill validation, lint, and secret scans.
2. Verify first-run create, second-run idempotency, snapshot delta, comment dedup, attachment visibility, document creation, report delivery, scheduled execution, and dashboard data.
3. Install the Skill from the public GitHub repository into a clean temporary Codex skills directory and run `doctor`.
4. Verify repository visibility and every public link.
5. Tag `v0.1.0`, push the tag, and create a GitHub release.
6. Deliver the GitHub repository, Feishu tutorial, Base, dashboard, and acceptance evidence links.

