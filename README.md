# swe-site

MkDocs Material site that publishes four sections as one site at
**https://swe.springlee.dev**, deployed on Cloudflare Pages.

## Layout

Content sources live under `content/`:

| Section | Source | Tracked how |
| ------- | ------ | ----------- |
| LeetCode Algorithms | `content/leetcode-algorithms/` | git **submodule** → [leetcode-algorithms](https://github.com/software-engineer-learning/leetcode-algorithms) |
| SWE Interview | `content/swe/` | in this repo |
| System Design | `content/system-design/` | in this repo (vendored from [liquidslr/system-design-notes](https://github.com/liquidslr/system-design-notes)) |
| Real Interview Questions | `content/real-interview-questions/` | in this repo |

Three of the four sections are edited here directly. Only LeetCode stays a
separate repo, because it has its own GitBook publication, PR workflow and
solution-generation tooling.

## How it works

- `scripts/prepare.sh` copies `content/*` into `docs/leetcode/`, `docs/swe/`,
  `docs/system-design/` and `docs/real-interview-questions/`, relocates GitBook
  assets to `_assets/`, and converts each source's GitBook `SUMMARY.md` into
  mkdocs-literate-nav format via `scripts/convert_summary.py`.
- `docs/SUMMARY.md` defines the top-level tabs (Home / LeetCode Algorithms / SWE
  Interview / System Design / Real Interview Questions); each section's nav comes
  from its converted SUMMARY.
- `swe` and `real-interview-questions` are copied the same way — every `*.md`
  except `SUMMARY.md` and their own `CLAUDE.md` — so maintenance docs stay out of
  the published site.
- `system-design` has no SUMMARY.md, so `scripts/gen_nav.py` generates one from its
  `NN. Chapter Name/README.md` folders, ordered by the numeric prefix and labelled
  with each chapter's H1. It also mixes `Readme.md` and `README.md` casing;
  `prepare.sh` normalises it, because only an exact `README.md` becomes a directory
  index and the chapters' raw `<img src="./images/...">` tags resolve only from that
  index URL.
- `scripts/leetcode_titles.py` gives every LeetCode `solution.md` an `<h1>` naming
  its problem and cross-links it with the matching `description.md`. Material's
  search titles a page by its first `<h1>`, so solutions opening with `# Intuition`
  were previously unreachable by problem number — searching "3876" found only the
  description, the SUMMARY page and the README index. It rewrites only the copies
  under `docs/`, never the submodule.
- Math: content uses GitBook-style inline `$$O(...)$$`; rendered client-side by
  KaTeX auto-render (`docs/javascripts/katex.js`).

## Local development

```bash
git clone --recurse-submodules https://github.com/software-engineer-learning/swe-site.git
# already cloned without it:
git submodule update --init --recursive

python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
bash scripts/prepare.sh
.venv/bin/mkdocs serve   # http://127.0.0.1:8000
```

Edit `content/swe/`, `content/system-design/` and
`content/real-interview-questions/` in place, then re-run `prepare.sh`. Never edit
under `docs/` — `prepare.sh` wipes those four directories on every run.

To pull new LeetCode solutions into your checkout:

```bash
git submodule update --remote content/leetcode-algorithms
```

You rarely need to do this by hand: after a successful deploy, CI commits the
bumped pointer back to `main` itself, so the recorded pointer names the LeetCode
commit that is actually live. Pull before starting local work, or your next push
will be rejected as non-fast-forward.

## CI/CD

Deploys are done by GitHub Actions (`.github/workflows/deploy.yml`), not by
Cloudflare's Git integration — do **not** also connect the repo in the Cloudflare
dashboard or every change would build twice. The workflow checks out submodules,
runs `git submodule update --remote` on the LeetCode submodule so the newest
solutions are published, builds the site, uploads it with `wrangler pages deploy`,
and then commits the bumped submodule pointer back to `main`. That bot push does
not re-trigger the workflow, because GitHub suppresses triggers for pushes made
with the default `GITHUB_TOKEN`. It runs on:

- pushes to `main` of this repo — which now covers every edit to the SWE, System
  Design and Real Interview Questions sections,
- `repository_dispatch` events of type `content-updated`, fired by
  `leetcode-algorithms`' `gitbook.yml` workflow on its content pushes,
- manual runs (`workflow_dispatch`).

### Updating the vendored system-design notes

`content/system-design/` is a vendored copy of our fork of the third-party
[liquidslr/system-design-notes](https://github.com/liquidslr/system-design-notes).
Because it is vendored rather than cloned at build time, syncing the fork no longer
reaches the site on its own — pull upstream changes in by hand:

```bash
gh repo sync software-engineer-learning/system-design-notes --source liquidslr/system-design-notes
git clone --depth 1 https://github.com/software-engineer-learning/system-design-notes.git /tmp/sd
rsync -a --delete --exclude '.git/' --exclude '.github/' /tmp/sd/ content/system-design/
bash scripts/prepare.sh && .venv/bin/mkdocs build --strict
```

Review the diff before committing — vendoring is what keeps third-party edits from
landing on the site unreviewed.

### One-time setup

1. Create the Pages project (Direct Upload):
   ```bash
   npx wrangler pages project create swe-site --production-branch=main
   ```
   (or Cloudflare dashboard → Workers & Pages → Create → Pages → _Direct Upload_.)
2. In **this repo's** GitHub settings → Secrets and variables → Actions, add:
   - `CLOUDFLARE_ACCOUNT_ID` — dashboard → Workers & Pages → right sidebar.
   - `CLOUDFLARE_API_TOKEN` — dashboard → My Profile → API Tokens → Create Token → "Edit Cloudflare Workers"-style custom token with **Account → Cloudflare Pages → Edit** permission.
3. `SITE_DISPATCH_TOKEN` — a classic PAT with the `repo` scope on an account that can
   write to `software-engineer-learning/swe-site`, held as an organization-level
   secret. Only `leetcode-algorithms` still needs it, since it is the one content
   repo left outside this one. Write access is what authorizes `repository_dispatch`.

   > **Don't use a Cloudflare Pages deploy hook here.** This project is Direct Upload, so a hook has no repo to clone and no build command to run — it re-serves the assets already uploaded and returns `success: true` while the content stays stale. Deploy hooks only build on Git-connected Pages projects, and connecting this repo would make every change build twice.
4. After the first deploy: Pages project → **Custom domains → Add** → `swe.springlee.dev`. With the `springlee.dev` zone on Cloudflare, the CNAME and TLS are automatic.

## Adding a section

1. Put the markdown under `content/<section>/` (or add a submodule there).
2. In `scripts/prepare.sh`: add a `<x>_src` variable, an entry in the existence
   check, the `rm -rf`/`mkdir -p` entries, a copy block, a `convert_summary.py` call
   writing `docs/<section>/SUMMARY.md`, and the dir in the final page-count `find`
   and the `normalize_fences.py` call.
3. Add the tab to `docs/SUMMARY.md` and a bullet to `docs/index.md`.
4. Add the section to the table above.
