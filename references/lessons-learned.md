# Running the round: rules learned the hard way

These came from real rounds. Each one is here because the failure happened.
- **Verify the done.** A commit reported as "untracked the files" changed only `.gitignore`: `git rm --cached` followed by `git commit -- <paths>` re-adds the files from disk. Check every "done" against the diff that landed (`git show --stat`), never against the tool's success message.
- **Review the round's own commits.** A distil commit once copied raw notes containing another project's text into a shared repo. Before closing, list every file the round committed and check that each belongs in that repo.
- **Read the live lines before applying a drafted diff.** A drafted OLD/NEW would have deleted a neighbouring rule and duplicated another; only re-reading the live file caught it.
- **Quote the human, never paraphrase.** A paraphrased sentence was attached to the wrong subject in a brief.
- **A gate question must stand on its own.** "Which of SP-41..44?" got the answer "How would I know what those are?" Say what changes, where and why.
- **Safe option first on dangerous questions.** An accidental Enter answered a host-changing question with the recommended first option. It was stopped within a minute, but only because a human was watching.
- **An approved wording change can blind a check keyed to the old wording.** Re-run the controls after every instruction-file commit, inside the closing distil too.
- **A comparison tool that silently drops unmatched cases is not a comparison.** Check that before/after runs used the same case set.
- **A stop condition fires on a disappearance too, not only an addition.** When one fires, ask with the evidence rather than reinterpreting it alone.
- **A bulk delete the permission layer refuses goes to the human as one prepared script with frozen target lists.** Never split it into smaller calls to get around the refusal.
- **An answer page whose state lives in the viewer's browser does not reach the session.** Ask for the answer text back, or use a store the session can read.
- **Measurement tools can report green while measuring nothing.** A checker read one folder level and missed 121 files; a collector reported "no inboxes" while 12 were waiting. This is why every check has a negative control and every zero has a denominator.
- **An absurd number (0 of N, N of 0) is first a sign of a wrong path or another session's write**, not a finding.
- **A step that ran and a step that was skipped look the same unless the report has a section for each.**
- **A check that only counts words misses a rewrite of the same length.** The helper compares content hashes for this reason; any instruction file that changed must be named as approved.
