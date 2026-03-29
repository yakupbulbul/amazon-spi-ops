# A+ Live Publish Test Runbook

This runbook is for the currently supported real Amazon A+ publish subset only:

- `hero` -> `STANDARD_HEADER_IMAGE_TEXT`
- `feature` -> `STANDARD_SINGLE_IMAGE_HIGHLIGHTS`
- `faq` -> `STANDARD_TEXT`

`comparison` remains editorial-only and must not be present in the draft you submit for live testing.

## Safe vs live environments

Use these environment files intentionally:

- `.env`
  - default local development profile
  - keep `APLUS_LIVE_PUBLISH_ENABLED=false`
  - safe for generation, editing, validation, preview, and internal publish-payload inspection
- `.env.live.amazon`
  - dedicated seller-account live test profile
  - set `APLUS_LIVE_PUBLISH_ENABLED=true`
  - use only for controlled Amazon submission tests

Do not turn on live publish in the default local `.env`.

## Preconditions

Before starting one live test:

1. Use a seller account and marketplace that are already working for the current SP-API configuration.
2. Choose one non-critical ASIN that you can safely use for a controlled A+ submission test.
3. Make sure the draft contains only supported modules:
   - one `hero`
   - one or more `feature`
   - optional `faq`
4. Use only JPEG or PNG images.
5. Check image minimums:
   - hero: at least `970 x 600`
   - feature: at least `300 x 300`
6. Keep image files under `APLUS_UPLOAD_MAX_BYTES`.

## Live environment setup

Create the dedicated live env file:

```bash
cd /Users/yakupbulbul/Documents/codex/amazon-spi
cp .env.live.amazon.example .env.live.amazon
```

Fill in the live Amazon credentials and seller values in `.env.live.amazon`.

Start the stack with the live profile:

```bash
cd /Users/yakupbulbul/Documents/codex/amazon-spi
docker compose --env-file .env.live.amazon up -d --build backend worker frontend nginx postgres redis
```

Verify the backend is using the live profile:

```bash
cd /Users/yakupbulbul/Documents/codex/amazon-spi
docker compose --env-file .env.live.amazon exec backend printenv APLUS_LIVE_PUBLISH_ENABLED
```

Expected value:

```text
true
```

## Exact manual test flow

1. Open [http://127.0.0.1:8080/aplus](http://127.0.0.1:8080/aplus).
2. Log in with the configured admin account.
3. Select one real catalog product that belongs to the live seller account.
4. Generate or open an existing draft.
5. Make sure the draft contains only:
   - hero
   - feature
   - faq
6. Remove any `comparison` module before validation.
7. Upload or select valid JPEG/PNG assets for every hero and feature module.
8. Click `Validate draft`.
9. Confirm the readiness panel shows the draft as ready for Amazon submit.
10. Click `Submit to Amazon review`.
11. Watch the lifecycle panel for these transitions:
    - `draft`
    - `assets prepared`
    - `validated`
    - `submitted`
    - `in review`
12. Capture the `content reference key` shown in the lifecycle panel.
13. If Amazon responds immediately with a terminal state, record:
    - `approved`, or
    - `rejected` plus the rejection reasons shown in the UI
14. If the submission stays in review, wait and poll again from the Studio later.

## What to record from the test

For the first live run, record:

- selected SKU
- selected ASIN
- marketplace
- module mix
- content reference key
- current lifecycle status
- any Amazon warnings
- any rejection reasons

## Current known boundaries

- The live pipeline currently supports only the subset listed at the top of this file.
- `comparison` is not part of the live publish contract yet.
- The lifecycle panel reflects Amazon metadata refresh for the latest publish job, but long review cycles may still require later rechecks.
