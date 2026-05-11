# Contributing to Eri

## TL;DR — the rules that matter most

1. **Never push to `main`.** Always work in a branch off `dev` and open a PR.
2. **One issue, one branch, one PR.** Use the issue number in the branch name.
3. **If you change a shared file, ping the other person before merging.** Shared files are: `src/router.tsx`, `tailwind.config.ts`, `src/index.css`, `requirements.txt`, `package.json`, anything in `src/components/eri/`.
4. **Pull from `dev` at least once a day.** End-of-day sync is mandatory.
5. **If you break the build, fix it or revert within 30 minutes.** Don't leave others blocked.
6. **No secrets in commits.** Squad keys, API key, JWT secrets all live in `.env.local` (gitignored).

---

## For the frontend. First install all dependencies. after cloning
```bash
  cd Desktop
  git clone https://github.com/PetJs/Eri.git
  cd Eri
  cd frontend
  npm install
  npm run dev
```

## Who owns what

| Person | Owns | Don't touch without asking |
|---|---|---|
| **Backend dev** | `backend/`, `notebooks/`, `models/`, Squad integration, AI engines | `frontend/` |
| **FE-1** | `src/routes/buyer/`, `src/lib/api/`, hooks for buyer flow | `src/routes/supplier/`, `src/routes/admin/`, `src/routes/public/` |
| **FE-2** | `src/routes/supplier/`, `src/routes/admin/`, `src/routes/public/`, `src/components/eri/`, design system | `src/routes/buyer/` |

**Shared files** (anyone can edit, but ping the team first):
- `src/router.tsx` — both FE-1 and FE-2 add routes here
- `tailwind.config.ts`, `src/index.css`, `src/styles/fonts.css` — design tokens
- `package.json`, `requirements.txt` — dependencies
- `src/lib/api/types.ts` — shared with backend; if you change a type, tell the backend dev
- `docs/*` — anyone can update, but say so in standup

---

## Branch strategy

```
main      ← deployed/demo branch. Only PRs from dev land here. PROTECTED.
  ↑
dev       ← integration branch. All work merges here first.
  ↑
feat/issue-18-verify-page    ← feature branches
chore/issue-22-landing
backend/issue-7-anomaly-notebook
```

### Branch naming

```
<desc>/<issue-number>-<short-slug>
```

Examples:
- `feat/issue-18-verify-page` — working on issue #18
- `fe2/issue-22-landing` — FE-2 working on issue #22
- `backend/issue-13-squad-virtual-accounts` — backend dev on issue #13
- `backend/hotfix-nafdac-scraper-timeout` — for urgent fixes (no issue yet)

Don't use spaces. Don't use uppercase. 

### Creating a branch

```bash
# Always start from latest dev
git checkout dev
git pull origin dev

# Create your branch
git checkout -b feat/issue-18-verify-page

# Work, commit, push
git push -u origin feat/issue-18-verify-page
```

---

## Commits

### Format

```
<type>: <short description>

<optional longer explanation>

Refs #<issue-number>
```

### Types

- `feat:` — a new feature or page
- `fix:` — a bug fix
- `refactor:` — changing code without changing behavior
- `style:` — formatting, whitespace, no logic change
- `docs:` — documentation only
- `test:` — adding or fixing tests
- `chore:` — config, deps, build setup

### Examples

```
feat: add TrustScoreRing component with count-up animation

Refs #17

fix: NAFDAC scraper times out after 5s instead of hanging

Refs #10

chore: bump framer-motion to 11.11.17

refactor: extract verification checklist from verify page

The checklist is now a standalone component used in both
the verify-supplier page and the delivery verification page.

Refs #18 #20
```

### Keep commits small

A commit should be one logical change. If you've been working for 4 hours without committing, you've been working wrong.

**Rough target:** at least one commit per hour of work.

---

## Pull Requests

### When to open a PR

Open a PR **as soon as the work is reviewable**, not when it's perfect. Draft PRs are fine — they let teammates see progress and catch design issues early.

### PR title

Same format as commits: `feat: add buyer dashboard page`

### PR description template

Copy-paste this into every PR:

```markdown
## What
Brief description of what this PR does.

## Why
Why this change matters (or which issue it closes).

## How to test
1. `git checkout fe1/issue-18-verify-page`
2. `cd frontend && npm run dev`
3. Visit http://localhost:3000/verify
4. Fill the form, click Verify
5. Should see the score ring animate in 0 → 62

## Screenshots / Loom
(For frontend PRs, always include a screenshot or short Loom video.)

## Checklist
- [ ] Branch is up to date with `dev`
- [ ] No console errors
- [ ] Tested locally end-to-end
- [ ] Updated relevant docs (if applicable)
- [ ] No secrets in commits

Closes #<issue-number>
```

### Reviewing

- **PRs need 1 approval before merging.**
- **Reviewer should test locally**, not just read the diff.
- **Comment with intent:** "blocking" (must fix), "suggestion" (nice to have), "nit" (style preference, ignore if you disagree)
- **Don't approve and merge your own PR.** Even if the reviewer is slow, ping them.

### Merging

- Use **Squash and merge**. This keeps `dev` history clean — one commit per PR.
- Delete the branch after merging.

---


```bash
git checkout dev
git pull origin dev
git checkout your-branch
git rebase dev      # or: git merge dev — your call
```

Resolve any conflicts before starting work. If something major changed, ping the team in chat.

### During work

Commit every meaningful unit of progress. Push at least once a day even if work is incomplete.

```bash
git add -A
git commit -m "feat: add escrow status card skeleton"
git push
```

### End of feature

1. Push everything
2. If your branch is ready, open a PR
3. Review at least one teammate's PR if they have one open
4. Post in chat: "Done for the day. PR #N up for review. Blocked on X."

---

## Conflicts — how to handle them

### Code conflicts

When `git rebase dev` shows conflicts:

```bash
# See what's conflicted
git status

# Open the conflicted files, find the <<<<<<< HEAD markers, edit to resolve
# Then:
git add <resolved-files>
git rebase --continue
```

If you're stuck, **don't force-push over the conflict.** Ask the teammate who owns the conflicting file. Two minutes of chat saves an hour of debugging.

### Schema / API conflicts

If the backend dev changes an API response shape, the frontend code that calls it breaks. To prevent this:

1. **Backend dev** changes the type in `app/schemas/*.py`
2. **Backend dev** posts in chat: "Heads up: changed `Order.status` to add a `disputed` state. Frontend should add this to the union type."
3. **Frontend dev** mirrors the change in `src/lib/api/types.ts`
4. Both PRs reference each other

If you find an API mismatch mid-build, **don't silently work around it.** Tell the backend dev.

---

## Code style

### TypeScript (frontend)

- Always type props (`interface FooProps { ... }`)
- No `any` in production code (`unknown` is fine when needed)
- Prefer named exports over default exports (except for pages, which Next.js/React Router conventions handle their own way)
- camelCase for variables and functions, PascalCase for components

### Both

- **No dead code.** If you commented something out for testing, delete it before merging.
- **No `console.log` / `print` debug statements in merged PRs.** Use proper logging.
- **No `TODO` without an issue.** If you can't finish it now, file an issue.

---

## Testing

### Backend

```bash
cd backend
pytest -v
```

If you add a new engine or integration, add at least one test. The bar is "does it run without crashing on a happy-path input."

### Before opening a PR

Always run the build:

```bash
# Backend
cd backend && pytest -q

# Frontend
cd frontend && npm run build
```

If either fails, fix it before opening the PR.

---

## Secrets and `.env`

### What goes in `.env.local`

- `SQUAD_SECRET_KEY` — Squad sandbox secret
- `ANTHROPIC_API_KEY` — Claude API key
- `JWT_SECRET` — random 32-byte string
- `DATABASE_URL` (if you change from the default)

### What does NOT go in commits

**Anything from `.env.local`.** Ever.

If you accidentally commit a secret:

1. **Don't just delete it in the next commit.** Git history keeps it forever.
2. **Rotate the key immediately** (regenerate it in the Squad / Anthropic dashboard).
3. **Tell the team** so we can update everyone's `.env.local`.

### `.env.example`

We commit a `.env.example` with **placeholder values** so new devs know what env vars are needed:

```bash
SQUAD_SECRET_KEY=sandbox_sk_xxx
ANTHROPIC_API_KEY=sk-ant-xxx
JWT_SECRET=change-me-to-32-random-bytes
```

When you add a new env var to your code, **also add it to `.env.example`**.

---

## Documentation

### When to update docs

- **New API endpoint** → update `docs/api.md`
- **New env var** → update `.env.example` and `README.md`
- **New shared component** → ensure it's documented in `STITCH_PROMPTS.md` or `FRONTEND_STRUCTURE.md`
- **Architecture decision** → write a short note in `docs/decisions/`

### When NOT to update docs

- Internal refactors
- Bug fixes that don't change behavior
- Style/formatting changes

---

## Issues

### Use the existing issue list

We have 33 issues already created from `ISSUES.md`. Each one has:
- A clear acceptance checklist
- A priority label
- An owner role (FE-1, FE-2, backend)

**Pick from the list.** Don't invent new work without filing a new issue.

### Creating a new issue

If you find something that needs doing:

1. Check existing issues first (use the search)
2. If genuinely new, create an issue with:
   - Clear title
   - 1-2 sentence description of the problem
   - Why it matters
   - Suggested approach (if you have one)
   - Label: `priority:p0` / `p1` / `p2` and a role label

### Closing issues

- Reference the issue number in your PR description (`Closes #18`)
- GitHub will auto-close the issue when the PR merges

---

## Communication

### Standup (5 min, daily)

Same three questions every day:

1. What did you finish yesterday?
2. What are you doing today?
3. What's blocking you?

If you're blocked, say so. Don't suffer silently.

## Quick reference

```bash
# Start work on a new issue
git checkout dev && git pull
git checkout -b fe1/issue-N-description

# Mid-work: stay in sync
git fetch origin
git rebase origin/dev      # rebase your branch onto latest dev

# Done: push and PR
git push -u origin fe1/issue-N-description
# → open PR in GitHub UI, use template from this doc

# After PR is merged
git checkout dev && git pull
git branch -d fe1/issue-N-description    # delete local branch
```

---

## Questions

If anything in this doc is unclear, just ask. 
