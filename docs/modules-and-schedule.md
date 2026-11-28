# MediCore — Modules, Tasks & Daily Schedule

**Status**: Living plan, owner-approved structure (2026-11-22). Updated when a module
starts, finishes, or a decision changes it.

## Rules (owner-set)

1. **Specs and complete documentation before coding** — no implementation work
   starts on a module until its spec is approved.
2. **Daily work** — tasks are worked on every day; progress is reported in the
   8pm PKT daily check-in.
3. **Modules and tasks** — the project is divided into modules `M1, M2, M3, ...`.
   Each module has tasks `M1-T01, M1-T02, ...`. A task may have sub-tasks
   `M1-T01-A, M1-T01-B, ...` when it needs breaking down; otherwise the task
   stands alone.
4. **Commit format** — every commit names its task, in this exact format:

   ```
   M1-T01 (feat/fix/docs/test/chore): short description
   ```

   Examples: `M3-T03 (feat): add Patient model and MRN generation`,
   `M1-T05 (test): cover role-based access denial`, `M0-T01 (docs): add Spec 002`.
   A commit that does not belong to a task does not get made.
5. **Module completion = tag + version** — when a module is finished (all its
   tasks done, tests passing, spec converged), it is tagged on GitHub with a
   version so every module is trackable. Tag format: `M<n>-v<major>.<minor>.0`
   (first release of a module is `v1.0.0`, e.g. `M1-v1.0.0`). The tag points at
   the merge commit that completed the module, and the release notes list the
   module's tasks and what was verified.

## Modules

| Module | Name | Spec | Status | Version (when tagged) |
|---|---|---|---|---|
| M0 | Foundation & Documentation | 001–009 + docs/ | Done — specs + docs written; scaffold unparked and merged 2026-11-23 (upstream PR #5) | — |
| M1 | Auth & RBAC | 002 | **Complete — tagged M1-v1.0.0** 2026-11-27 on `cbfc7f0` (PR #12 merge) | M1-v1.0.0 |
| M2 | Hospital Setup | 003 | Spec 003 **Approved** 2026-11-25 (D-08–D-15); T03 backend merged 2026-11-26 (upstream PR #11); T04 frontend merged 2026-11-27 (upstream PR #13, main `307375f`); T05 tests merged 2026-11-28 (upstream PR #14, main `b249347`); T06 review in progress | — |
| M3 | Patient Registration | 001 | **Approved** 2026-11-22 (D-01–D-13) | — |
| M4 | Appointments | 004 | Spec draft, awaiting approval | — |
| M5 | Encounters | 005 | Spec draft, awaiting approval | — |
| M6 | Laboratory | 007 | **Decided 2026-11-22: Laboratory** is the P1 supporting module | — |
| M7 | Prescription | 006 | Spec draft, awaiting approval — own module (owner decision 2026-11-22) | — |
| M8 | Billing | 008 | Spec draft, awaiting approval — own module (owner decision 2026-11-22) | — |
| M9 | Online Payments | 010 | Spec draft, awaiting approval — own module (owner decision 2026-11-22) | — |
| M10 | Dashboard & Reports | 009 | Spec draft (P1 candidate) | — |
| M11 | Verification & Release | test-strategy, deployment-guide | Not started | — |

## Task template (per module)

| Task | Work | Type |
|---|---|---|
| `M<n>-T01` | Feature specification (spec.md) | docs |
| `M<n>-T02` | Technical plan (plan.md, research, data model) | docs |
| `M<n>-T03` | Backend: models, migrations, API | feat |
| `M<n>-T04` | Frontend: screens, forms, API wiring | feat |
| `M<n>-T05` | Tests: unit, API permission, E2E for the module | test |
| `M<n>-T06` | Review + converge: verify against spec, fix gaps | fix/chore |

Sub-tasks use `M<n>-T0<m>-A`, `M<n>-T0<m>-B`, ... (e.g. `M3-T03-A`: Patient
model + MRN; `M3-T03-B`: registration API + duplicate review).

### Current task list (as of 2026-11-22)

- **M0-T01** — Specs 001–009 written. **Done** (Spec 001 approved; 002–009 draft).
- **M0-T02** — Complete documentation (architecture, data model, API contract,
  UX flows, test strategy, deployment guide). **Done**, this document included.
- **M0-T03** — Application scaffold (Django + React shells). **Done** — unparked and merged 2026-11-23 (upstream PR #5, main `4fcd5f8`).
- **M1-T01 / M1-T02** — Spec 002 written and **approved 2026-11-23** (D-09–D-19).
- **M1-T03** — Auth backend. **Done**, merged 2026-11-23 (upstream PR #6, main `91ff686`).
- **M1-T04** — User-admin API + auth audit events. **Done**, merged 2026-11-24 (upstream PR #7, main `68d3308`).
- **M1-T05** — Frontend auth. **Done**, merged 2026-11-25 (upstream PR #9, main `e606570`).
- **M1-T06** — Review + converge. **Done 2026-11-27** — verified Spec 002 D-01–D-19 against code; one gap fixed (`accounts.enable` audit event on reactivation); module complete, tagged M1-v1.0.0 on `cbfc7f0`.
- **M2-T01 / M2-T02** — Spec 003 written and **approved 2026-11-25** (D-08–D-15).
- **M2-T03** — Organisation backend. **Done**, merged 2026-11-26 (upstream PR #11, main `3d715a7`).
- **M2-T04** — Frontend: departments/staff/services screens. **Done**, merged 2026-11-27 (upstream PR #13, main `307375f`).
- **M2-T05** — Tests: deny beyond create, deactivate/reactivate audit, FR-010 sort/search/pagination, unauthenticated coverage, plus first Playwright E2E journey. **Done**, merged 2026-11-28 (upstream PR #14, main `b249347`; all 4 CI checks green incl. E2E).
- **M2-T06** — Review + converge. **In progress 2026-11-28** — verifying Spec 003 acceptance scenarios against code; two gaps fixed so far (staff↔account link now visible on the user record; deactivated categories no longer offered for new services).
- **M4-T01 / M5-T01 / M6-T01 / M7-T01 / M8-T01 / M9-T01 /
  M10-T01** — specs written, drafts awaiting owner/supervisor approval.
- **M3-T01 / M3-T02** — **Done and approved.**

## Daily schedule

Work runs every day, one task at a time, in module order. The 8pm PKT daily
check-in reports the task worked on, what was finished, and the next task.

| Week | Focus | Exit |
|---|---|---|
| 23–29 Nov 2026 | Specs 002 + 003 approved; M0-T03 scaffold unparked (23 Nov); M1-T03/T04/T05 merged (23–25 Nov); M2-T03 merged (26 Nov); M1-T06 review done + M1 tagged (27 Nov); M2-T04 merged (27 Nov); M2-T05 merged (28 Nov); M2-T06 review underway (28 Nov) | M1 tagged M1-v1.0.0; M2 finishing, a day early |
| 30 Nov–6 Dec | **M2 tagged M2-v1.0.0** (review finishing 28 Nov, ahead of plan); M3 patient registration begins | M2 tagged, M3 underway |
| 7–13 Dec | M3 patient registration (T03 backend, T04 frontend) | M3 underway |
| 14–20 Dec | M3 complete → **tag M3-v1.0.0**; M4 appointments | M3 tagged, M4 underway |
| 21 Dec–3 Jan | M3 complete → **tag M3-v1.0.0**; M4 appointments | M3 tagged, M4 underway |
| Jan 2027 | M4 → **tag M4-v1.0.0**; M5 encounters → **tag M5-v1.0.0** | Outpatient flow complete |
| Feb 2027 | M6 Laboratory → **tag M6-v1.0.0**; M7 Prescription → **tag M7-v1.0.0** | Lab + prescription complete |
| Mar 2027 | M8 Billing → **tag M8-v1.0.0**; M9 Online Payments → **tag M9-v1.0.0** | Billing + payments complete |
| Apr 2027 | M10 Dashboard & Reports → **tag M10-v1.0.0**; M11 verification, security review, deployment, submission | Release candidate |

Dates are a plan, not a promise — a slipped task moves the weeks after it, and
the change is recorded here and in the daily check-in. The Master Plan roadmap
(6–7 months, Phases 0–9) is the outer frame; this table is the working schedule
inside it.

## How a module is marked complete

1. All its T01–T06 tasks are done and committed in the `M<n>-T0<m> (...)` format.
2. Its tests pass; the spec's acceptance scenarios are verified (converge step).
3. The work is merged to upstream main via a Contribute PR.
4. A GitHub tag `M<n>-v1.0.0` is created on the merge commit, with release notes
   listing the tasks and verification evidence.
5. This table is updated: status → Complete, version filled in.
