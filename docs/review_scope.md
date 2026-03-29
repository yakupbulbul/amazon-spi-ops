# Code Review Scope

This repository contains a full-stack Amazon seller operations platform.

The goal of this pull request is to perform a thorough system-level code review before starting the next major development phase.

This review should focus on platform quality, architectural consistency, production-readiness, and hidden risks across the full stack.

---

## Review Objectives

We want to validate that the current implementation is robust enough to serve as the foundation for future development.

The review should identify:

- critical bugs
- hidden data integrity issues
- architecture weaknesses
- unsafe assumptions
- validation gaps
- async workflow risks
- security concerns
- missing tests
- refactor opportunities
- production-readiness risks

This review is intended to cover the entire platform, not just the A+ Studio.

---

## Platform Scope

### 1. Backend
The FastAPI backend currently handles:
- product and inventory-related APIs
- A+ draft generation flows
- multilingual translation flows
- asset upload and retrieval APIs
- optimization/scoring responses
- service-layer orchestration for generation, validation, and preview support

Review focus:
- API design consistency
- request/response schema safety
- service boundaries
- validation coverage
- error handling
- backward compatibility risks
- coupling between routes, services, and schemas

---

### 2. Frontend
The React frontend currently includes:
- product and A+ Studio workflows
- multilingual draft editing
- image upload / selection / generation UI
- preview flows
- scoring and optimization panels
- module editing and asset-related state handling

Review focus:
- component boundaries
- state management quality
- maintainability of large page-level components
- UX consistency
- resilience to partial or invalid backend data
- editor vs preview separation
- long-term scalability of the UI structure

---

### 3. Async Worker System
The platform uses background processing for async workflows such as image generation and related state transitions.

Review focus:
- job lifecycle correctness
- retry behavior
- failure handling
- race conditions
- duplicate execution risks
- state transition safety
- consistency between backend DB state and worker activity

---

### 4. Image and Asset System
The platform now supports:
- reusable asset library
- file uploads
- media serving
- per-module image modes
- generated images
- uploaded images
- selected existing assets
- reference-based image generation inputs

Review focus:
- upload validation
- unsafe file handling risks
- media access patterns
- asset lifecycle correctness
- orphaned asset risks
- invalid asset reference handling
- consistency between generated/uploaded/selected asset states
- preview behavior when assets are missing or invalid
- future compatibility with Amazon publish workflows

---

### 5. Multilingual A+ Generation
The system supports:
- source language / target language workflows
- optional auto-translation
- preservation of structured module data during translation
- localized draft creation and editing

Review focus:
- data integrity during translation
- preservation of non-text fields
- multilingual schema safety
- accidental mutation of IDs, statuses, asset references, URLs, and control fields
- consistency of translated drafts in editor, preview, and future publish steps

---

### 6. A+ Content Generation and Optimization
The platform includes:
- AI-assisted A+ draft generation
- module-based A+ structure
- optimization scoring
- section insights
- warnings
- missing-section detection
- quality heuristics

Review focus:
- correctness of optimization heuristics
- realism of scoring
- false positives / false negatives
- quality of actionable suggestions
- separation between generation logic and optimization logic
- preview vs publish mismatch risks
- schema compatibility with future Amazon publish workflows

---

### 7. Product and Inventory Workflows
The platform also includes broader seller operations logic beyond A+.

Review focus:
- product workflow consistency
- inventory-related API robustness
- stock/price flow safety
- future extensibility for Amazon SP-API integration
- hidden assumptions that may break real marketplace data flows

---

### 8. Notifications and Integrations
The platform includes integration-oriented logic such as Slack notifications and OpenAI-backed workflows.

Review focus:
- integration boundaries
- secret handling
- failure behavior
- retry strategy
- observability gaps
- unsafe assumptions in external-provider workflows

---

## Key Review Areas

Please review the codebase with special attention to the following categories.

### A. Architecture and Boundaries
- Is the architecture coherent across backend, frontend, and worker?
- Are responsibilities separated clearly?
- Are services, schemas, routes, and UI components properly layered?
- Are there areas where logic is leaking across boundaries?

### B. Data Integrity and Schema Safety
- Are schemas stable and future-proof?
- Are draft/module/image structures safe under edits, translation, async updates, and preview?
- Are optional fields handled consistently?
- Are there hidden assumptions that could corrupt state?

### C. Async and State Transition Safety
- Are async operations idempotent where needed?
- Could retries duplicate work or corrupt status?
- Are image generation states reliable?
- Are there race conditions between UI, API, and worker state?

### D. Preview and Future Publish Readiness
- Could preview output diverge from actual publish payload expectations?
- Are there structural mismatches between UI editing models and future Amazon A+ publish requirements?
- Are current abstractions likely to hold when real publish flows are added?

### E. Security
Please inspect for:
- unsafe file upload handling
- weak content-type/file-type validation
- path traversal or unsafe file serving risks
- asset exposure risks
- leaked or mishandled secrets
- unsafe API key usage
- insufficient validation on external-provider inputs

### F. Testing and Reliability
- What critical logic is currently under-tested?
- What integration scenarios are missing?
- What async/image/multilingual edge cases need coverage?
- Are current tests sufficient to prevent regressions?

### G. Production Readiness
- What would likely break first in production?
- What observability/logging gaps exist?
- What operational concerns are missing?
- What should be hardened before scaling or adding major features?

---

## Requested Review Output

Please return the review in this structure:

1. **Critical issues**  
   Issues that could cause data corruption, security problems, broken workflows, or serious production failures.

2. **Important issues**  
   Significant problems that may not break immediately but should be addressed before major expansion.

3. **Medium / low priority improvements**  
   Maintainability, clarity, and UX issues that can be scheduled after the critical fixes.

4. **Refactoring suggestions**  
   Specific structural improvements to reduce technical debt and improve extensibility.

5. **Missing test coverage**  
   Key scenarios, edge cases, and integration paths that should be tested.

6. **Production-readiness risks**  
   Operational, deployment, scalability, security, and observability risks.

---

## Notes

- The repository is currently clean and pushed.
- This review is intentionally broader than a page-level or feature-level review.
- We want to validate the platform foundation before introducing the next major feature set.
- Please prioritize issues that could impact future Amazon publishing, multilingual correctness, asset integrity, async job safety, and long-term maintainability.
