# Formats

Every artifact the round writes has one shape, so any session (or a different runtime) can resume from disk without the transcript.

## Finding

One row per finding, in every audit, claims and simplify report.

| Field | Content |
|---|---|
| Location | `file:line` or `file:line-range`; an artifact (cron table, remote, endpoint) where no file applies |
| Evidence | The exact text, quoted, or the command and the line of its output |
| Class | The check, arm or pattern it matches (`S3`, `B2`, `PP-1`, `D1` ...) |
| Why | One or two sentences: what it misleads or breaks |
| Severity | `critical` / `high` / `medium` / `low`, below |
| Confidence | `high` / `medium` / `low`, below |
| Action | `remove` / `rewrite` / `move` / `add` / `flag`, with the exact text for anything but `flag` |

**Severity.**
- `critical`: exposes a secret, publishes something private, or loses data (a backup that does not exist, work in no copy).
- `high`: makes an agent act wrongly (a false claim it will rely on, contradictory rules, a dead path in a procedure step).
- `medium`: wastes effort or context (duplication, over-limit files, stale history).
- `low`: cosmetic.

**Confidence.**
- `high`: checked against the primary artifact, or measured by a check whose negative control passed this round.
- `medium`: hand-read against a documented rule, evidence quoted, not checked against the primary artifact.
- `low`: a heuristic or an unadjudicated signal. Low is always `flag`.

**Flag vs fix.** A finding that matches a documented rule is medium or high and gets a concrete action with its text. "Seems minor" or "judgement call" are reasons the human may decline, never reasons to withhold a proposal.

**Order.** Severity, then confidence. A check that found nothing says so in one sentence, with its denominator.

## Proposal (diff file)

`runs/<date>/diffs/<NN>-<owner-or-area>__<target-file-slug>.md`:

````
Status: STAGED            (later: one of the statuses listed under "Statuses" below)
Id: P-<NN>
Title: <plain language: what changes, where, why - this is what the gate shows>
Target: <path> § <exact heading, quoted from the live file>
Class: <finding class>   Severity: <...>   Confidence: <...>
Free or diff-first: <which, and why>
Evidence: <command + output line, or quote>
Rounds open: 1

OLD (must match the live file exactly once; whole lines, nothing but the text between the fences):
```
<exact text>
```

NEW:
```
<exact text>
```

Verify after apply: <a read-only command whose output proves the change landed; never one that runs project scripts or tests>
````

To delete lines, NEW is the single word `(delete)`. To add lines, OLD is the one existing line the new text goes after (the anchor), and NEW repeats that line followed by the addition. A decision with more than one editing option carries one `NEW (option b):`, `NEW (option c):` block per option, so whichever the human picks can be applied as written. A diff file is named `<NN>-<area>__<target path with / replaced by ->.md`; for kind `human-applied`, the area and a word for the thing it touches. Before staging, read NEW as the helper would: a backticked or path-shaped token in it that names nothing on disk will be reported as a new dead reference when the diff lands.

**Statuses.**
- `STAGED`: waiting. `Rounds open` goes up by one at step 0 of each later round that finds it still staged. `proposals.md` is the authority; the diff file's own line is updated when the file is next touched.
- `APPLIED <date> <commit or "no-git">`: landed and verified.
- `BLOCKED <date> <why>`: approved, but applying it tripped a check; undone; asked again at the next gate.
- `DISCARDED <date> <reason>`: the proposal itself was wrong or withdrawn, or the human excluded it without keeping the finding open.
- `DONE-BY-HUMAN <date>` / `DECLINED <date>`: for kind `human-applied`. "Not yet" or "later" leaves it STAGED.
- `ACCEPTED <date> <the human's words>`: the finding is real and the human keeps things as they are ("keep the row", "no hook", a batch item excluded with "except"). Every audit reads `proposals.md` first: a finding that matches an ACCEPTED row is listed under FYI as accepted and is not proposed again unless the evidence changes, even though the helper will keep reporting it. A declined fix for a RULE FAILURE is raised again only when the lesson recurs, citing the new sightings.

`proposals.md` mirrors every STAGED or carried proposal as one row:

```
| Id | Title | Target | Diff file | Status | Rounds open | Notes |
```

Ids are append-only across rounds. The orchestrator writes `proposals.md`, after each step returns its diffs.

**Kinds.** A proposal is one of three kinds; write `Kind:` under `Id:`.
- `edit` (default): OLD/NEW in an instruction file, as above. When the target has no heading (a frontmatter `description:` line, a body without headings), write `Target: <path> line <N>` and quote the line.
- `new-file`: an instruction file that does not exist yet. No OLD block; NEW is the whole file.
- `human-applied`: anything outside the instruction layer (a `.gitignore`, a hook, a push, unstaging a file, a config or dependency change). No OLD/NEW. Give `Command or change:` (exactly what the human would run or add) and `Verify:` (the read-only command that shows it was done). The round never applies these. At the gate they are DECISIONS, worded "will you ...?". The closing distil runs `Verify:` and closes the proposal as `DONE-BY-HUMAN <date>` when it passes, `DECLINED <date>` when the human said no, or leaves it STAGED.

## baselines.md and lessons.md

`baselines.md`: a `## Limits` section (the limits in force and who chose them), then one row per round:

```
| Round | Model | Files | Words | Over limit | Dead paths | Ambiguous paths | Missing units | Probe | Stopped at |
```

`lessons.md`: the round's own lesson blocks (shape below), newest last, each prefixed with its round date. They are about running the round, so they are never clustered or promoted by the distil; they are appended here at every stop.

## Held lesson

`held-lessons.md`:

```
| Lesson (one line, as general as the evidence allows) | First seen | Seen | Last round | Sources |
```

Write `### Held at round <date>` before adding rows. A row seen twice is promoted (and removed here). A row untouched for 3 rounds moves to `## Aged out`, never deleted.

## Rule sighting

`rule-sightings.md`:

```
| Rule (file + first eight words, quoted) | Owner | Added | Last seen (round, or - if never) | Status |
```

A rule, for this ledger, is one bullet or sentence that tells the actor to do or not do something, in a top-level instruction file or a rules/lessons section. Routing rows and skill bodies are not listed. `Added` is the date of the commit that introduced the line (`git log -S`), or "before round 1". On a project with hundreds of rules, list only those a finding touched plus those already in the ledger.

Status values:
- NEW: first listed this round; not judged until round 3.
- RETIRED: the rule was removed (date, proposal id). A reworded rule keeps its row; update the quoted words.
- ACTIVE: seen within 3 rounds.
- DORMANT: unseen for 3 rounds while its owner was active.
- UNTESTED: its owner did no work in the window.

Only DORMANT rules are step 7 targets.

## Lesson block (the round's own, and any pass's)

```
L<n> <WHO>: <the lesson in one sentence, general>
- Evidence: <what happened, with file/command>
- Proposed home: <file § heading where the actor will read it when acting>
- Confidence: high | medium | low
```

## Reconciliation

The unit is one collected lesson line. Every line lands in exactly one bucket:
- `promoted`: it became a rule, or a staged diff that would make it one (say "staged" until it lands);
- `held`: seen once, parked in `held-lessons.md`;
- `folded`: absorbed into a rule that already says it, or into a RULE FAILURE proposal (name the rule or the proposal);
- `discarded`: not a lesson, already obsolete, or rejected by the human (give the reason).

## Step line

Every step reports one line in this exact shape; the report carries them verbatim.

```
<step> - findings: N · applied: N · held: N · tokens: N|n/a · <one clause: what carried or what it means>
```

- A flag-only step writes `applied: 0 (flag-only)`, never blank.
- `held` in a step line counts everything this step left waiting on the human: staged proposals, diff batches, unanswered questions. Lessons parked in `held-lessons.md` are not counted here; they appear in the reconciliation.
- Step 0 and the gates get a line too (labelled `gate 1`, `gate 2`): step 0's `findings` are the pre-existing failures it labelled; a gate's `held` is the number of items asked, and `applied` is 0.
- A step that ran a paid probe adds `· probe: <spent> of <budget>` before the clause.

## Gate question

Interactive: one message (or AskUserQuestion call); non-interactive: `GATE-<n>.md`. Shape:

```
GATE <n> - <round date> - <N> items. Nothing below is applied until you answer.

SETUP (first round only; these defaults apply unless you say otherwise)
- Limits: <each limit that matters here with its reason from mr.py limits, one line each, auto-loaded files first: they cost context in every session, a skill only when it is used. Leave the byte limit out unless mr.py limits shows it on (Codex)>. Say that the numbers are a starting point from one setup.
- Left out of the scan: <what git ignores, virtual environments, other checkouts; plus any folder you propose for the exclude list, with the reason>.
- State folder: <committed on <branch> | ignored>. Paid probe: none.

BATCH (one "yes" applies all of these; or answer "yes except 3, 7")
1. <Title>. <file § heading>. Why: <one sentence>. Evidence: <short>. [P-12]
2. ...

DECISIONS (each needs its own answer; my recommendation is marked)
D1. <question in plain words, standing on its own>
    a) <safe option>            <- first when the question deletes, publishes or touches production
    b) <option> (recommended)
    c) <option>
D2. ...

FYI (no action)
- <...>

How to answer: reply "BATCH yes" / "BATCH yes except 2" / "D1 b" ... (or write the same into ANSWERS-<n>.md)
```

Answers are recorded verbatim in the report and in `ANSWERS-<n>.md`, with the date.

## Removed verbatim

`runs/<date>/removed-verbatim.md`, appended before each removal lands:

````
### <path> § <heading> - <time> - P-<NN> - <reason>
```
<the removed or replaced text, exactly>
```
````

## Report skeleton

```
# Maintenance round - <date>

- Runtime: <name version>   Model: <exact id>   Model changed since last round: yes/no/first round
- Round started: <ISO time>   Start commit per repo: <hash>   Helper: mr.py <version>   Branch for the round's commits: <name>
- Environment: subagents <y/n> · interactive <y/n> · git <y/n, repos N> · python <y/n> · helper selftest <PASS/FAIL/not run> · owners <one | map> · probe <none | budget>
- Previous round: <date or "first round">   Scope: changes since <date>
- Dirty files at start, not ours: <list or none>

## Stops
<one line per stop, appended: time · where (gate 1, gate 2, abort after step N, close) · why · what the next session does first>

## Lead summary
<2-3 findings in prose, severity first, each naming its file and the one change it asks for.
A round that found nothing important says so.>

## Step 0 - baselines
| Measure | Value | Command | Denominator |
| Instruction files | | mr.py inventory | files scanned |
| Over limit | | mr.py inventory | of N files |
| Dead path references | | mr.py refs | of N path references checked |
| Ambiguous path references | | mr.py refs | of the same N; sorted by hand in step 2 |
| Missing / unreached units | | mr.py refs | of N skills, agents and commands that exist |
| Signals | | mr.py signals | over N files |
| Repos ahead of upstream / without upstream | | mr.py git | of N repos |
| Negative controls | PASS/FAIL | mr.py selftest | 7 check families |
| Probe | x/y | probe-cases.md | y cases x runs |

## Step lines
<one per step, fixed shape>

## Step 1 - distil (opening)
...one section per step, each with its findings table...

## Gate 1 - questions and answers (verbatim)
## Gate 2 - questions and answers (verbatim)

## Abort rule after-readings
- After step N: <mr.py compare summary line> - pass/STOP
- compare sees size, content, paths and names. It cannot tell whether an approved edit says what was approved: that is what "verify the done" is for.

## Baselines before → after
| Measure | Step 0 | Close |

## Carried to next round
- Open proposals (id, title, rounds open)
- Unexplained regressions, UNTESTABLE claims, BLIND checks, NOT MEASURED rows

## Run close
| Field | Value |
| Reconciliation | triaged N = promoted N + held N + folded N + discarded N (arithmetic shown) |
| Diffs | runs/<date>/diffs/, N files |
| Approval posture | N free applies, N approved diffs applied, N rejected, N carried; any edit that was neither, named and justified |
| Removed content | runs/<date>/removed-verbatim.md, N entries, or "nothing removed" |
| Verify-the-done | N applied, N verified by diff, N found NOT DONE |
| Own commits reviewed | N commits, N files, findings or "clean" (the closing state commit is counted, not reviewed) |
    | Probe / skipped steps | <result or NOT MEASURED> · <steps skipped and why> |

## Round lessons
L1 ...
```
