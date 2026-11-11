---
name: maintenance-round
description: A periodic maintenance round for an AI-agent project's instruction layer (CLAUDE.md / AGENTS.md / GEMINI.md, Cursor or Copilot rules, skills, subagents, lessons files) and for the facts those files claim about the project. It turns repeated lessons into rules, audits structure, tests every "this is true" sentence against reality, looks for silent failures, then proposes simplification. It stops exactly twice for the human, and nothing that changes meaning is applied without an exact, approved diff. Use every 2-4 weeks, after a burst of agent work, after a model change, or when the instructions feel bloated, contradictory or wrong. Not for fixing one bug, building features, or a single doc edit.
---

# Maintenance Round

A round chains passes over the instruction layer. Each pass has one lens, writes its findings in a fixed shape, and hands the next pass a cleaner state. The orchestrator owns the two gates, the abort rule and the report; the passes never ask the human anything.

## The rules the round runs on

1. **Finding a problem is not permission to fix it.** Audits are flag-only. Their fixes leave as proposals with exact old and new text.
2. **Free vs diff-first.** Exactly three things are free (applied, then reported): adding a twice-seen lesson as a new bullet under a lessons or gotchas heading that already exists, wherever that heading lives; deleting a lesson bullet the code made obsolete; updating the round's own ledgers. Everything else is a diff for the human, including any change to an existing line, any new text in a skill or agent body, and any deletion of a file. A round with zero free applies is normal. Nothing outside the instruction layer (data, history, infrastructure, dependencies) is ever changed by the round; those are proposals.
3. **Two gates, never on silence.** Gate 1 after the audits, gate 2 after the simplification package. Starting the round grants neither. While an interactive gate waits, the round keeps doing only the work the answer cannot change; a non-interactive run stops at the gate.
4. **Measure before, re-measure after every step, stop on regression** (abort rule, below).
5. **A number carries its command and its denominator.** A zero without a denominator is indistinguishable from a check that looked at nothing. Label every zero VERIFIED (candidates existed and were each cleared) or VACUOUS (nothing existed to check). A check that cannot see a planted fault is BLIND and its "clean" is NOT MEASURED.
6. **A claim is not a fact until checked against the primary artifact**: the scheduler, the file, the process list, the remote, the endpoint. A document agreeing with another document is not evidence. This includes the round's own subagents: their "done", "empty" and "not found" are claims.
7. **Every removal is recorded verbatim** before it lands, so any cut can be put back.

## Before you start: detect the environment (orchestrator, 2 minutes)

Record each answer in the report header.

| Question | How to find out | If absent |
|---|---|---|
| Runtime and model | Your own system prompt / `claude --version` / the CLI's version flag | Write "unknown"; the model-change trigger then counts as due |
| Subagents available? | Claude Code: the Agent/Task tool. Others: check your tool list | Run every step yourself, in order; write each step's result into the report before starting the next, and re-read only the report, not your earlier reasoning |
| Interactive? | Can you ask the human and wait (AskUserQuestion, chat)? Headless runs (`claude -p`, `codex exec`, CI) cannot | Non-interactive gate protocol, below |
| Git? | `git rev-parse --show-toplevel` | No-git protocol, below |
| Repos | `mr.py git .` lists every repo at or under the root (depth 3); or `find . -maxdepth 3 -name .git` | One-repo or no-repo |
| Python 3? | `python3 --version` | Do the helper's work by hand: `references/checks.md § Without the helper` |
| Previous round | `.maintenance/baselines.md` and the newest `.maintenance/runs/*/REPORT.md` | First run: scope the last 30 days, create the state folder, and say "first round, no baseline" in every comparison row |
| Owners | Per-agent folders, CODEOWNERS, a routing table naming owners | One owner: the human. Otherwise a fix to another owner's file is always a staged proposal, even when a free class would apply |

The helper (Python 3 stdlib, no install) is the mechanical half: inventory and sizes, limits, dead path references, prompt-pattern signals, git hygiene, baseline/compare for the abort rule, and its own negative controls. It lives in this skill's folder, not in the project: wherever this skill writes `mr.py`, run `python3 <this skill's folder>/scripts/mr.py`, from the project root. Run `mr.py selftest` first. A FAIL means its numbers are BLIND this round: say so and use the manual commands. The helper never scans its own skill folder, `.maintenance/` or what git ignores (`references/checks.md`).

## State the round keeps

Markdown and JSON, at the root of the project (or of the main repo in a multi-repo setup). Formats: `references/formats.md`.

```
.maintenance/
  baselines.md          limits chosen by the human, closing numbers of each round, round dates
  limits.json           optional: limit overrides, exclude list
  held-lessons.md       lessons seen once, with seen-count; aged out after 3 rounds untouched
  proposals.md          staged proposals: id | plain-language title | target | diff file | status | rounds open
  rule-sightings.md     per rule: last round any finding touched it (the sunset list)
  probe-cases.md        behaviour probe cases (optional)
  lessons.md            lessons about running the round itself; read at every step 0
  runs/YYYY-MM-DD/
    REPORT.md           the round report
    baseline.json       mr.py baseline at step 0 (and after-step snapshots)
    diffs/              one file per proposed change
    removed-verbatim.md every line removed or rewritten, verbatim
    GATE-1.md, GATE-2.md, ANSWERS-1.md, ANSWERS-2.md   (non-interactive runs)
    backup/             pre-edit copies (no-git runs only)
```

On a first run, create `baselines.md` and `lessons.md` at step 0 (a title line is enough) and update both at every stop. `.maintenance/` is committed by default (all but `backup/`), following the project's own commit rules: `references/environments.md § Commits`. On a first round nothing is committed and no branch is created until the human has answered gate 1's SETUP block.

## The sequence

```
0  open report, baselines, controls, model trigger           orchestrator
1  distil lessons (opening, full)                            subagent  - strongest model for clustering
2  structure audit (flag-only)                               subagent
3  claims vs reality (flag-only)                             subagent  - finds the most
3h silent-failure health pass (flag-only)                    subagent  - parallel, any time after 1
4  GATE 1                                                    orchestrator
5  distil (closing, scoped: apply approved + new lessons)     subagent
6  owner-context pass (only if the project keeps one)        subagent
7  simplification package, then GATE 2                      subagents draft, orchestrator asks
8  apply the simplification                                  subagent (fresh)
8b behaviour probe (when routing text changed or model changed)  orchestrator
9  close                                                     orchestrator
```

Why this order: distilling first drains the lessons backlog, so the audit measures drift and not backlog. The structure audit precedes the claims check, which assumes the files it compares exist. The audits only stage; the closing distil is the one place approved changes land. Simplification comes last, against the final state.

Each step's brief: `references/briefs.md`. Pass it verbatim with the placeholders filled; quote the human's words, never paraphrase them.

### Step 0: open the report and take baselines (orchestrator)

1. Read `references/lessons-learned.md` and `.maintenance/lessons.md` (if it exists) before anything else.
2. Create `runs/<date>/REPORT.md` from the skeleton in `references/formats.md`, with one empty section per step. An empty section at close means a skipped step, and the report says so.
3. Bump `rounds open` on every proposal carried in STAGED from an earlier round. Header: runtime and version, the exact model id you run on, date, the environment table above, and `git status --short` plus the branch of every repo. Record dirty files that are not yours; never commit them.
4. `mr.py selftest`, then `mr.py baseline . --save .maintenance/runs/<date>/baseline.json`, then `mr.py limits`, `inventory`, `refs`, `signals`, `git`. Paste the summary lines into the report's baseline table.
5. **Model-change trigger.** Compare the model id with the previous report's. First round: just record the id. Changed: this round adds the re-baseline pass. Model-fossil signals (PP-6) and pressure language (PP-1) join step 7's target list. The behaviour probe (8b) runs at the start and at the end.
6. **Behaviour probe baseline** (optional; recommended when the project routes work to skills or subagents): see `references/checks.md § Behaviour probe`.

**Abort rule.** After every step, run `mr.py compare . --against .maintenance/runs/<date>/baseline.json --allow-change <files this step was approved to change>`. Exit 3 stops the chain. After a step that changed an instruction file, re-run `mr.py selftest` too. Regressions are: a new file over its limit, an instruction file whose content changed without an approved diff, a new dead reference or missing unit, a removed instruction file, a negative control that flipped PASS→FAIL, a probe case that passed and now fails. Report the regression and the step that caused it. Do not go on "and fix it later": every later step would measure a broken state. A failure already present at step 0 is pre-existing: label it so and never attribute it to a step. After an approved step lands, refresh the baseline (`baseline --save` to `baseline-after-<step>.json`) and compare the next step against that.

### Step 1: distil lessons, opening pass (subagent)

Brief: `references/briefs.md § Distil`. It collects lessons since the last round from every source that exists, with a count per source. It clusters them by meaning. It promotes only what repeated (never a single sighting) to where the actor reads it when acting, and holds one-offs in `held-lessons.md`. A lesson that recurs despite its rule is a **RULE FAILURE**: the fix is structural (a step, a gate, a hook, a test), not more words. Person-claims are routed, never promoted. It updates the sunset list and balances its books: `triaged = promoted + held + folded + discarded`. Free items are applied and reported; everything else becomes a diff.

### Step 2: structure audit (subagent, flag-only)

Brief: `references/briefs.md § Structure audit`; checklist `references/checks.md § Structure`. It writes only its report section and `diffs/`. Every measured row carries value, command and denominator; a row it cannot fill is NOT MEASURED, never omitted.

### Step 3: claims vs reality (subagent, flag-only)

Brief: `references/briefs.md § Claims`; arms and the verify-against table: `references/checks.md § Claims`. The arm that finds the most is B2: every sentence asserting current state ("runs nightly", "is backed up", "always pushed", "we use pnpm", "is private") is tested against the primary artifact, both polarities ("fixed" is checked fixed, "broken" is checked still broken), plus the reverse direction (things that run but no document mentions). The report also lists **true statements that merely matched**, so the next round doesn't "fix" them, and **could not determine**, with what would settle it.

### Step 3h: silent-failure health pass (subagent, parallel, read-only)

Brief: `references/briefs.md § Health`. It covers scheduled jobs, backups (does the newest copy exist, and is the work that matters inside it), pushes, secret-shaped file names, disk, certificates and outdated tools; list in `references/checks.md § Health`. Upgrades are proposals, never applied.

### Step 4: GATE 1 (orchestrator)

Present every diff and proposal from steps 1-3h, plus everything carried in `proposals.md`, in the gate format of `references/formats.md § Gate question`:
- **BATCH:** the changes one "yes" applies. Only edits inside the instruction layer with one obvious fix and high-confidence evidence.
- **DECISIONS:** numbered, each with options and a recommended default. Anything with more than one defensible answer (two files disagree, a false claim whose truth only the human knows), any removal of a rule, and everything the human must apply themselves (formats.md § Proposal, kind `human-applied`).
- **SETUP:** first round only. The defaults the round will use unless the human says otherwise: limits, where `.maintenance/` is kept, no paid probe. One block, not one question each.
- **FYI:** no action implied.

After each of steps 1-3h returns, the orchestrator mirrors its staged diffs into `proposals.md`, stages a proposal for any health finding that needs one, and marks the rules the findings touched in `rule-sightings.md`.

Each item stands on its own: what changes, in which file, why, the evidence. An id is a suffix, never the label. A question that deletes, publishes or touches production puts the safe option first, because an accidental Enter takes the first option. Include anything step 1 routed as a person-claim, and the probe budget only when a probe is due and the human has not ruled it out. Record the answers verbatim. A fix the human turns down for a real finding is ACCEPTED, and later rounds do not propose it again. Unanswered items stay STAGED; at 3 rounds open an item is asked as "apply or withdraw". A gate longer than about 12 items asks the critical and high ones and lists the rest, still STAGED, under FYI as deferred.

### Step 5: distil, closing pass (subagent, scoped)

Brief: `references/briefs.md § Distil (closing)`. This is collect + apply, not a re-promotion. It applies exactly the approved items and lessons written since step 1 (the audits' own notes, the health pass's warnings). It does not re-cluster the period, because that reproduces the same candidates and a second approval round. Every apply follows `references/checks.md § Apply protocol`: re-read the live lines first, verify the done, review the round's own commits. An item that trips the abort rule is undone and marked BLOCKED; the others still apply. Every proposal ends the step with a status from `references/formats.md § Statuses`.

### Step 6: owner-context pass (subagent; only if the project keeps a profile or context file about the human)

Brief: `references/briefs.md § Owner context`. Tier A (consolidation, compression, corroboration of what the human already said directly) is applied and reported. Tier B (any new claim about the human) counts only after the human confirms it as theirs; it rides gate 2. Tier C (a rewrite changing a line's meaning) is shown as a diff at gate 2. It never blocks the round: unanswered tier B items stay `awaiting-confirmation`. No such file: skip with one line.

### Step 7: simplification package, then GATE 2

Brief: `references/briefs.md § Simplify`; classes and keep-list: `references/simplify.md`.
- **Target list** = files over a limit ∪ files changed this round ∪ files carrying mr.py signals ∪ DORMANT rules ∪ (model changed) PP-1/PP-6 hits.
- One drafter per owner (or per file group) can run in parallel. Drafters write to `diffs/simplify-*.md` and apply nothing.
- Every hunk names its class; length alone is never a reason. Keep-list items stay even when a signal matches.
- Before removing a kind of line everywhere, grep for a step that reads it.
- A file that earns no hunk is reported clean; an empty package ends the round at step 9, unless step 6 left items to confirm.

Present the package hunk by hunk (class, why, words before → after, confidence) in gate 1's shape, high-confidence hunks in the batch, together with step 6's tier B and C items. Items answered "later" at gate 1 are not asked again this round. Nothing the human does not take is applied.

### Step 8: apply the simplification (fresh subagent)

Brief: `references/briefs.md § Simplify apply`. Pre-flight: re-run the controls and `mr.py compare`. Apply only the taken hunks, each verified with `references/checks.md § Apply protocol`. Record removals verbatim; one hunk at a time. Post-flight: a NEW control failure blocks the round until it is repaired or the human explicitly accepts it. Repair means fixing what the cut broke, never deleting the check that noticed.

### Step 8b: behaviour probe (orchestrator)

Run it when the model changed, when step 5 or 8 touched routing or description text, or when a skill or agent was added or removed. Same cases, same command as the baseline. If a case regresses, re-run the failing cases against the pre-round text (a `git worktree add` at the round's start commit, or the `backup/` copies) to tell whether the round caused it. Report what was measured, including "cause open". A partial or aborted run is not a baseline and says so.

### Step 9: close (orchestrator)

Fill the report (`references/formats.md § Report skeleton`):
- the lead summary in prose: the 2-3 findings that could mislead or break something, severity first;
- one step line per step in the fixed shape;
- gate outcomes with the human's words verbatim;
- baselines before → after;
- what is carried to next round;
- the run-close block.

Append the round's own lessons to `.maintenance/lessons.md`. Update `baselines.md`. If git is in use, commit the round's state with explicit pathspecs.

**Stopping before step 9** (a gate in a non-interactive run, an abort): add a line to the report's Stops section, fill the lead summary, the step lines so far and "Carried to next round", and mark Run close "not reached". An abort also writes `ABORT.md` (`references/environments.md § Resuming`).

## Environments that differ

Non-interactive runs stop at each gate by writing `GATE-<n>.md` and resume from `ANSWERS-<n>.md`. No subagents, no git, monorepos and other runtimes' instruction files each have a protocol: `references/environments.md`.

## Rules learned the hard way

`references/lessons-learned.md`, from real rounds. The three that matter most: verify the done against the diff that landed, review the round's own commits, re-read the live lines before applying a drafted diff.

## Cost and speed

- **Parallel:** step 3h with steps 1-3; collectors inside step 1 (one per source); step 7 drafters (one per owner).
- **Model tiers:** the strongest model for clustering, routing lessons, the claims arm and the orchestrator; a fast or mid model for collection, drafting and applies.
- Record each subagent's token or cost figure in its step line when the runtime reports it, otherwise `n/a`.
- **Small project** (fewer than about 15 instruction files): steps 1-3h run as one pass with one report section each; `rule-sightings.md` lists only the bullets of top-level files; the probe is skipped unless asked for; gate 1 groups related fixes into one item with lettered parts (the human can still answer "yes except 1b"). The gates and the abort rule never merge.
