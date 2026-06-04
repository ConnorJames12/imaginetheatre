# build_llms_full.py

Generates `llms-full.txt` for imaginetheatre.co.uk — fetches `/llms.txt`, follows every
linked page, strips Squarespace boilerplate, converts each page body to markdown, and
concatenates everything into one file an AI can ingest in a single fetch.

## Why you were stuck

Two separate problems, both about the environment rather than the code:

1. **`pip install` failed.** On recent macOS / Python (3.11+), installing into the system
   Python is blocked with an `error: externally-managed-environment` message (PEP 668).
   The fix is to install into a project-local virtual environment instead of the system one.
2. **No venv.** Without a venv there was nowhere isolated for the dependencies to live, so
   the imports (`requests`, `bs4`, `markdownify`) couldn't be found when you ran the script.

`run.sh` handles both: it creates a `.venv`, installs the dependencies into it, and runs the
script — all in one command.

## Quick start (recommended)

```bash
cd "path/to/this/folder"
chmod +x run.sh        # only needed once
./run.sh
```

That produces `llms-full.txt` in this folder. Any extra arguments pass straight through:

```bash
./run.sh --out llms-full.txt
./run.sh --site https://www.imaginetheatre.co.uk
```

## Manual setup (if you prefer to do it by hand)

```bash
python3 -m venv .venv          # create the virtual environment
source .venv/bin/activate      # activate it (prompt shows (.venv))
pip install -r requirements.txt
python3 build_llms_full.py
deactivate                     # when you're done
```

The key point: **activate the venv (or call `.venv/bin/python` directly) before
`pip install` or `python3 build_llms_full.py`.** Running them against the system Python is
what caused the original errors.

## Command-line options

| Flag      | Default                              | Description                     |
|-----------|--------------------------------------|---------------------------------|
| `--site`  | `https://www.imaginetheatre.co.uk`   | Site root URL                   |
| `--llms`  | `/llms.txt`                          | Path to the llms.txt index      |
| `--out`   | `llms-full.txt`                      | Output file path                |

## Running it automatically (nightly)

Once the venv exists, point cron (or a launchd job / GitHub Action) at `run.sh`:

```cron
# 03:15 every day
15 3 * * * /full/path/to/run.sh >> /full/path/to/build.log 2>&1
```

## Notes

- `.venv/` is a local build artifact — don't commit it. A `.gitignore` is included.
- A bug was fixed in the link extractor: links containing an anchor fragment
  (e.g. `/shows/cinderella#tickets`) and the bare home path `/` were previously dropped.
  They're now captured correctly.
