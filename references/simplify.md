# Simplification classes and keep-list (step 7)

Judge every hunk against the model that will read the file. Current models follow instructions closely and literally. Text written to push older, less steerable models now over-applies.

## The test for every sentence

*If this sentence were deleted, would the reader act differently?* If not, it is a candidate. Removing history and removing rationale are two different edits: history goes, the reason a constraint exists stays.

## Classes (every hunk names one)

- **D1 - rule and pointer only.** No dates, attributions, quotes-as-authority, incident stories, "added after X", change logs or "last updated" lines in a rule file. The story moves to the report or a record file. An identifier is not narrative: a path, a flag, a limit, a script name is payload and stays.
- **D2 - one rule, one home.** The same rule in two places becomes one home plus a pointer. A second copy stays only where it is the copy the actor reads at that exact step.
- **D3 - sections stay disjoint.** Process is the procedure; no Process step is ever deleted. Quality bar: only measurable checks the process does not imply. Rules/feedback: only what the process does not contain.
- **D4 - person or project names inside a general skill** move to the project's own files; the general rule stays.
- **PP-1 - pressure language.** Capitals (MUST, NEVER, CRITICAL), `!!`, emphasis with no reason beside it; hedges ("try to", "if possible") on what is actually required. Replace with the plain instruction plus its reason.
- **PP-2 - choreography for judgement work.** A fixed sequence of moves for a task whose order does not matter ("first read X, then think about Y"). State the goal and the constraints.
- **PP-3 - prohibition without a reason.** Judge each line alone. A line encoding a real constraint (safety, data, authority, money) keeps its prohibition and gains its reason; a line with no traceable reason is a removal candidate.
- **PP-4 - patch accretion.** Narrow special cases, each traceable to one incident, standing where a principle should. Generalise the principle in one line; keep any special case the principle does not cover.
- **PP-5 - description contract.** A skill or agent description carries what it does, when to use it, when not. Scolding cross-references and behaviour rules move into the body.
- **PP-6 - model fossils.** A model name or version pinned in prose, "known issue with <model>" workarounds, thinking incantations ("think step by step", scratchpad instructions). Remove, or replace with the capability the text actually needs.
- **PP-7 - update suppressors and anti-formatting rules** written for chatty models ("hold all findings for the end", "never use bullets", reminders re-inserted on a cadence).
- **DORMANT** - a rule no round has seen for 3 rounds while its owner was active. Propose retiring it; the human decides each one.

## Keep-list (as binding as the classes)

1. **Context is never cruft:** audience, environment facts, the quality bar, tool contracts, hard judgement calls, the reasons behind constraints.
2. **Cruft is not length.** No hunk is justified by a word, byte or limit count alone.
3. **Fragile operations keep exact commands:** destructive commands, git in shared trees, credentials, migrations, anything where exactly one sequence is safe.
4. **A prohibition against a failure that still happens stays.** The test is whether the failure would still reproduce on the current model, not whether the line reads as a prohibition.
5. **Trigger text may carry calibrated urgency:** a description, a when-to-use list, a routing row. Flag shouting in bodies, not in triggers.
6. **Tool and script contract detail stays and may grow:** flags, limits, exit codes, what a script does not check.
7. **Records are out of scope:** lessons ledgers, decision records, changelogs and reports carry history as their payload.
8. **A clean surface is a valid outcome.** No hunk is manufactured to fill a package.

## Before removing a kind of line everywhere

Grep the skills, scripts and hooks for a reader of it. A `Last verified:` stamp, an evidence tag or a numbered citation may be the input to some step. A line with a reader is a mechanism, not decoration.

## Package shape

`runs/<date>/diffs/simplify-PACKAGE.md`:
1. Target list: file · kind · words · limit · which set brought it in.
2. Findings, ordered by confidence, in the finding shape.
3. Words table: file · before → after.
4. Kept-against-signal list: each signal adjudicated "keep", with the keep-list item.
5. Per-hunk diffs, each in the proposal shape of formats.md (Id, Status, Class, OLD, NEW, Verify after apply), so a hunk is applied and tracked exactly like any other proposal.
