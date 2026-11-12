#!/usr/bin/env python3
"""mr.py - mechanical half of the maintenance round. Python 3.8+, stdlib only.

It measures and reports; it never edits a project file and never decides.
Every figure it prints names its denominator; a scan that saw nothing exits 2
(NOT MEASURED) so an empty result can never read as a clean project.

  python3 mr.py limits    [ROOT]          the limits in force (defaults + limits.json)
  python3 mr.py inventory [ROOT]          instruction files, sizes, limits
  python3 mr.py refs      [ROOT]          referenced paths that do not exist
  python3 mr.py signals   [ROOT]          prompt-pattern candidates (to adjudicate)
  python3 mr.py git       [ROOT]          repo hygiene (names and counts, never contents)
  python3 mr.py baseline  [ROOT] --save F all of the above as JSON
  python3 mr.py compare   [ROOT] --against F [--allow-change PATH ...]
                                           abort rule: exit 3 on any regression; an instruction file whose
                                           content changed must be named (--allow-grow is the old spelling)
  python3 mr.py selftest                  negative controls: every check must fire
                                           on a planted fault and go silent without it

Exit codes: 0 ok, 1 findings present (inventory/refs/git/signals), 2 NOT MEASURED,
3 regression (compare), 4 selftest failed.
Limits: `mr.py limits` prints them; override in ROOT/.maintenance/limits.json (same keys).
The skill's own folder and .maintenance/ are never scanned: they are the tool, not the subject.
"""
import hashlib
import json
import os
VERSION = "1.4"
import fnmatch
import re
import subprocess
import sys
import tempfile
import shutil

DEFAULT_LIMITS = {
    # words, unless the key says otherwise. Real-fleet values; tune per project.
    "top_words": 4500,          # an auto-loaded instruction file (CLAUDE.md, AGENTS.md, ...)
    "top_bytes": None,          # Codex only: see codex_limit(). A number here overrides what Codex is set to
    "skill_words": 3000,        # one skill / command body
    "agent_words": 1200,        # one subagent definition
    "rule_file_words": 1500,    # one rules file (.cursor/rules, .github/instructions)
    "memory_lines": 200,        # a lessons / memory file
    "memory_words": 2000,
    "rule_bullet_words": 60,    # one bullet in a lessons / rules section
    "exclude": [],              # extra paths to leave out, as globs relative to ROOT ("drafts/*", "old/**")
}

LIMIT_WHY = {
    "top_words": "auto-loaded into every session, so every word costs context each time",
    "top_bytes": "Codex only: it stops reading AGENTS.md at project_doc_max_bytes (32 KiB unless changed); other runtimes have no such cut",
    "skill_words": "read only when the skill is used, so it may be longer than a top-level file",
    "agent_words": "a subagent's whole definition is loaded each time it is spawned",
    "rule_file_words": "rule files are usually attached by path or glob, several at once",
    "memory_lines": "a lessons file past this stops being read to the end",
    "memory_words": "same file, measured in words",
    "rule_bullet_words": "a bullet longer than this is usually two rules or a story",
    "exclude": "globs for folders that hold copies, drafts or archives of instruction files",
}

SKIP_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".venv", "venv",
             "__pycache__", ".maintenance", "third_party", ".next", "target",
             ".tox", ".cache", "coverage", "site-packages", "worktrees"}

TOP_NAMES = {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", "AGENTS.override.md",
             "GEMINI.md", ".cursorrules", ".windsurfrules", "copilot-instructions.md"}
MEMORY_NAMES = {"MEMORY.md", "LESSONS.md", "lessons.md", "LEARNINGS.md", "learnings.md"}


def kind_of(rel):
    parts = rel.split("/")
    name = parts[-1]
    if name in TOP_NAMES:
        return "top"
    if name == "SKILL.md":
        return "skill"
    if name in MEMORY_NAMES:
        return "memory"
    if len(parts) >= 2 and parts[-2] == "agents" and name.endswith(".md") and (
            ".claude" in parts or ".codex" in parts or ".gemini" in parts):
        return "agent"
    if len(parts) >= 2 and parts[-2] == "commands" and name.endswith(".md") and (
            ".claude" in parts or ".gemini" in parts):
        return "skill"
    if name.endswith(".mdc") and "rules" in parts:
        return "rule"
    if name.endswith(".instructions.md") and ".github" in parts:
        return "rule"
    if name.endswith(".toml") and "commands" in parts and ".gemini" in parts:
        return "skill"
    return None


# The skill's own folder is the tool, not the subject: never inventory it.
SELF_DIR = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_IGNORED = {}
# instruction folders are read even when git ignores them: the agent loads them all the same
KEEP_IGNORED = {".claude", ".claude/skills", ".claude/agents", ".claude/commands", ".cursor", ".cursor/rules",
                ".agents", ".agents/skills", ".gemini", ".gemini/commands"}


def git_ignored(root):
    """Paths git ignores under ROOT (one call, cached): (set of dirs, set of files), relative, '/'-separated."""
    key = os.path.realpath(root)
    if key not in _IGNORED:
        dirs, files = set(), set()
        if shutil.which("git"):
            try:
                r = subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--directory"],
                                   cwd=root, capture_output=True, text=True, timeout=60)
                if r.returncode == 0:
                    for ln in r.stdout.splitlines():
                        (dirs if ln.endswith("/") else files).add(ln.rstrip("/"))
            except (OSError, subprocess.TimeoutExpired):
                pass
        _IGNORED[key] = (dirs, files)
    return _IGNORED[key]


def is_other_checkout(path):
    """A linked git worktree: its .git is a file pointing into another repo's worktrees/ folder."""
    g = os.path.join(path, ".git")
    if os.path.isfile(g):
        try:
            return "/worktrees/" in open(g, encoding="utf-8", errors="replace").read(400)
        except OSError:
            return False
    return False


def walk(root):
    """Files of the project itself: not git-ignored, not a virtual environment, not another checkout,
    not a path the human excluded. An auto-loaded top-level file is kept even when ignored
    (CLAUDE.local.md is usually ignored and still read by the agent)."""
    excl = limits_for(root).get("exclude") or []
    owner = {}   # folder -> the repository whose ignore rules judge it

    def repo_of(dp):
        if dp not in owner:
            owner[dp] = dp if (dp == root or os.path.isdir(os.path.join(dp, ".git"))) else repo_of(os.path.dirname(dp))
        return owner[dp]

    def ignored(full, is_dir):
        # each file is judged by its own repository's rules: a workspace often ignores the repositories inside it
        base = repo_of(full if is_dir else os.path.dirname(full))
        if is_dir and base == full:
            return False
        ig_dirs, ig_files = git_ignored(base)
        return os.path.relpath(full, base).replace(os.sep, "/") in (ig_dirs if is_dir else ig_files)

    def skipped(rel, name, full):
        return (name in SKIP_DIRS or name.startswith((".venv", "venv")) or os.path.isfile(os.path.join(full, "pyvenv.cfg"))
                or (rel not in KEEP_IGNORED and ignored(full, True))
                or os.path.islink(full) or os.path.realpath(full) == SELF_DIR or is_other_checkout(full)
                or any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(rel + "/", g) for g in excl))

    for dp, dns, fns in os.walk(root):
        rel_dp = os.path.relpath(dp, root).replace(os.sep, "/")
        rel_dp = "" if rel_dp == "." else rel_dp + "/"
        dns[:] = sorted(d for d in dns if not skipped(rel_dp + d, d, os.path.join(dp, d)))
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            rel = rel_dp + fn
            if os.path.islink(p):
                continue
            if fn not in TOP_NAMES and ignored(p, False):
                continue
            if any(fnmatch.fnmatch(rel, g) for g in excl):
                continue
            yield p, rel


def read(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def limits_for(root):
    lim = dict(DEFAULT_LIMITS)
    p = os.path.join(root, ".maintenance", "limits.json")
    if os.path.isfile(p):
        try:
            lim.update(json.load(open(p)))
        except ValueError as e:
            print(f"WARN limits.json unreadable ({e}); defaults used", file=sys.stderr)
    return lim


CODEX_HOME = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
CODEX_DEFAULT_BYTES = 32768
CODEX_FILES = {"AGENTS.md", "AGENTS.override.md"}


def codex_limit(root, lim=None):
    """(bytes or None, where the number comes from). None: no sign of Codex, so no byte limit applies.
    Codex is seen when the project has a .codex folder or the user has a Codex home folder. Its limit is
    project_doc_max_bytes in config.toml (32 KiB when unset); this only reads that one number."""
    lim = lim or limits_for(root)
    homes = [h for h in (os.path.join(root, ".codex"), CODEX_HOME) if os.path.isdir(h)]
    if not homes:
        return None, "Codex not seen: no .codex folder in the project or the home folder"
    if isinstance(lim.get("top_bytes"), int) and not isinstance(lim.get("top_bytes"), bool):
        return lim["top_bytes"], ".maintenance/limits.json"
    for h in homes:
        cfg = os.path.join(h, "config.toml")
        if os.path.isfile(cfg):
            m = re.search(r"(?m)^\s*project_doc_max_bytes\s*=\s*(\d+)", read(cfg))
            if m:
                return int(m.group(1)), f"project_doc_max_bytes in {cfg}"
    return CODEX_DEFAULT_BYTES, f"Codex default; to change it set project_doc_max_bytes in {os.path.join(CODEX_HOME, 'config.toml')}"


def inventory(root):
    lim = limits_for(root)
    codex_bytes, _ = codex_limit(root, lim)
    rows = []
    for p, rel in walk(root):
        k = kind_of(rel)
        if not k:
            continue
        t = read(p)
        words, lines, nbytes = len(t.split()), t.count("\n") + (1 if t and not t.endswith("\n") else 0), len(t.encode())
        over = []
        if k == "top":
            if words > lim["top_words"]:
                over.append(f"words {words}>{lim['top_words']}")
            if codex_bytes and os.path.basename(rel) in CODEX_FILES and nbytes > codex_bytes:
                over.append(f"bytes {nbytes}>{codex_bytes} (Codex stops reading here)")
        elif k == "skill" and words > lim["skill_words"]:
            over.append(f"words {words}>{lim['skill_words']}")
        elif k == "agent" and words > lim["agent_words"]:
            over.append(f"words {words}>{lim['agent_words']}")
        elif k == "rule" and words > lim["rule_file_words"]:
            over.append(f"words {words}>{lim['rule_file_words']}")
        elif k == "memory":
            if lines > lim["memory_lines"]:
                over.append(f"lines {lines}>{lim['memory_lines']}")
            if words > lim["memory_words"]:
                over.append(f"words {words}>{lim['memory_words']}")
        long_bullets = 0
        if k in ("memory", "rule", "top", "skill"):
            for ln in t.splitlines():
                s = ln.strip()
                if s.startswith(("- ", "* ")) and len(s.split()) > lim["rule_bullet_words"]:
                    long_bullets += 1
        rows.append({"path": rel, "kind": k, "words": words, "lines": lines,
                     "bytes": nbytes, "over": over, "long_bullets": long_bullets,
                     "sha": hashlib.sha256(t.encode()).hexdigest()[:16]})
    return rows, lim


PATH_TOKEN = re.compile(r"`([^`\s]+)`")
CODE_SPAN = re.compile(r"`([^`]*\s[^`]*)`")   # a backticked command with arguments
LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
EXT = re.compile(r"\.(md|mdc|py|sh|js|ts|tsx|json|ya?ml|toml|txt|sql|go|rs|rb|css|html)$")
# a path written in prose without backticks: needs a slash and a known extension, so plain words never match
BARE = re.compile(r"(?<![`\w./:@-])((?:\.{1,2}/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:md|mdc|py|sh|js|ts|tsx|json|ya?ml|toml|txt|sql|go|rs|rb|css|html))(?![\w/-])")


def candidate_paths(text):
    in_fence = False
    for i, ln in enumerate(text.splitlines(), 1):
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        bare_src = PATH_TOKEN.sub(" ", LINK.sub(" ", re.sub(r"[a-z]+://\S+", " ", ln)))
        spans = " ".join(m.group(1) for m in CODE_SPAN.finditer(ln))
        for m in (list(PATH_TOKEN.finditer(ln)) + list(LINK.finditer(ln)) + list(BARE.finditer(bare_src))
                  + list(BARE.finditer(re.sub(r"[a-z]+://\S+", " ", spans)))):
            tok = m.group(1).strip().rstrip(".,;:")
            if re.match(r"^[a-z]+://", tok) or tok.startswith(("mailto:", "#", "$", "-", "@")):
                continue
            if any(c in tok for c in "<>*{}()[]|=?\"'") or ".." in tok.replace("../", ""):
                continue
            if "/" not in tok and not EXT.search(tok):
                continue
            if tok.startswith("/"):
                # an absolute token is a file path only if its first segment is a directory on this host;
                # otherwise it is a URL route (`/ready`, `/api/v1/users`) or another machine's path
                seg = tok.strip("/").split("/")
                if len(seg) < 2 or not os.path.isdir("/" + seg[0]):
                    continue
            if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", tok) and not EXT.search(tok) and not tok.endswith("/"):
                # owner/repo or npm @scope/pkg shapes are ambiguous; only report if it looks local
                if not os.path.splitext(tok)[1] and tok.count("/") == 1 and tok.split("/")[0] not in (".", "src", "docs", "scripts", ".claude", ".github", ".cursor", ".agents"):
                    continue
            yield i, tok


NAMED = [re.compile(r"`([A-Za-z0-9_-]+)`\s+(skill|subagent|agent|command)\b", re.I),
         re.compile(r"\b(skill|subagent|agent|command)\s+`([A-Za-z0-9_-]+)`", re.I)]


def known_units(root):
    names = set()
    for p, rel in walk(root):
        parts = rel.split("/")
        if parts[-1] == "SKILL.md" and len(parts) >= 2:
            names.add(parts[-2])
        elif kind_of(rel) == "agent" or (len(parts) >= 2 and parts[-2] == "commands"):
            names.add(os.path.splitext(parts[-1])[0])
    return names


def named_refs(root):
    """Skills/agents/commands named in instruction text that do not exist, and existing ones nothing names."""
    rows, _ = inventory(root)
    units = known_units(root)
    missing, mentioned = [], set()
    alltext = ""
    for r in rows:
        t = read(os.path.join(root, r["path"]))
        alltext += t
        for i, ln in enumerate(t.splitlines(), 1):
            for rx in NAMED:
                for m in rx.finditer(ln):
                    name = m.group(1) if rx is NAMED[0] else m.group(2)
                    mentioned.add(name)
                    if name not in units and name != os.path.basename(SELF_DIR):
                        missing.append({"file": r["path"], "line": i, "name": name})
    unreached = sorted(u for u in units if u != os.path.basename(SELF_DIR)
                       and not re.search(r"(?<![A-Za-z0-9_-])" + re.escape(u) + r"(?![A-Za-z0-9_-])",
                                         "\n".join(read(os.path.join(root, r["path"])) for r in rows if r["kind"] == "top")))
    return missing, unreached, len(units)


def refs(root):
    """(dead, checked, ambiguous). DEAD: the path starts in a folder that exists here and then leads nowhere,
    so it was meant for this project and is wrong. AMBIGUOUS: nothing of it exists here (a bare file name, or a
    first folder this project does not have); it may be written relative to another repository or machine,
    so it is listed for a human to read and never counted as a regression."""
    rows, _ = inventory(root)
    dead, ambiguous, checked = [], [], 0
    for r in rows:
        p = os.path.join(root, r["path"])
        base = os.path.dirname(p)
        for line, tok in candidate_paths(read(p)):
            checked += 1
            t = os.path.expanduser(tok)
            cands = [t] if os.path.isabs(t) else [os.path.join(base, t), os.path.join(root, t)]
            if any(os.path.exists(c.rstrip("/")) for c in cands):
                continue
            item = {"file": r["path"], "line": line, "ref": tok, "host_specific": os.path.isabs(t)}
            if os.path.isabs(t) or tok.startswith(("./", "../")):
                dead.append(item)
                continue
            parts = [x for x in tok.split("/") if x]
            first = parts[0] if parts else tok
            anchored = len(parts) > 1 and (os.path.isdir(os.path.join(base, first)) or os.path.isdir(os.path.join(root, first)))
            (dead if anchored else ambiguous).append(item)
    return dead, checked, ambiguous


SIGNALS = [
    # English and Turkish emphasis words, capitals only; other languages are read by hand
    ("PP-1 pressure", re.compile(r"\b(MUST|NEVER|ALWAYS|CRITICAL|IMPORTANT|MANDATORY|ASLA|MUTLAKA|KRİTİK|ÖNEMLİ|ZORUNLU|KESİNLİKLE)\b|!!")),
    ("PP-6 model fossil", re.compile(r"(?i)think step by step|take a deep breath|\b(gpt-[34]|claude[- ](2|3|instant)|sonnet 3\.\d|opus 3|haiku 3)\b|known issue with")),
    ("D1 history", re.compile(r"(?i)\b20\d\d-\d\d-\d\d\b|last updated|^\s*#+\s*change ?log|\bincident\b|added after")),
    ("PP-7 suppressor", re.compile(r"(?i)don'?t narrate|never use bullets|hold all findings")),
]


def signals(root):
    rows, _ = inventory(root)
    out = []
    for r in rows:
        if r["kind"] == "memory":
            continue  # lessons files are records; history is their payload
        in_fence = False
        for i, ln in enumerate(read(os.path.join(root, r["path"])).splitlines(), 1):
            if ln.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for cls, rx in SIGNALS:
                if rx.search(ln):
                    out.append({"file": r["path"], "line": i, "class": cls, "text": ln.strip()[:140],
                                "safety": bool(cls.startswith("PP-1") and SAFETY_LINE.search(ln))})
    return out, len(rows)


# matched against the file's own name only, so a folder called "secretary" flags nothing
SECRET_NAME = re.compile(r"(^|/)(\.env(\.[^/]*)?|[^/]*\.pem|[^/]*\.key|id_rsa[^/]*|id_ed25519[^/]*|[^/]*credentials[^/]*"
                         r"|([^/]*[._-])?secrets?([._-][^/]*)?\.(json|ya?ml|txt|env)|\.npmrc|\.pgpass)$", re.I)
# column names that suggest personal or payment data; only the header row of a CSV is ever read
PII_COLUMN = re.compile(r"(?i)(e[-_ ]?mail|e[-_ ]?posta|phone|telefon|gsm|iban|tckn|tc[-_ ]?(no|kimlik)|ssn|passport|pasaport"
                        r"|address|adres|birth|do[gğ]um|card|kart|price|fiyat|amount|tutar|payment|[oö]deme|salary|maa[sş])")
# a line about approval, secrets or data loss: capitals there are usually deliberate (keep-list)
SAFETY_LINE = re.compile(r"(?i)approv|onay|secret|gizli|password|parola|[sş]ifre|credential|token|delete|\bsil|production|prod\b|backup|yedek|push|deploy"
                         r"|privacy|personal data|ki[sş]isel veri|kvkk|gdpr|decrypt|vault"
                         r"|payment|[öo]deme|invoice|fatura|refund|\biade|\bsend\b|g[öo]nder|message|mesaj|irreversible|geri al[ıi]namaz")


def sh(args, cwd):
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def find_repos(root, depth=3):
    repos = []
    rc, top = sh(["git", "rev-parse", "--show-toplevel"], root)
    if rc == 0:
        repos.append(top.strip())
    root_d = root.rstrip(os.sep).count(os.sep)
    for dp, dns, _ in os.walk(root):
        if dp.count(os.sep) - root_d >= depth:
            dns[:] = []
            continue
        if ".git" in dns or os.path.isfile(os.path.join(dp, ".git")):
            rp = os.path.realpath(dp)
            if rp not in [os.path.realpath(x) for x in repos]:
                repos.append(dp)
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
    return repos


def git_report(root):
    if shutil.which("git") is None:
        return None
    out = []
    for repo in find_repos(root):
        info = {"repo": os.path.relpath(repo, root) if repo != root else "."}
        rc, b = sh(["git", "branch", "--show-current"], repo)   # git >= 2.22
        if rc != 0:
            rc, b = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
        info["branch"] = b.strip() or "(detached)"
        rc, ab = sh(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"], repo)
        if rc == 0 and ab.split():
            behind, ahead = ab.split()[:2]
            info["ahead"], info["behind"] = int(ahead), int(behind)
        else:
            info["ahead"] = info["behind"] = None  # no upstream configured
        _, refs_out = sh(["git", "for-each-ref", "--format=%(refname:short)\t%(upstream:short)", "refs/heads"], repo)
        tracked, unpushed = 0, []
        for ln in refs_out.splitlines():
            name, _, up = ln.partition("\t")
            if not up:
                continue
            tracked += 1
            rc2, cnt = sh(["git", "rev-list", "--count", f"{up}..{name}"], repo)
            if rc2 == 0 and cnt.strip().isdigit() and int(cnt) > 0:
                unpushed.append({"branch": name, "ahead": int(cnt)})
        info["branches_with_upstream"] = tracked
        info["branches_ahead"] = unpushed
        _, rem = sh(["git", "remote"], repo)
        info["remotes"] = len(rem.split())
        _, st = sh(["git", "status", "--porcelain"], repo)
        lines = [l for l in st.splitlines() if l and not l[3:].startswith(".maintenance/")]
        info["uncommitted"] = sum(1 for l in lines if not l.startswith("??"))
        info["untracked"] = sum(1 for l in lines if l.startswith("??"))
        _, staged = sh(["git", "diff", "--cached", "--name-only"], repo)
        big = []
        for f in staged.split("\n"):
            fp = os.path.join(repo, f)
            if f and os.path.isfile(fp) and os.path.getsize(fp) > 1_000_000:
                big.append({"path": f, "bytes": os.path.getsize(fp)})
        info["staged_count"] = len([f for f in staged.split("\n") if f])
        info["staged_large"] = big
        _, unt = sh(["git", "ls-files", "--others", "--exclude-standard"], repo)
        _, trk = sh(["git", "ls-files"], repo)
        info["secret_named_untracked"] = [f for f in unt.split("\n") if f and SECRET_NAME.search(f)
                                          and not f.startswith(".maintenance/")]
        info["secret_named_tracked"] = [f for f in trk.split("\n") if f and SECRET_NAME.search(f)
                                        and not f.endswith((".example", ".sample", ".template"))]
        pii = []
        for f in [x for x in (trk + "\n" + unt).split("\n") if x.lower().endswith(".csv")][:300]:
            try:
                with open(os.path.join(repo, f), encoding="utf-8", errors="replace") as fh:
                    head = fh.readline(4096)
            except OSError:
                continue
            cols = [c.strip().strip('"').strip("'") for c in re.split(r"[,;\t|]", head)]
            hit = [c for c in cols if c and len(c) < 40 and PII_COLUMN.search(c)]
            if len(hit) >= 2:
                pii.append({"path": f, "columns": hit[:8]})
        info["personal_data_headers"] = pii
        _, last = sh(["git", "log", "-1", "--format=%cI"], repo)
        info["last_commit"] = last.strip()
        out.append(info)
    return out


def collect(root):
    rows, lim = inventory(root)
    dead, checked, ambiguous = refs(root)
    sig, nfiles = signals(root)
    missing, unreached, nunits = named_refs(root)
    return {"mr_version": VERSION, "root": os.path.abspath(root), "limits": lim, "inventory": rows, "unreached_units": unreached,
            "missing_units": missing, "units_existing": nunits,
            "dead_refs": dead, "refs_checked": checked, "ambiguous_refs": len(ambiguous), "signals": sig,
            "git": git_report(root)}


def print_inventory(rows):
    if not rows:
        print("NOT MEASURED: 0 instruction files found (denominator 0). Is ROOT right?")
        return 2
    print(f"instruction files: {len(rows)}")
    print("kind\twords\tlines\tbytes\tover-limit\tlong-bullets\tpath")
    for r in rows:
        print(f"{r['kind']}\t{r['words']}\t{r['lines']}\t{r['bytes']}\t{'; '.join(r['over']) or '-'}\t{r['long_bullets']}\t{r['path']}")
    n = sum(1 for r in rows if r["over"])
    print(f"over limit: {n} of {len(rows)}")
    return 1 if n else 0


def compare(root, against, allow):
    old = json.load(open(against))
    new = collect(root)
    if old.get("mr_version") != VERSION:
        print(f"WARN baseline was written by helper version {old.get('mr_version', 'unknown')}, this is {VERSION}: "
              f"figures may not be comparable; re-save the baseline if no instruction file changed since")
    reg = []
    o_inv = {r["path"]: r for r in old["inventory"]}
    for r in new["inventory"]:
        o = o_inv.get(r["path"])
        if r["over"] and (not o or not o["over"]):
            reg.append(f"NEW OVER LIMIT {r['path']}: {'; '.join(r['over'])}")
        if o and r["path"] not in allow:
            if r["words"] > o["words"]:
                reg.append(f"GREW WITHOUT APPROVAL {r['path']}: {o['words']} -> {r['words']} words")
            elif "sha" in o and r["sha"] != o["sha"]:
                reg.append(f"CHANGED WITHOUT APPROVAL {r['path']}: {o['words']} -> {r['words']} words, content differs")
        if not o and r["path"] not in allow:
            reg.append(f"NEW INSTRUCTION FILE {r['path']} ({r['words']} words) not in --allow-grow")
    old_dead = {(d["file"], d["ref"]) for d in old["dead_refs"]}
    for d in new["dead_refs"]:
        if (d["file"], d["ref"]) not in old_dead:
            reg.append(f"NEW DEAD REF {d['file']}:{d['line']} -> {d['ref']}")
    old_miss = {(d["file"], d["name"]) for d in old.get("missing_units", [])}
    for d in new["missing_units"]:
        if (d["file"], d["name"]) not in old_miss:
            reg.append(f"NEW MISSING UNIT {d['file']}:{d['line']} -> {d['name']}")
    gone = set(o_inv) - {r["path"] for r in new["inventory"]}
    for g in sorted(gone):
        if g not in allow:
            reg.append(f"INSTRUCTION FILE GONE {g} (not in --allow-grow; a removal must be approved)")
    tot_o = sum(r["words"] for r in old["inventory"])
    tot_n = sum(r["words"] for r in new["inventory"])
    print(f"files {len(old['inventory'])} -> {len(new['inventory'])}; words {tot_o} -> {tot_n}; "
          f"over-limit {sum(1 for r in old['inventory'] if r['over'])} -> {sum(1 for r in new['inventory'] if r['over'])}; "
          f"dead paths {len(old['dead_refs'])} -> {len(new['dead_refs'])}; "
          f"missing units {len(old.get('missing_units', []))} -> {len(new['missing_units'])}")
    if reg:
        print("REGRESSION (abort rule):")
        for x in reg:
            print("  " + x)
        return 3
    print("no regression")
    return 0


def selftest():
    """Negative controls: plant one fault per check, confirm it fires; remove, confirm silence."""
    fails = []
    d = tempfile.mkdtemp(prefix="mr-selftest-")
    try:
        os.makedirs(os.path.join(d, ".claude", "skills", "demo"))
        clean_top = "# Project\n\nRun `scripts/build.sh` to build. Release notes use the changelog skill.\n"
        os.makedirs(os.path.join(d, "scripts"))
        os.makedirs(os.path.join(d, "docs"))
        open(os.path.join(d, "scripts", "build.sh"), "w").write("echo ok\n")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top)
        open(os.path.join(d, ".claude", "skills", "demo", "SKILL.md"), "w").write("---\nname: demo\n---\nDo the thing.\n")
        # silence checks
        rows, _ = inventory(d)
        if len(rows) != 2:
            fails.append(f"inventory: expected 2 files, saw {len(rows)}")
        if any(r["over"] for r in rows):
            fails.append("inventory: clean fixture reported over limit")
        if refs(d)[0]:
            fails.append(f"refs: clean fixture reported dead refs {refs(d)[0]}")
        if signals(d)[0]:
            fails.append(f"signals: clean fixture fired {signals(d)[0]}")
        if named_refs(d)[1] != ["demo"]:
            fails.append(f"named refs: unreached-unit control expected ['demo'], got {named_refs(d)[1]}")
        # fire checks
        big = "word " * (DEFAULT_LIMITS["skill_words"] + 1)
        open(os.path.join(d, ".claude", "skills", "demo", "SKILL.md"), "w").write(big)
        if not any(r["over"] for r in inventory(d)[0]):
            fails.append("inventory: over-limit skill did not fire")
        # the byte limit is Codex's: it applies to AGENTS.md only, and only when Codex is seen
        global CODEX_HOME
        real_home, CODEX_HOME = CODEX_HOME, os.path.join(d, "no-codex-home")
        blob = "# Agents\n\n" + ("x" * 99 + "\n") * 400
        for name in ("AGENTS.md", "GEMINI.md"):
            open(os.path.join(d, name), "w").write(blob)
        over = lambda: sorted(r["path"] for r in inventory(d)[0] if any(o.startswith("bytes") for o in r["over"]))
        if over():
            fails.append(f"limits: byte limit fired with no Codex in sight: {over()}")
        os.makedirs(os.path.join(d, ".codex"))
        if over() != ["AGENTS.md"]:
            fails.append(f"limits: Codex seen, 40 KB AGENTS.md should be the only byte finding: {over()}")
        open(os.path.join(d, ".codex", "config.toml"), "w").write("model = \"x\"\nproject_doc_max_bytes = 65536\n")
        if over() or codex_limit(d)[0] != 65536:
            fails.append(f"limits: raised project_doc_max_bytes not honoured: {codex_limit(d)}")
        shutil.rmtree(os.path.join(d, ".codex"))
        os.remove(os.path.join(d, "AGENTS.md"))
        os.remove(os.path.join(d, "GEMINI.md"))
        CODEX_HOME = real_home
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "See `docs/missing.md`.\nYou MUST think step by step.\nAdded 2025-01-02 after the incident.\n")
        if not any(x["ref"] == "docs/missing.md" for x in refs(d)[0]):
            fails.append("refs: dead path did not fire")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "In the other repo see `vscode/` and `elsewhere/notes.md`, and `NOTES.md`.\n")
        dd, _, amb = refs(d)
        if dd or sorted(x["ref"] for x in amb) != ["NOTES.md", "elsewhere/notes.md", "vscode/"]:
            fails.append(f"refs: ambiguous control wrong: dead={[x['ref'] for x in dd]} ambiguous={[x['ref'] for x in amb]}")
        # ignored folders, virtual environments and excluded globs are not the project
        for sub in (".venv-test", os.path.join("ignored", "x"), os.path.join("old", "x"), "pyenv",
                    "inner", os.path.join("inner", "junk")):
            os.makedirs(os.path.join(d, sub))
            open(os.path.join(d, sub, "CLAUDE.md"), "w").write("# Sub\n")
        open(os.path.join(d, "pyenv", "pyvenv.cfg"), "w").write("home = x\n")
        os.makedirs(os.path.join(d, ".maintenance"), exist_ok=True)
        json.dump({"exclude": ["old/*"]}, open(os.path.join(d, ".maintenance", "limits.json"), "w"))
        if shutil.which("git"):
            sh(["git", "init", "-q"], d)
            # a repository the workspace ignores is still scanned, by its own ignore rules
            open(os.path.join(d, ".gitignore"), "w").write("ignored/\ninner/\n")
            sh(["git", "init", "-q"], os.path.join(d, "inner"))
            open(os.path.join(d, "inner", ".gitignore"), "w").write("junk/\n")
            _IGNORED.clear()
            got = sorted(r["path"] for r in inventory(d)[0])
            if got != [".claude/skills/demo/SKILL.md", "CLAUDE.md", "inner/CLAUDE.md"]:
                fails.append(f"inventory: ignored/venv/excluded/nested-repo control wrong: {got}")
            shutil.rmtree(os.path.join(d, ".git"))
            os.remove(os.path.join(d, ".gitignore"))
            _IGNORED.clear()
        for sub in (".venv-test", "ignored", "old", "pyenv", "inner"):
            shutil.rmtree(os.path.join(d, sub))
        os.remove(os.path.join(d, ".maintenance", "limits.json"))
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "ASLA production'a onaysız dokunma.\n")
        s_tr = signals(d)[0]
        if not s_tr or not s_tr[0].get("safety"):
            fails.append(f"signals: Turkish emphasis on a safety rule not tagged: {s_tr}")
        for line, want in (("İçeriği ASLA Drive'a kopyalama, kişisel veri içerir.", True),
                            ("NEVER send the payment link twice.", True),
                            ("ASLA uzun paragraf yazma.", False)):
            open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + line + "\n")
            got = signals(d)[0]
            if not got or bool(got[0].get("safety")) != want:
                fails.append(f"signals: safety tag {'missing' if want else 'false alarm'} on {line!r}: {got}")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "Deploy with scripts/gone.sh after reading https://example.com/a/b.md and scripts/build.sh.\n")
        open(os.path.join(d, "CLAUDE.md"), "a").write("Check `/ready` and `/api/v1/users.json` on staging.\n"
                                                      "Then `scripts/build.sh --fast` and `git switch -c wip/x`.\n")
        if [x["ref"] for x in refs(d)[0]] != ["scripts/gone.sh"]:
            fails.append(f"refs: command-span silence control fired {[x['ref'] for x in refs(d)[0]]}")
        open(os.path.join(d, "CLAUDE.md"), "a").write("Run `scripts/nope.sh staging` last.\n")
        if "scripts/nope.sh" not in [x["ref"] for x in refs(d)[0]]:
            fails.append("refs: dead path inside a backticked command did not fire")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "Deploy with scripts/gone.sh after reading https://example.com/a/b.md and scripts/build.sh.\n")
        bare = [x["ref"] for x in refs(d)[0]]
        if bare != ["scripts/gone.sh"]:
            fails.append(f"refs: bare-path control expected ['scripts/gone.sh'], got {bare}")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "See `docs/missing.md`.\nYou MUST think step by step.\nAdded 2025-01-02 after the incident.\n")
        open(os.path.join(d, "CLAUDE.md"), "a").write("Release via the `ship` skill. Demo via the `demo` skill.\n")
        miss, unr, _ = named_refs(d)
        if not any(x["name"] == "ship" for x in miss):
            fails.append("named refs: missing skill did not fire")
        if any(x["name"] == "demo" for x in miss):
            fails.append("named refs: existing skill reported missing")
        classes = {s["class"] for s in signals(d)[0]}
        for c in ("PP-1 pressure", "PP-6 model fossil", "D1 history"):
            if c not in classes:
                fails.append(f"signals: {c} did not fire")
        # compare / abort rule
        open(os.path.join(d, ".claude", "skills", "demo", "SKILL.md"), "w").write("---\nname: demo\n---\nDo the thing.\n")
        open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top)
        base = os.path.join(d, "base.json")
        json.dump(collect(d), open(base, "w"))
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            if compare(d, base, []) != 0:
                fails.append("compare: unchanged tree reported a regression")
            open(os.path.join(d, "CLAUDE.md"), "a").write("More text here.\n")
            if compare(d, base, []) != 3:
                fails.append("compare: growth without approval did not fire")
            if compare(d, base, ["CLAUDE.md"]) != 0:
                fails.append("compare: approved growth still fired")
            open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top.replace("Project", "Product"))
            if compare(d, base, []) != 3:
                fails.append("compare: same-length rewrite without approval did not fire")
            open(os.path.join(d, "CLAUDE.md"), "w").write(clean_top + "More text here.\n")
            open(os.path.join(d, "CLAUDE.md"), "a").write("Use the `ghost` skill.\n")
            if compare(d, base, ["CLAUDE.md"]) != 3:
                fails.append("compare: new missing unit did not fire")
        # git checks
        if shutil.which("git"):
            g = os.path.join(d, "repo")
            os.makedirs(g)
            sh(["git", "init", "-q"], g)
            open(os.path.join(g, ".env"), "w").write("X=1\n")
            os.makedirs(os.path.join(g, "secretary"))
            open(os.path.join(g, "secretary", "notes.txt"), "w").write("hi\n")
            open(os.path.join(g, "client_secret.json"), "w").write("{}\n")
            open(os.path.join(g, "export.csv"), "w").write("Ad,E-posta,Tutar\nx,y,1\n")
            open(os.path.join(g, "plain.csv"), "w").write("x,y\n1,2\n")
            open(os.path.join(g, "blob.bin"), "wb").write(os.urandom(1_200_000))
            sh(["git", "add", "blob.bin"], g)
            rep = [r for r in git_report(d) if r["repo"] == "repo"]
            if not rep:
                fails.append("git: nested repo not discovered")
            else:
                r = rep[0]
                if ".env" not in r["secret_named_untracked"]:
                    fails.append("git: untracked .env not reported")
                if sorted(r["secret_named_untracked"]) != [".env", "client_secret.json"]:
                    fails.append(f"git: secret-name control wrong: {r['secret_named_untracked']}")
                if [x["path"] for x in r["personal_data_headers"]] != ["export.csv"]:
                    fails.append(f"git: personal-data header control wrong: {r['personal_data_headers']}")
                if not r["staged_large"]:
                    fails.append("git: staged 1.2 MB file not reported")
                if r["ahead"] is not None or r["branches_with_upstream"] != 0:
                    fails.append("git: repo without upstream reported an ahead count")
        else:
            print("selftest: git not installed; git checks NOT MEASURED")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if fails:
        print("SELFTEST FAIL")
        for f in fails:
            print("  " + f)
        return 4
    print("SELFTEST PASS (inventory, limits, refs, named units, signals, compare, git)")
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    root = "."
    if rest and not rest[0].startswith("--"):
        root = rest.pop(0)
    root = os.path.abspath(root)
    if cmd == "selftest":
        return selftest()
    if not os.path.isdir(root):
        print(f"no such directory: {root}")
        return 2
    if cmd == "limits":
        lim = limits_for(root)
        src = "defaults + .maintenance/limits.json" if os.path.isfile(os.path.join(root, ".maintenance", "limits.json")) else "defaults"
        print(f"limits in force ({src}):")
        cb, csrc = codex_limit(root, lim)
        for k in DEFAULT_LIMITS:
            v = (f"{cb} ({csrc})" if cb else f"off ({csrc})") if k == "top_bytes" else lim[k]
            print(f"  {k}\t{v}\t# {LIMIT_WHY[k]}")
        print("These defaults come from one real multi-agent setup; they are a starting point, not a standard.")
        return 0
    if cmd == "inventory":
        return print_inventory(inventory(root)[0])
    if cmd == "refs":
        dead, checked, ambiguous = refs(root)
        print(f"path references checked: {checked}; dead: {len(dead)}; ambiguous: {len(ambiguous)}")
        for x in dead:
            print(f"{x['file']}:{x['line']}\tDEAD\t{x['ref']}{'  (absolute: host-specific)' if x['host_specific'] else ''}")
        if ambiguous:
            print("ambiguous = nothing of the path exists here; it may be relative to another repository or machine. Read, do not count:")
            for x in ambiguous:
                print(f"{x['file']}:{x['line']}\tAMBIGUOUS\t{x['ref']}")
        missing, unreached, nunits = named_refs(root)
        print(f"named skills/agents/commands: {nunits} exist; named but missing: {len(missing)}; existing but named in no top-level file: {len(unreached)}")
        for x in missing:
            print(f"{x['file']}:{x['line']}\tMISSING UNIT\t{x['name']}")
        for u in unreached:
            print(f"-\tUNREACHED UNIT\t{u}")
        return 2 if checked == 0 and nunits == 0 else (1 if dead or missing or unreached else 0)
    if cmd == "signals":
        sig, n = signals(root)
        print(f"signals: {len(sig)} over {n} instruction files (candidates only; adjudicate each)")
        for s in sig:
            print(f"{s['file']}:{s['line']}\t{s['class']}{' [safety rule: likely keep]' if s.get('safety') else ''}\t{s['text']}")
        return 2 if n == 0 else (1 if sig else 0)
    if cmd == "git":
        g = git_report(root)
        if g is None:
            print("NOT MEASURED: git not installed")
            return 2
        if not g:
            print("NOT MEASURED: no git repository at or under ROOT (depth 3)")
            return 2
        flag = 0
        for r in g:
            print(json.dumps(r))
            if (r["staged_large"] or r["secret_named_untracked"] or r["secret_named_tracked"]
                    or r["branches_ahead"] or r["branches_with_upstream"] == 0 or r["personal_data_headers"]):
                flag = 1
        return flag
    if cmd == "baseline":
        if "--save" not in rest:
            print("usage: mr.py baseline [ROOT] --save FILE")
            return 2
        f = rest[rest.index("--save") + 1]
        data = collect(root)
        os.makedirs(os.path.dirname(os.path.abspath(f)), exist_ok=True)
        json.dump(data, open(f, "w"), indent=1)
        n = len(data["inventory"])
        print(f"baseline saved: {f} ({n} instruction files, {sum(1 for r in data['inventory'] if r['over'])} over limit, "
              f"{len(data['dead_refs'])} dead paths of {data['refs_checked']} checked ({data['ambiguous_refs']} ambiguous), "
              f"{len(data['missing_units'])} missing units ({data['units_existing']} exist), {len(data['signals'])} signals)")
        return 2 if n == 0 else 0
    if cmd == "compare":
        if "--against" not in rest:
            print("usage: mr.py compare [ROOT] --against FILE [--allow-change PATH ...]")
            return 2
        f = rest[rest.index("--against") + 1]
        allow = []
        for flag in ("--allow-change", "--allow-grow"):
            if flag in rest:
                for a in rest[rest.index(flag) + 1:]:
                    if a.startswith("--"):
                        break
                    allow.append(a)
        return compare(root, f, allow)
    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
