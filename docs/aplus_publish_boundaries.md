# A+ Editorial And Publish Boundaries

## Stable validated checkpoint

The validated A+ payload is treated as a stable editorial checkpoint.

- Editing the working draft updates `draft_payload`
- Background image generation updates `draft_payload` only
- `validated_payload` is not mutated by async image jobs
- publish preparation continues to use the last explicitly validated payload

This means image changes created after validation do not silently alter the last approved editorial version.

## Current preview vs publish behavior

The Studio preview is currently an editorial and visual review surface.

- uploaded, selected, and generated images can appear in the editor and preview
- the current publish preparation flow does **not** map those image selections into the Amazon payload yet
- publish preparation currently includes text content and `imageBrief` only

Until Amazon image mapping is added to the publish adapter, the UI should always describe image preview as editorial-only rather than publish-faithful.
