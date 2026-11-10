# Environments that differ

**Non-interactive (headless, CI, `claude -p`, `codex exec`).** At a gate, write `runs/<date>/GATE-<n>.md` in the gate format, put a one-paragraph summary plus the file path in your final output, and stop. Do not apply anything gate-bound. Steps after a gate wait for `ANSWERS-<n>.md`. The human writes it, or replies and the next run writes it verbatim. On the next invocation, find the newest run directory. If `GATE-<n>.md` exists and `ANSWERS-<n>.md` does not, re-print the gate and stop. If the answers exist, resume at the step after that gate. Answers older than the round's step-0 date are stale: re-ask. Nothing after the gate is drafted while it waits. Answers may name items by their position or by their id; when an answer is not clear enough to act on, that item stays STAGED and is asked again.

**Resuming, in any environment.** A new session trusts the disk, not memory: the report's Stops section says where the round stopped, `proposals.md` says what has already landed. Record files that became dirty since the last stop in the header. If the round stopped on the abort rule, it wrote `ABORT.md` in the run folder (what regressed, after which step, the compare output, the options); the human answers under an `ANSWER:` line in that file, and the next session starts there.

## Commits

The round commits two things: approved edits (steps 5 and 8) and its own state. Both follow the project's commit rules. If those forbid commits on the current branch, create `maintenance/<date>` once with `git switch -c`, commit there, leave it checked out when the round stops and tell the human it is theirs to merge. Every commit names its pathspec, so files someone else has staged stay out.

On a first round, nothing is committed and no branch is created before the human has answered gate 1 (its SETUP block decides whether and where the state is kept). From then on, at every stop (gate, abort, close): write `.maintenance/.gitignore` containing the one line `runs/*/backup/` if it is missing, then `git add .maintenance` and `git commit -m "maintenance <date>: state at <stop>" -- .maintenance`. The baseline JSON files are committed, because the next round's growth check (S9) reads the previous one.

**A harness that refuses to write report files.** Some runtimes block their file-write tool for names like `REPORT.md` inside a subagent. Write the file through the shell instead and say so in the header; the report on disk is what lets another session resume.

**No subagents.** Run the steps in order yourself. After each step, write its section and step line into the report before starting the next. At the start of a step, re-read the report and the step's brief, not your earlier reasoning, so each lens stays separate. Where a step asks for a fresh subagent (step 8), apply only from what is on disk: the package file and the recorded answers.

**No git.** Before the first edit to any file, copy it to `runs/<date>/backup/<same relative path>`. Proposals are OLD/NEW blocks, applied by exact-match replacement (the OLD block must match the live file exactly once, or the item stops). "Verify the done" compares the live file with the backup: `diff -u backup/<path> <path>`. Skip the git rows of the health pass and mark them NOT MEASURED.

**Monorepo / multi-repo.** Inventory from the workspace root. Run git checks per repo (`mr.py git` lists them). Commit per repo, never across. Keep one `.maintenance/` at the workspace root, or one per repo if repos have different owners; say which in the header.

**Other runtimes' instruction files.** Everything `mr.py inventory` lists is in scope: CLAUDE.md, AGENTS.md, GEMINI.md, `.cursorrules`, `.cursor/rules/*.mdc`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `.claude/skills|agents|commands`, `.agents/skills`, `.gemini/commands`. When two runtimes load different files for the same project, the claims arm checks that they agree (checks.md, arm A2).
