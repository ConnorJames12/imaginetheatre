# llms-full.txt builder

Generates **`llms-full.txt`** for [imaginetheatre.co.uk](https://www.imaginetheatre.co.uk) —
a single markdown file containing the body content of every page listed in the
`llms.txt` index, so an AI assistant can ingest the whole site in one fetch instead of
crawling pages one by one.

- **Input:** the `llms.txt` index (a list of markdown links to pages).
- **Output:** `llms-full.txt` (all those pages, cleaned and concatenated as markdown).

### Two hosts, on purpose

This project reads from two different places, which is the key thing to understand:

| Thing                | Where it lives                                                        | Why |
|----------------------|-----------------------------------------------------------------------|-----|
| The **index** (`llms.txt`) | GitHub Pages — `https://connorjames12.github.io/imagine-theatre/llms.txt` | Squarespace won't serve a custom `/llms.txt` at the site root (it returns 404), so the index is hosted on Pages instead. |
| The **page content** | The live site — `https://www.imaginetheatre.co.uk/...`                | The actual pages (shows, about, etc.) live on Squarespace. The relative links in the index resolve against this. |

The script reads the index from the first, then fetches each page's content from the
second. These are the `--llms` and `--site` options respectively, and both have sensible
defaults baked in, so usually you can just run it with no arguments.

---

## Contents

- [What it does](#what-it-does)
- [How it works](#how-it-works)
- [Requirements](#requirements)
- [Running it locally](#running-it-locally)
- [Command-line options](#command-line-options)
- [Running it automatically (GitHub Actions)](#running-it-automatically-github-actions)
- [Project files](#project-files)
- [Troubleshooting](#troubleshooting)

---

## What it does

`/llms.txt` is a short index — a list of links to the important pages on the site.
`/llms-full.txt` is the *expanded* version: the actual content of all those pages,
packaged together. This script builds the second from the first.

It produces one markdown file with:

1. A **header** describing the site and when the file was generated.
2. An **index** of every page included.
3. A **section per page** — the cleaned body content of each page, converted to markdown.
4. A **footer** with build metadata (counts of successful and failed fetches) and notes
   for AI assistants reading the file.

---

## How it works

The build runs in five steps (all in `build_llms_full.py`):

1. **Load the index.** Reads `llms.txt` from the `--llms` source. That source can be a full
   URL (the default GitHub Pages one), a local file, or a path relative to `--site`.
2. **Extract the links.** A regular expression pulls every relative path out of the
   markdown links (e.g. `/about/about-us`, `/pantomime2026`). Duplicates are removed while
   keeping the original order, anchor fragments like `#tickets` are trimmed off, and
   external `http(s)://` links are ignored.
3. **Fetch each page.** Downloads each path from the live site (`--site`). If a link points
   at a non-HTML file such as a PDF, the script links to it rather than trying to convert it.
4. **Clean and convert.** For each page it strips out Squarespace boilerplate — scripts,
   styles, headers, footers, navigation, cookie banners — then locates the main content
   block (`<main>`, `<article>`, etc.) and converts that HTML to clean markdown.
5. **Assemble and write.** Joins the header, index, all page sections, and footer into a
   single string and writes it to `llms-full.txt`. If an individual page fails to fetch,
   the script records the error in that section and carries on rather than aborting the
   whole build.

Progress is printed to *stderr* as it runs, so you can watch which pages are being fetched.

---

## Requirements

- **Python 3.9 or newer** (3.12 recommended).
- Three Python packages, listed in `requirements.txt`:
  - `requests` — fetches the pages over HTTP.
  - `beautifulsoup4` — parses and cleans the HTML.
  - `markdownify` — converts the cleaned HTML to markdown.

These install into a **virtual environment** (a `.venv` folder local to the project) so
they don't touch your system Python. The `run.sh` script sets this up for you.

---

## Running it locally

### Option A — one command (recommended)

```bash
cd "path/to/this/folder"
chmod +x run.sh        # only needed the first time
chmod +x run.sh        # only needed the first time
./run.sh
```

`run.sh` creates the `.venv` on first run, installs the dependencies into it, and runs the
build. It's safe to run again and again — later runs reuse the existing environment.
Arguments pass straight through to the script:
`run.sh` creates the `.venv` on first run, installs the dependencies into it, and runs the
build. It's safe to run again and again — later runs reuse the existing environment.
Arguments pass straight through to the script:

```bash
./run.sh --out llms-full.txt
./run.sh --site https://www.imaginetheatre.co.uk
```

When it finishes you'll have `llms-full.txt` in this folder.

### Option B — manual setup

If you'd rather drive it by hand:
When it finishes you'll have `llms-full.txt` in this folder.

### Option B — manual setup

If you'd rather drive it by hand:

```bash
python3 -m venv .venv          # 1. create the virtual environment
source .venv/bin/activate      # 2. activate it (your prompt shows (.venv))
pip install -r requirements.txt # 3. install dependencies into the venv
python3 build_llms_full.py      # 4. run the build
deactivate                     # 5. leave the venv when you're done
python3 -m venv .venv          # 1. create the virtual environment
source .venv/bin/activate      # 2. activate it (your prompt shows (.venv))
pip install -r requirements.txt # 3. install dependencies into the venv
python3 build_llms_full.py      # 4. run the build
deactivate                     # 5. leave the venv when you're done
```

> **The important bit:** activate the venv (or call `.venv/bin/python` directly) *before*
> `pip install` and *before* running the script. Running `pip install` against the system
> Python is what produces the `error: externally-managed-environment` message on modern
> macOS/Python — and the reason the original setup couldn't find its dependencies. The
> virtual environment fixes both.

---
> **The important bit:** activate the venv (or call `.venv/bin/python` directly) *before*
> `pip install` and *before* running the script. Running `pip install` against the system
> Python is what produces the `error: externally-managed-environment` message on modern
> macOS/Python — and the reason the original setup couldn't find its dependencies. The
> virtual environment fixes both.

---

## Command-line options

| Flag      | Default                                                          | Description                          |
|-----------|------------------------------------------------------------------|--------------------------------------|
| `--site`  | `https://www.imaginetheatre.co.uk`                               | Site root that page links resolve against (where the content lives) |
| `--llms`  | `https://connorjames12.github.io/imagine-theatre/llms.txt`       | The index: a full URL, a local file path, or a path relative to `--site` |
| `--out`   | `llms-full.txt`                                                  | Where to write the output file       |

Examples:

```bash
./run.sh                                              # use all defaults
./run.sh --llms llms.txt                              # read the index from a local file
./run.sh --out public/llms-full.txt                   # write somewhere else
```

---

## Running it automatically (GitHub Actions)

The repo includes a scheduled workflow at `.github/workflows/build-llms-full.yml` that
rebuilds the file every night **on GitHub's servers** — your computer doesn't need to be
on. Each night it checks out the repo, installs the dependencies, runs the script, and
commits the refreshed `llms-full.txt` back to the repo (skipping the commit on nights when
nothing changed).

### Turning it on

1. **Push this folder to a GitHub repository** (`git init`, commit, push — or use GitHub
   Desktop).
2. **Allow the Action to commit.** In the repo, go to **Settings → Actions → General →
   Workflow permissions** and select **Read and write permissions**.
3. **Test it.** Open the **Actions** tab, choose *Build llms-full.txt*, and click **Run
   workflow** to trigger a build by hand and confirm it works before relying on the
   schedule.

### Changing the schedule

The timing lives in the `cron:` line of the workflow. It's in **UTC**:
## Running it automatically (GitHub Actions)

The repo includes a scheduled workflow at `.github/workflows/build-llms-full.yml` that
rebuilds the file every night **on GitHub's servers** — your computer doesn't need to be
on. Each night it checks out the repo, installs the dependencies, runs the script, and
commits the refreshed `llms-full.txt` back to the repo (skipping the commit on nights when
nothing changed).

### Turning it on

1. **Push this folder to a GitHub repository** (`git init`, commit, push — or use GitHub
   Desktop).
2. **Allow the Action to commit.** In the repo, go to **Settings → Actions → General →
   Workflow permissions** and select **Read and write permissions**.
3. **Test it.** Open the **Actions** tab, choose *Build llms-full.txt*, and click **Run
   workflow** to trigger a build by hand and confirm it works before relying on the
   schedule.

### Changing the schedule

The timing lives in the `cron:` line of the workflow. It's in **UTC**:

```yaml
on:
  schedule:
    - cron: "15 3 * * *"   # 03:15 UTC daily
```

For example, `0 2 * * *` is 02:00 UTC. Note that GitHub's scheduled runs can be delayed a
few minutes during busy periods — that's normal.

> **Publishing the file:** committing `llms-full.txt` to the repo keeps it version-tracked,
> but for the public `/llms-full.txt` URL to serve the latest copy you'll either point that
> redirect at the raw GitHub file or enable GitHub Pages. Ask if you'd like a Pages step
> added to the workflow.

---

## Project files

| File                                      | Purpose                                              |
|-------------------------------------------|------------------------------------------------------|
| `build_llms_full.py`                      | The generator script.                                |
| `run.sh`                                  | One-command setup + run (creates venv, installs, runs). |
| `requirements.txt`                        | The three Python dependencies.                       |
| `.github/workflows/build-llms-full.yml`   | Nightly GitHub Actions schedule.                     |
| `.gitignore`                              | Keeps `.venv/` and caches out of version control.    |
| `README.md`                               | This file.                                           |

---

## Troubleshooting

**`error: externally-managed-environment` when installing.**
You're installing into the system Python. Use the virtual environment instead — run
`./run.sh`, or follow the manual steps above and activate `.venv` before `pip install`.

**`ModuleNotFoundError: No module named 'requests'` (or `bs4`, `markdownify`).**
The dependencies aren't installed in the environment you're running from. Make sure the
venv is active (or use `.venv/bin/python build_llms_full.py`), and that
`pip install -r requirements.txt` ran without errors.

**`Build failed: 404 Client Error: Not Found for url: .../llms.txt`.**
The script couldn't find the index. By default it reads `llms.txt` from GitHub Pages, *not*
from imaginetheatre.co.uk (Squarespace returns 404 for `/llms.txt`). Make sure the `--llms`
value points at where your index actually lives — the Pages URL, or a local file.

**`Build failed: ... 403 Forbidden` / connection errors.**
The script couldn't reach the site. Check your internet connection and that the `--site`
URL is correct and reachable. A 403 can also mean the host is blocking the request's user
agent; the user agent is set near the top of `build_llms_full.py` if it needs adjusting.

**Some sections say `_Fetch failed: ..._`.**
Individual pages that couldn't be fetched are recorded inline so the rest of the build
still completes. The footer's "Failed fetches" count tells you how many. Re-running often
clears transient failures.

**`./run.sh: Permission denied`.**
Make the script executable once with `chmod +x run.sh`, then run `./run.sh` again.
