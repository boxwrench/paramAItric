# Session Transfer Method

This note defines the adopted method for moving ParamAItric work across sessions while staying token-efficient.
Templates for handoffs and startup prompts are in [Appendix A](#appendix-a-handoff-template) and [Appendix B](#appendix-b-next-session-prompt-template).

The goal is not to reconstruct the whole repo every time.
The goal is to preserve:

- current repo state
- current trajectory
- current constraints
- the next useful move

with a bounded startup read.

## Operating Model

ParamAItric work is split into two session roles:

- orchestrator sessions
  - higher-capability models such as ChatGPT or Claude
  - used for synthesis, strategy, hard-problem framing, adoption decisions, and implementation planning
- worker sessions
  - mid-tier models such as Gemini or Kimi
  - used for bounded implementation, smoke runs, refactors, housekeeping, and other well-scoped execution work

This is a workflow method, not a hardcoded tooling dependency.

## Durable vs Temporary Context

Use three context layers:

1. Durable history
   - [`docs/dev-log.md`](./dev-log.md)
   - append major landed work, validation, and durable lessons
2. Temporary restart context
   - `docs/session-handoff-YYYY-MM-DD-<topic>.md`
   - capture only the immediate local state needed for the next session
   - archive superseded handoffs under `docs/archive/handoffs/` once they are no longer the active restart aid
3. Token-conservative startup prompt
   - a short prompt that tells the next session exactly what to read and what not to re-scan

Do not use the dev log as a handoff dump.
Do not use the handoff doc as permanent history.

## Orchestrator Responsibilities

Orchestrator sessions should:

- audit repo state against the active handoff
- decide what is adopted guidance versus working artifact versus private research
- synthesize new research into repo decisions
- write or revise the implementation plan
- choose worker-safe bounded tasks
- write the next session handoff and startup prompt

Orchestrators should not spend tokens rereading the whole repo if the handoff is good enough.

## Worker Responsibilities

Worker sessions should:

- execute bounded tasks from the current implementation plan
- run targeted tests or live smokes
- clean up narrow repo clutter
- report drift, breakage, or ambiguity clearly
- avoid broad canon changes unless the task explicitly calls for them

Workers should be given:

- exact objective
- files or docs to read first
- exact validation to run
- stop conditions

## Startup Contract

A new session should start with a bounded read:

1. read the current handoff doc
2. read the relevant recent slice of [`docs/dev-log.md`](./dev-log.md)
3. read only the files named in the handoff or required by `git diff`
4. audit local repo state against the handoff
5. run targeted validation, not a broad repo reread

Default rule:

- do not review the whole codebase unless the handoff is missing, untrustworthy, or contradicted by the worktree

## End-of-Session Contract

Before ending a meaningful session:

1. update [`docs/dev-log.md`](./dev-log.md) with durable results
2. refresh or replace the active handoff doc
3. include a suggested next-session prompt
4. name the exact validation status
5. call out any drift between:
   - adopted guidance
   - research archive
   - temporary internal artifacts
   - local-only private work

## Handoff Content Rules

A good handoff should include:

- current branch and whether work extends past the last pushed commit
- what landed this session
- what is solid
- what is questionable
- exact validation run and result
- local-only context that matters next session
- the best next move

Keep it concise.
A handoff is a restart aid, not a transcript.

## Token Economy Rules

To conserve resources:

- put durable lessons in the dev log once, not in every prompt
- keep temporary handoff docs short and current
- point the next session at a small reading set
- prefer targeted validation commands over repo-wide test reruns
- prefer implementation plans produced by orchestrators, then execution by workers

If a session starts by rediscovering old context from scratch, the transfer method failed.

---

## Appendix A: Handoff Template

Use this only as a restart aid for the next coding session.
Durable history belongs in [`docs/dev-log.md`](./dev-log.md).

```markdown
# Session Handoff - YYYY-MM-DD - Topic

## Read First

- this handoff
- the relevant recent slice of docs/dev-log.md
- any files explicitly named below

## Current Repo State

- Branch:
- Last pushed baseline:
- Local worktree state:
- This session focused on:

## What Landed

-

## What Is Solid

-

## What Is Questionable

-

## Validation

- Passed:
- Not run:
- Live status:

## Next Move

- Best next step:
- Stop conditions:
- Files/docs to read first:
```

## Appendix B: Next-Session Prompt Template

Use this when starting a new session from an orchestrator-written handoff.
Keep it short and bounded.

```text
We are resuming work in `C:\Github\paramAItric`.

Start by reading:
- <handoff doc>
- docs/dev-log.md
- <1-3 additional files only if needed>

Current pushed commit is:
- <sha> (<subject>)

Working style for this session:
- audit the repo state against the handoff first
- do not assume internal harnesses are trustworthy just because they exist
- prefer targeted validation over broad assumptions
- call out questionable or drifted items explicitly
- preserve the distinction between adopted guidance, research archive, temporary/internal artifacts, and private local work

Current objective:
- <one clear objective>

Do first:
- <first validation or audit step>
```
