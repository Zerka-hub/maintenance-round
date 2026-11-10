# Checks

## Structure (step 2)

Each row reports value · command · denominator, and resolved/new/persistent against the previous round.

| Id | Check | How (portable) |
|---|---|---|
| S1 | Inventory and sizes | `mr.py inventory` (or the manual commands below) |
| S2 | Over limit | `mr.py inventory`; limits from `.maintenance/limits.json` or the human's gate-1 answer |
| S3 | Dead references: every path, script, skill or command an instruction names exists | `mr.py refs` (backticked paths, links, and bare paths with a slash and a known extension); then by hand for names without a path shape (a skill named in prose: `ls .claude/skills/<name>`) |
| S4 | Routing both ways: every skill or subagent named in a routing table, index or description exists, and every existing skill/subagent is reachable from some routing or description text | list `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, `.agents/skills/*`; grep each name in the top-level files |
| S5 | Description contract: each skill/agent description says what, when, when-not; no two descriptions claim the same trigger | read the frontmatter `description:` lines side by side |
| S6 | Same rule, two homes, different words | grep the key noun of each rule across all instruction files; quote both |
| S7 | Lessons files healthy: within limits, no bullet over the bullet limit, held ledger ages correct | `mr.py inventory` long-bullets column; read `held-lessons.md` |
| S8 | Git hygiene | `mr.py git`: staged files over 1 MB, secret-shaped names tracked or untracked (names only), branches ahead of upstream, repos without upstream, uncommitted count |
| S9 | Growth since last round | `mr.py compare --against <previous round baseline.json>` (informational here; the abort rule uses this round's baseline) |

## Claims (step 3)

**A1 - routing/description agreement.** The routing table or index says job X goes to skill/agent Y, and Y's own description and body say it does X. Check both directions.

**A2 - one rule, every runtime.** If the project has files for more than one runtime (CLAUDE.md and AGENTS.md, Cursor rules, GEMINI.md, Copilot instructions), the same rule says the same thing in each, or one file points to the other. A symlink or `@import` counts as agreement: check it resolves.

**B1 - the global/top file vs everything else.** Each statement in the top-level file about tools, commands or conventions holds in the skills and agents that act on it.

**B2 - claim vs reality** (finds the most). For every sentence asserting current state, check the primary artifact, never another document:

| Claim type | Verify against (portable command) |
|---|---|
| A schedule ("runs nightly", "every hour") | `crontab -l`; `systemctl list-timers --all` (Linux); `launchctl list` (macOS); CI schedule files (`.github/workflows/*.yml` `schedule:`); the job's own log: last run time and exit status |
| A backup ("backed up daily") | the newest backup file or object: name, date, size (`ls -lt <dir> \| head`; in a fresh clone every file's time is the checkout time, so for a tracked file use `git log -1 --format=%cI -- <path>`); then: is the thing that matters in it (uncommitted work is in no backup) |
| "Always pushed" / "remote is the source of truth" | `git remote -v` (names only), `git rev-list --left-right --count @{upstream}...HEAD`, `git status --porcelain \| wc -l` |
| A package manager or tool ("we use pnpm") | the lockfile present (`ls *lock*`), `packageManager` in `package.json`, the CI install command |
| A version ("Node 20", "Python 3.11") | `.nvmrc` / `.tool-versions` / `pyproject.toml` / the CI image, and `<tool> --version` |
| A code path ("X calls Y") | the source file that makes the call (`grep -rn`) |
| A deploy path | the committed deploy config and the CI job that runs it |
| "Private / not exposed / not public" | the exposure config and the hosting settings that would make it public; a listening port with `ss -ltn` (Linux) or `lsof -iTCP -sTCP:LISTEN` (macOS) |
| A tool or integration available to the agent | the runtime's own config listing it (MCP config, settings), not a doc |
| A stated exception ("except helper X handles this") | the helper's source: does it actually do that |
| A conditional ("when implemented", "verify later") | the condition itself; it never becomes false, it stops being informative |
| A prohibition | B3 |

Also run the reverse direction: things that run but no document mentions (each crontab line, each timer, each CI workflow, each remote). Check both polarities of every status claim: "fixed" is checked fixed, "broken" or "open" is checked still broken.

**B3 - prohibition currency.** For every "never/do not/forbidden" line naming a concrete referent (a file, a tool, a service, a model, a vendor, a date-bound policy), ask whether the referent still exists and the reason still holds. Report candidate-stale with evidence; never retire it yourself. Also grep the same files for text that still grants what the prohibition bans, or still bans what a newer decision allowed.

**B4 - decision propagation.** For every decision recorded in the period (decision files, gate answers in previous reports, ADRs, commit messages saying "decided"), check that each file it should have changed now says it. A decision that never reached the text is a finding.

**B5 - names that date.** Model names, versions and vendor names pinned in prose (`mr.py signals` PP-6 lines): still current? Out of scope: other vendors' own model ids used as identifiers in code.

The report lists, besides the findings:
- **true statements that merely matched**, so the next round doesn't "fix" them;
- **could not determine**, with what would settle it;
- **comparison with the previous round**: resolved / new / persistent.

## Health (step 3h)

Read-only. Each line: what was checked, the command, the result, and the age of the evidence.

When the tool that would check something is absent on this host (no `crontab`, no systemd, no network for an advisory page), the row is NOT MEASURED with the reason, never VACUOUS and never "clean". A claim that depends on it is FALSE only if the documents say it runs here; otherwise it goes to "could not determine", with where it would have to be checked.
- Scheduled jobs: for each, the last run time and exit status from its log. A job with no log, or none in 2x its period, is a finding.
- Backups: the newest copy exists, is younger than 2x the stated period, and is not suspiciously small compared with the previous one. Whatever cannot be in a backup (uncommitted work, local-only branches) is counted.
- Git: `mr.py git` per repo.
- Disk: `df -h .`; above 85 % is a finding.
- Certificates the project owns: expiry date (`openssl x509 -enddate -noout -in <file>` or from the endpoint).
- Versions with known security advisories for the tools the project runs (needs network: the tool's own audit command, such as `npm audit` or `pip-audit`, or the vendor advisory page); each is an upgrade proposal, never applied.
- Anything the instructions say is monitored: check the monitor itself ran (its own last output).

## Behaviour probe (step 0 and 8b, optional)

Purpose: the only evidence that an edit to routing or description text left behaviour intact.
1. Write 8-15 cases in `.maintenance/probe-cases.md`:
   `| id | request (one realistic line, the human's phrasing) | expect: skill/agent name, or "ask", or "refuse" | why |`
   Cover every routing row once, plus the two most-confused pairs.
2. Run each case in a fresh, non-persistent, read-only session from the project root. In Claude Code:
   `claude -p "<request>" --no-session-persistence --permission-mode plan --output-format json`
   Other runtimes: their non-interactive mode, in a read-only or plan mode. Record which skill or agent was invoked or named (in Claude Code: the `Skill`/`Agent` tool calls; with `--output-format stream-json --verbose` they appear as tool_use events).
   When a probe is due but the human gave no budget, write NOT MEASURED in the report and carry it.
3. Score `passed / cases`, R runs each (R = 1 by default, 3 when comparing). A probe costs real tokens: run it only on a budget the human states at gate 1.
4. Compare only identical case sets. A case added or removed between runs makes the comparison invalid for that case; say so.

## Apply protocol (steps 5 and 8)

Order: the gate's order (BATCH items, then DECISIONS). Items are independent: one that fails does not stop the others.

Which branch the round commits on: `references/environments.md § Commits`.

For every approved item:
1. `git status --porcelain` and `git branch --show-current` in the file's own repo (`git -C <dir> rev-parse --show-toplevel`). No git: copy the file to `backup/` first.
2. Re-read the live lines: the OLD block must match the file exactly once. If it doesn't, stop on this item and report "live text changed since the proposal".
3. Append the OLD text to `removed-verbatim.md` when the item removes or rewrites (a pure addition has nothing to record). One item at a time: apply, verify, commit, then the next, so an undo never touches another item's edit.
4. Apply. Then run the item's own "Verify after apply" command and `mr.py compare . --against <the step's baseline> --allow-change <every file approved for this step so far>`.
   If compare exits 3 because of this item: undo this item's uncommitted edit (`git restore <file>`, or copy it back from `backup/`), add "DID NOT LAND" under its `removed-verbatim.md` entry, set the proposal to `BLOCKED <date> <the compare line>`, and go on to the next item. A BLOCKED item is asked at the next gate with its evidence. The chain itself stops only if compare still exits 3 after the undo.
5. Commit with explicit file pathspecs: `git add <file>` then `git commit -m "<msg>" -- <file>`. Never `git add -A`, `git commit -a` or `git stash` in a tree others work in. An index-only change (`git rm --cached`) is committed without a pathspec, after `git diff --cached --stat` shows only your change.
6. **Verify the done:** `git show --stat HEAD` must list the file and the change. No git: `diff -u backup/<path> <path>`. A commit that does not contain the change is NOT DONE, whatever the tool said.
7. After the last apply of the step: **review the round's own commits**. `git log <round start commit>..HEAD --name-only --format='%h %s'` lists every file (the start commit is in the report header). Check each belongs in that repo and holds nothing that should not be there: another project's text, secret-shaped strings, large generated files.

## Without the helper (no Python)

The same checks by hand. Portable across GNU and BSD/macOS userlands.

```sh
# inventory + sizes
find . \( -name node_modules -o -name .git -o -name vendor \) -prune -o -type f \( \
  -name CLAUDE.md -o -name CLAUDE.local.md -o -name AGENTS.md -o -name GEMINI.md -o -name SKILL.md \
  -o -name MEMORY.md -o -name '*.mdc' -o -name .cursorrules -o -name copilot-instructions.md \
  -o -name '*.instructions.md' \) -print > /tmp/mr-files.txt
xargs wc -l -w -c < /tmp/mr-files.txt

# referenced paths (then ls each one relative to its file and to the root)
xargs grep -noE '`[^` ]*/[^` ]*`' < /tmp/mr-files.txt

# skills/agents named in text vs present
xargs grep -noE '`[A-Za-z0-9_-]+` (skill|agent|subagent|command)' < /tmp/mr-files.txt
ls .claude/skills .agents/skills .claude/agents 2>/dev/null

# prompt-pattern signals (candidates only)
xargs grep -nE '(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT)|!!|[Tt]hink step by step|20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]' < /tmp/mr-files.txt

# git hygiene, per repo
git status --porcelain
git diff --cached --name-only
git rev-list --left-right --count '@{upstream}...HEAD'   # "behind ahead"; an error means no upstream
git ls-files --others --exclude-standard | grep -E '(^|/)\.env|\.pem$|\.key$|credentials'

# abort rule: save sizes at step 0, compare after each step
xargs wc -w < /tmp/mr-files.txt > .maintenance/runs/<date>/sizes-step0.txt
xargs wc -w < /tmp/mr-files.txt | diff .maintenance/runs/<date>/sizes-step0.txt -
```

Negative controls by hand: plant one fault per check in a scratch copy (a dead path, a missing skill name, an over-limit file, a "MUST"), run the check, and confirm it fires. Remove the fault and confirm it goes silent.
