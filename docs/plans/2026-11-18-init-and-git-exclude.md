# Plan: `just init` and git-excluded repo outputs

| | |
|---|---|
| **Status** | Approved and executed 2026-11-18 |
| **Implements** | D-014 (DEV-7), D-015 (INS-9) in the [specification](../SPECIFICATION.md) |
| **Depends on** | galtzagorri G-006 (INI-1) and G-007 (PKG-2) |
| **Date** | 2026-11-18 |

## Starting point

Facts checked on 2026-11-18:

- `app.run_scope` loads the scope's manifest, plans, applies and saves it. After `apply`, `manifest.entries` holds every owned target (`Entry.target`, `Entry.mode`). File and link targets are paths under the root; CLI registrations are not paths.
- Nothing in `src/` writes `.gitignore` or `.git/info/exclude` today.
- `lantoki plan repo ~/repos/galtzagorri --all` targets `.claude/rules/*`, `.claude/skills/*`, `.github/instructions/*`, `.github/prompts/*`, `.github/skills/*` and `AGENTS.md`.
- lantoki's own repository commits `AGENTS.md` and ignores its outputs in `.gitignore`.

## Phase 1: exclude block (D-015, INS-9)

1. **Generic core, no provider names (PRI-3).** In a new module, `gitexclude.py`, write pure functions:
   - `render_block(paths) -> str`: sorted, `/`-anchored entries between `# >>> lantoki (managed, do not edit) >>>` and `# <<< lantoki <<<`.
   - `merge(existing_text, block) -> str`: replaces the block, adds it, or removes it when it is empty. Lines outside the block are never changed.
2. **Locating the file.** `git -C <repo> rev-parse --git-path info/exclude`, resolved against the repo, so worktrees and `GIT_DIR` work. Not a git repository → skip with a warning. In `plan repo`, also flag owned targets that git already tracks (`git ls-files`) with a warning.
3. **Wiring.** `run_scope`, project scope and `apply` only: after `manifest.save`, write the block from the manifest's path-like entries. The block follows the manifest, so pruned targets leave it.
4. **Tests (tmp repos made with `git init`, QLT-5).** Cover:
   - The block is created, updated, and removed when the repo has no targets.
   - Foreign lines are kept.
   - A worktree.
   - Not a git repository.
   - A tracked target produces a warning.
   - `merge` cases, unit-tested without git.

**Check:** `just check`; golden tests unchanged; `lantoki plan user` identical to the 2026-11-18 baseline (user scope is untouched).

## Phase 2: `just init` for lantoki (D-014, DEV-7)

After galtzagorri G-006 is pushed:

1. `just update`.
2. `project.just`: add `init-project: sync-user`, and point `install-tools` at the template's `install-tool-editable` (galtzagorri PKG-2). `packaging.just` is removed by the update.
3. README *Getting started*: `git clone` + `sudo apt install just` + `just init` reproduces the setup (PUR-2).
4. Remove lantoki's own `.gitignore` block for its outputs. The exclude block replaces it.

**Check:** `just init` on this machine ends with *all checks passed*. `git status` is clean, and `.git/info/exclude` holds the block.

## Phase 3: existing repositories

Run `lantoki sync repo <path>` once in each repository that already has lantoki outputs, to write their blocks. Their `.gitignore` entries can then be removed by each project, in its own time.

## Results (2026-11-18)

- **Phase 1:** 12 new tests (146 in total). `plan user` still reports 25 unchanged.
- **Phase 2:** `just init` was run without `install-system`, because sudo needs a password that the agent does not have. All other steps ran: `init-git`, `install-user`, `install-env`, `install-tool-editable`, `init-hook` (`sync-user`: 25 unchanged), `init-ai` (6 unchanged) and `check`. They ended with *all checks passed*. The tree is clean, and `.git/info/exclude` holds the 6 targets.
- **Phase 3:** lantoki is the only repository with a manifest. An empty manifest for a temp folder was deleted: an early, unisolated run of galtzagorri's `init-ai` test had created it.
- **Found:** the template's `install-python` (`pdm use --first`) recreates `.venv` on every run, so `init` and `update` reinstall every dependency. They still end in a working environment, but slowly. Fixing it is template work, outside this plan.

## Risks

| Risk | Mitigation |
|---|---|
| A user edits inside the block | It is rewritten on the next sync; the marker says so. |
| A target is already tracked by git, so excluding it would be ineffective | It is not excluded, and `plan repo` warns. |
| `git` missing on `PATH` | Skip with a warning. Installing still works. |

## Out of scope

- Writing to the repository's committed `.gitignore`.
- Changing which targets lantoki installs.
