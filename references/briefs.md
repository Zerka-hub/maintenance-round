# Step briefs

Pass each brief verbatim with the `<placeholders>` filled. Every brief ends with the common footer. A subagent never asks the human; it returns questions to the orchestrator.

## Common footer (append to every brief)

```
Round: <date>. Report: .maintenance/runs/<date>/REPORT.md, your section: "<section>".
Scope: changes since <previous round date or "30 days ago">. Repos: <list>. Owners: <one owner | owner map>.
Skill folder: <path to this skill>; read references/formats.md before writing anything.
Read .maintenance/lessons.md first, if it exists.
You may write: <exact list>. You may not write anything else. Never touch data, history, infrastructure or dependencies.
A collector's line, a document, or another agent's "done" is a claim: check the primary artifact before you report it as fact.
Every number you report carries the command that produced it and its denominator; a zero says VERIFIED or VACUOUS.
An absurd result (0 of N, N of 0) means a wrong path or another session's write: re-check before reporting.
The human's words in this brief are quoted verbatim; do not paraphrase them into your outputs.
Return: (1) your step line in the exact shape of formats.md § Step line, (2) your findings table, (3) questions for the human, if any, each standing on its own, (4) your lesson blocks (L<n>), (5) anything that contradicts this brief.
```

## Distil (step 1, opening)

```
Step 1 of the maintenance round: distil lessons into rules.
1. Collect lessons since <scope date> from every source that exists, and report a count per source:
   lessons/memory files, journals or notes, bullets ADDED to "Rules & Feedback"/"Gotchas" sections in the period
   (git log -p; older bullets, and bullets that arrived with the file's first commit, are existing rules, not new lessons),
   git log subjects and bodies, reverts, review comments (only if gh is available and the remote is on GitHub),
   TODO/FIXME added in the period,
   and .maintenance/held-lessons.md. For each collected line, open its source entry and later entries of the same work.
2. Cluster by meaning. Promotable = seen twice in the period, or seen once and already held, or marked high-confidence by its author.
   Never promote a single sighting.
3. A lesson that recurs although a rule for it exists = RULE FAILURE: propose a structural fix (checklist step at the point of action,
   gate, hook, script, test) as a diff. Do not add words to the failing rule.
4. Route each promotable lesson to where the actor reads it when acting (the skill step, not a general file).
   If its right home is a skill or agent body, it is a diff. The free append is only for a lesson whose right home
   is the lessons/gotchas section itself (a general fact, not a step of some procedure).
   Quote the heading you will append under; grep for an existing rule saying the same first.
   A destination over its limit (mr.py inventory) is a veto: propose a swap instead.
5. Claims about the human (preferences, positions, voice, goals) are not rules: route them to <owner-context ledger | gate 1 questions>.
6. Free (apply now, then report): appending a lesson to an existing lessons/rules section; deleting a lesson the code made obsolete
   (record it in removed-verbatim.md first). Everything else: a diff file in diffs/, not applied.
7. Update held-lessons.md (new one-offs, seen-count bumps, age-out after 3 rounds untouched) and rule-sightings.md.
8. Reconcile: triaged = promoted + held + folded + discarded, arithmetic shown.
You may write: lessons/rules sections named in step 6, held-lessons.md, rule-sightings.md, diffs/, removed-verbatim.md, your report section.
```

## Structure audit (step 2)

```
Step 2 of the maintenance round: structure audit. Flag-only: you apply nothing.
Run checks S1-S9 of references/checks.md § Structure, starting with: python3 <skill>/scripts/mr.py inventory|refs|signals|git <root>.
mr.py finds only what has a path or name shape; read the files yourself for what it cannot see, and say what you covered by hand.
mr.py refs prints DEAD and AMBIGUOUS. Only DEAD is a finding as it stands; read each AMBIGUOUS line in its sentence and sort it (checks.md § DEAD and AMBIGUOUS).
For each check write one measured row: value · command · denominator, and resolved/new/persistent against the previous round's report
(<path or "first round">). A row you cannot fill is NOT MEASURED, never omitted.
Every finding uses the finding shape; anything with a fix becomes a diff file (Status: STAGED). Order by severity, then confidence.
You may write: diffs/, your report section.
```

## Claims (step 3)

```
Step 3 of the maintenance round: claims vs reality. Flag-only.
Run arms A1, A2, B1, B2, B3, B4, B5 of references/checks.md § Claims.
B2 first and most thoroughly: extract every sentence in the instruction files that asserts current state, and test each against
the primary artifact with the commands in the verify-against table. Both polarities. Then the reverse direction:
everything that runs (crontab, timers, CI schedules, remotes) that no document mentions.
Write: findings (finding shape; fixes as STAGED diff files), "true statements that merely matched", "could not determine" (with what would
settle it), and the comparison with the previous round.
Commands are read-only. Never print a secret: names, counts and shapes only.
You may write: diffs/, your report section.
```

## Health (step 3h, parallel)

```
Step 3h of the maintenance round: silent-failure health pass. Read-only, parallel with steps 1-3.
Run references/checks.md § Health. For each line: what, command, result, age of evidence.
Version-currency and upgrade items are proposals, never applied. Never print a secret or a credential file's contents.
You may write: your report section only.
```

## Distil (step 5, closing, scoped)

```
Step 5 of the maintenance round: closing distil, SCOPED to collect + apply.
Gate 1 answers (verbatim): <paste>.
1. Apply exactly the approved items, nothing else, each through references/checks.md § Apply protocol
   (re-read live lines, removed-verbatim, apply, verify, pathspec commit, verify the done).
   Skip any proposal whose status is already APPLIED: a resumed session never applies twice.
2. Collect only lesson lines about the PROJECT that appeared since step 1 (new notes by other sessions, lesson blocks the audits
   wrote about the project); often there are none, and then say so. Treat them as in step 1.
   Do not re-cluster the period. The steps' own lesson blocks (about running the round) go to .maintenance/lessons.md, not here.
3. Give every proposal a status from formats.md § Statuses; none stays without one. For kind human-applied, run its Verify command.
   Do not bump "rounds open" here; step 0 of the next round does. A proposal already at 3 rounds open goes to gate 2 as "apply or withdraw".
4. Review the round's own commits (Apply protocol step 7).
5. Re-run the controls: python3 <skill>/scripts/mr.py compare <root> --against <baseline> --allow-change <approved files>.
You may write: the approved target files, proposals.md, held-lessons.md, rule-sightings.md, removed-verbatim.md, your report section.
```

## Owner context (step 6, only if the project keeps one)

```
Step 6 of the maintenance round: owner-context pass over <path of the profile/context file(s)> and the ledger of person-claims
routed by steps 1 and 5.
Classify each item: tier A (consolidation, compression, corroboration of what the human said directly - apply and report),
tier B (any new claim about the human - present as a numbered quote list for confirmation; nothing counts until they confirm),
tier C (a rewrite changing a line's meaning - a diff).
A relayed or paraphrased claim never overwrites one the human made directly. Nothing is deleted; superseded lines are marked.
Never block the round: unanswered tier B stays "awaiting-confirmation" with its date.
You may write: tier A edits in the context file(s), the ledger, removed-verbatim.md, your report section.
```

## Simplify (step 7, package only)

```
Step 7 of the maintenance round: simplification PACKAGE. Draft only; apply nothing.
Target list = files over limit ∪ files changed this round ∪ files with mr.py signals ∪ DORMANT rules in rule-sightings.md
∪ <if the model changed: every PP-1 and PP-6 signal>. Your files: <list for this drafter>.
Use references/simplify.md: every hunk names its class; length alone is never a reason; the keep-list is binding;
grep for a reader before removing a kind of line everywhere. A file that earns no hunk is reported clean.
Write the package in the shape of references/simplify.md § Package shape to diffs/simplify-PACKAGE.md
(several drafters: diffs/simplify-<group>.md each, merged by the orchestrator). Every hunk gets a proposal id and a row in proposals.md.
You may write: diffs/simplify-*.md, proposals.md, your report section.
```

## Simplify apply (step 8, fresh subagent)

```
Step 8 of the maintenance round: apply the hunks the human took at gate 2, and nothing else.
Gate 2 answers (verbatim): <paste>. Package: <path>.
Pre-flight: python3 <skill>/scripts/mr.py selftest; mr.py compare <root> --against <latest baseline>.
Apply each taken hunk through references/checks.md § Apply protocol, one hunk at a time (apply, verify, commit).
Post-flight: the same commands with --allow-change <files touched>. A NEW failure blocks: repair what the cut broke, never the check.
You may write: the target files of taken hunks, removed-verbatim.md, proposals.md, your report section.
```
