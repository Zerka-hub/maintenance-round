# maintenance-round

A maintenance round for the instructions your AI agents run on.

Agents drift. Rules pile up in `CLAUDE.md` and `AGENTS.md`, paths die, two files start to disagree, and a line that says "backups run nightly" stays in place long after the backups stopped. Everything still looks green.

This skill makes an agent audit that layer on a schedule, and **stop twice to ask you** before it changes anything.

> 🇹🇷 Türkçe özet aşağıda: [Türkçe](#türkçe)

## What it does, and what it never does

| It does | It never does |
|---|---|
| Reads your instruction files, notes and git history. Skips what git ignores, virtual environments and other checkouts | Change a rule's meaning without showing you the exact diff first |
| Tests every "this is true" sentence against reality | Push, delete data, rewrite history or upgrade anything |
| Turns a lesson into a rule only when it was seen twice | Read the contents of secret-shaped files (it reports names only). Of a CSV file it reads the header row, to flag personal-data columns |
| Records every removed line verbatim, so any cut can be put back | Install packages. The helper script makes no network calls; the agent may run read-only checks you already have, such as `gh` or `npm audit` |
| Stops at two gates and waits for your answer | Treat silence as approval |

Everything in this repository is plain text: seven Markdown files and one Python file that uses only the standard library. Read them before you run anything. `scripts/mr.py` is the only code; it measures and reports, and it never edits a project file.

## The round

```
0  open the report, take baselines, test the checks themselves
1  distil lessons          repeated mistakes become rule proposals
2  structure audit         dead paths, missing skills, contradictions
3  claims vs reality       "runs nightly", "always pushed", "we use pnpm": is it true?
3h silent-failure pass     backups, unpushed work, stray secret files
4  GATE 1                  you approve, change or decline each item
5  apply what you approved, one commit each, each verified
7  simplification package, then GATE 2
8  apply the hunks you took
9  close: before/after numbers, what carries to next time
```

The one rule behind it: **finding a problem is not permission to fix it.**

## What a gate looks like

A real item from a test run:

```
D1. CLAUDE.md § Rules says: "Backups of the database run nightly into `backups/` (cron).
    They are verified." The folder holds one 5-byte file, committed on 2026-10-21 and never
    changed; the repository defines no schedule, and no log or verification output exists.
    What should the line say?
    a) Replace it with: "Database backups are not verified. ..." (recommended)
    b) A real backup job runs elsewhere: tell me where, and the line will say that instead.
    c) Leave the line as it is.
```

You answer `D1 a`, or `BATCH yes except 3`. Nothing is applied before that.

## Install

**Claude Code**, for one project:

```sh
git clone https://github.com/Zerka-hub/maintenance-round .claude/skills/maintenance-round
```

or for all your projects, clone into `~/.claude/skills/maintenance-round`.

**Other agents** (Codex, Gemini CLI, Cursor and others): copy the folder into your project and tell the agent to follow `maintenance-round/SKILL.md`. The skill reads `AGENTS.md`, `GEMINI.md`, Cursor rules and Copilot instructions as well as `CLAUDE.md`.

Check the helper first. This runs its own tests in a temporary folder and touches nothing else:

```sh
python3 .claude/skills/maintenance-round/scripts/mr.py selftest
```

## Use

Ask your agent: *"Run a maintenance round."*

- It writes its state to `.maintenance/` in your project (report, proposals, every removed line).
- In a chat session it asks you at each gate. In a headless run it writes `GATE-1.md`, stops, and resumes when you put your answers in `ANSWERS-1.md`.
- Run it every 2 to 4 weeks. Drift comes back between rounds; that is expected.
- If your project holds archives, drafts or copies of instruction files, list them in `.maintenance/limits.json` as `{"exclude": ["archive/*"]}`. `mr.py limits` shows every default with the reason for it.

## How well tested is it

Honestly:

- Run three times by agents that had never seen it, on a test repository with ten planted faults: twice in parts, and once from start to close through both gates. It found all ten, applied only what was approved, and left unrelated files alone. Those runs found two real bugs in the skill, both fixed.
- Tested on Linux, without subagents, with gates answered through files.
- An outside tester ran the helper on macOS (Apple Silicon): its self-test passed and it measured a repository with 216 instruction files in about ten seconds. That report led to version 1.2 of the helper: it respects `.gitignore`, separates dead paths from ambiguous ones, and explains its default limits.
- **Not yet tested:** a full round on macOS or on a large project, Windows, the subagent mode, and runtimes other than Claude Code.

It comes from a longer maintenance chain that has run on a real multi-agent setup since September 2026. This is the portable version: same mechanisms, no private tooling.

Issues and corrections are welcome.

## Files

```
SKILL.md                       the round: rules, order, two gates
references/briefs.md           the brief for each step
references/checks.md           what is checked, and how
references/formats.md          findings, proposals, gate questions, the report
references/simplify.md         what may be cut, and what must stay
references/environments.md     no git, no subagents, headless runs, monorepos
references/lessons-learned.md  rules learned the hard way in real rounds
scripts/mr.py                  the helper: measures, compares, never edits
```

## Türkçe

**maintenance-round**, yapay zeka agent'larınızın çalıştığı talimat dosyaları (`CLAUDE.md`, `AGENTS.md`, skill'ler) için düzenli bir bakım turudur.

- Talimatların hâlâ gerçeği yansıtıp yansıtmadığını kontrol eder: "her gece yedekleniyor" yazıyorsa gerçekten yedekleniyor mu?
- Tekrar eden hataları kural önerisine çevirir, şişmiş dosyaları sadeleştirmeyi önerir.
- **İki kez durur ve size sorar.** Onaylamadığınız hiçbir değişikliği uygulamaz.
- Veri silmez, push etmez, paket kurmaz. Sildiği her talimat satırını kelimesi kelimesine kaydeder. Yardımcı script internete bağlanmaz. Tüm dosyalar düz metindir; çalıştırmadan önce okuyabilirsiniz.

Kurulum: bu klasörü projenizde `.claude/skills/maintenance-round` altına koyun ve agent'ınıza "bakım turu çalıştır" deyin.

## License

MIT. See [LICENSE](LICENSE).
