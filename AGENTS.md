# AGENTS.md — hk-bus-crawling

Guidance for AI coding agents working in this repository. Humans: see `README.md`.

## What this repo is

Two things that share a directory:

1. **The crawler** (`crawling/`) — a pipeline of standalone Python scripts that
   fetch route, stop, fare, frequency and journey-time data for every Hong Kong
   public transport operator, reconcile them against the government GTFS feed,
   and merge everything into a single **`routeFareList.min.json`**. GitHub
   Actions runs it twice daily and publishes to `gh-pages`, served as
   `https://data.hkbus.app/routeFareList.min.json`.
2. **The `hk-bus-eta` PyPI package** (`hk_bus_eta/`) — a small library for
   querying live ETAs, the Python counterpart of the npm package of the same
   name.

**This repo is upstream of the whole family.** If a route is missing, a stop is
in the wrong order, a direction is inverted, or a fare is wrong in
[hkbus.app](https://hkbus.app), the bug is almost certainly here, not in the app.

## Repository family

| Repo | Role |
| --- | --- |
| `hkbus/hk-bus-crawling` | **this repo** — the route/stop/fare database + Python ETA package |
| `hkbus/hk-independent-bus-eta` | the hkbus.app React PWA that consumes `routeFareList.min.json` |
| `hkbus/hk-bus-eta` | the npm ETA package (TypeScript twin of `hk_bus_eta/`) |
| `hkbus/route-waypoints` | route polylines (GeoJSON) for the map |

## The pipeline

Scripts are run **in order** and communicate through JSON files written to the
repository root (all git-ignored). Order matters: later stages read earlier
stages' output.

```text
parseHoliday.py                       holiday.json
ctb.py kmb.py nlb.py lrtfeeder.py     routeList.<co>.json, stopList.<co>.json
lightRail.py mtr.py
parseJourneyTime.py                   routeTime.json
parseGtfs.py                          gtfs.zip → gtfs.json
parseGtfsEn.py                        gtfs-en.json
gmb.py                                routeList.gmb.json, stopList.gmb.json
sunferry.py fortuneferry.py hkkf.py   ferry route/stop lists
matchGtfs.py                          matches operator routes to GTFS routes/
                                      stops → routeGtfs.all.json
cleansing.py                          fixes known bad records
mergeRoutes.py                        routeFareList.mergeRoutes[.min].json
mergeStopList.py                      stop de-duplication → routeFareList[.min].json
routeCompare.py  mtrExits.py          diagnostics, MTR exits
```

Note `gmb.py` and the ferry crawlers run **after** the GTFS stages, not with the
other operators.

The authoritative order is `.github/workflows/fetch-data.yml` — read it rather
than trusting this table if the two ever disagree.

`crawling/crawl_utils.py` holds the shared HTTP helper (`emitRequest`: retries
429/502/504/403 with exponential backoff), the `REQUEST_LIMIT` concurrency knob
(env var, default 10; CI uses 6), and `store_version()` which records each
source's version into `0versions.json`.

`matchGtfs.py` is the hard part: operator stop lists and GTFS stop lists disagree
in naming, ordering and completeness, so it uses a dynamic-programming alignment
(`matchStopsByDp`) with a distance penalty (`DIST_DIFF = 600` m). Changes here
move data for thousands of routes — see "Verifying a change".

## Commands

```sh
pip install -r ./crawling/requirements.txt      # installs the package too (-e .)
python ./crawling/kmb.py                        # run ONE stage
python -m compileall -q .                       # CI syntax gate
flake8 . --select=E9,F63,F7,F82 --show-source   # CI undefined-name gate
```

Run scripts **from the repository root**, not from inside `crawling/` — outputs
are written relative to the working directory, and the scripts rely on their own
directory being importable for `crawl_utils`.

Use an isolated environment (`uv venv`, `conda`, or `python -m venv`); never
install into the system Python.

## CI gates

`.github/workflows/ci.yml` runs on every push and PR:

1. `python -m compileall -q .` — every `.py` file must parse.
2. `pip install requests && python -c "from hk_bus_eta import HKEta; ..."` — the
   published package must still import and expose its methods.
3. `flake8 . --select=E9,F63,F7,F82` — syntax errors and undefined names.

`.github/workflows/format.yml` runs autopep8 and **auto-commits** any
reformatting. `.github/workflows/fetch-data.yml` runs the full pipeline on a
schedule and on push, and deploys to `gh-pages`.

There is no unit-test suite. `crawling/test.py` is a scratch script, not a test
runner.

## House rules

### Formatting: two-space indent, autopep8-aggressive

This repo is **two-space indented Python**. The Format workflow runs:

```sh
autopep8 --exit-code --recursive --in-place --aggressive --aggressive --indent-size=2 .
```

Check your change before pushing — **scoped to the files you touched**:

```sh
autopep8 --aggressive --aggressive --indent-size=2 --diff crawling/yourfile.py
```

Aggressive autopep8 also enforces the 79-character line limit, which at this
indentation leaves very little room for trailing comments.

**Do not run it recursively over the whole repo and commit the result.** A
current autopep8 (checked with 2.3.2 / pycodestyle 2.14.0) disagrees with the
version bundled in `peter-evans/autopep8@v2` and rewrites ~80 lines of untouched,
CI-clean code — wrapping long signatures and, worse, splitting long f-strings at
the brace:

```python
logger.warning(
    f"status_code={
        r.status_code}, wait {retry_timeout} and retry. URL={url}")
```

`master`'s HEAD is often literally the bot's own "Formatted Code!" commit, so
whole-repo churn from your local tool is version drift, not a real violation.
Keep the diff to your own lines and let the workflow settle the rest.

> Note the sibling repo `hkbus/route-waypoints` runs the *same* action **without**
> `--indent-size=2`, so it is four-space indented. Do not carry style between them.

The workflow pushes a "Formatted Code!" commit itself. On a **fork** PR that push
403s (the bot cannot write to your fork), so a red Format job on a fork PR often
means "your code needed reformatting *and* the bot could not do it for you" —
format locally and push again.

### Diffs and comments

- Minimal, single-concern diffs. Unrelated fixes go in separate PRs.
- Comments are rare and terse — one short line where the *why* is not obvious.
  Reasoning belongs in the PR body, not the source.
- Do not reformat untouched code, restructure the pipeline, or add dependencies
  without raising it first. `crawling/requirements.txt` is pinned deliberately.

## Data conventions

- **Route key**: `"<route>+<serviceType>+<orig>+<dest>"`, e.g.
  `"1+1+CHUK YUEN ESTATE+STAR FERRY"` (`mergeRoutes.py`). This is the *raw* DB
  key. hkbus.app normalises it on load —
  `k.replace(/\+/g, "-").replace(/ /g, "-").toUpperCase()` in the app's
  `src/db.ts` — so the same route appears there as
  `1-1-CHUK-YUEN-ESTATE-STAR-FERRY`. Expect that mismatch when comparing this
  repo's output against app state or URLs.
- **Company codes** (`co`): `kmb`, `ctb`, `nlb`, `lrtfeeder`, `gmb`, `lightRail`,
  `mtr`, `sunferry`, `hkkf`, `fortuneferry`. A route may have several.
- **Direction** (`bound`): `"O"` (outbound) or `"I"` (inbound), per company.
  Operators express direction differently — NLB, for example, uses a numeric
  bound that must be translated, and getting that mapping wrong makes both
  directions of a route render identically in the app. When adding an operator,
  check what its API actually means by "direction" and normalise it here.
- **JSON writing is not uniform — match the writer you are editing.**
  `mergeRoutes.py` writes its intermediates with `ensure_ascii=False` and, for
  `.min`, `separators=(',', ':')`. The *final* artifacts are written by
  `mergeStopList.py` with a plain `json.dump(db, f)` (so `.min.json` differs from
  the pretty version only by the absence of `indent=4`, and non-ASCII is escaped).
  Do not "restore" a convention the file you are touching never had.
- Everything the pipeline emits is git-ignored (`*.json`, `gtfs*`, `route-ts`).
  Never commit generated data.

## Verifying a change

A green CI proves the file parses. It does not prove the data is right. For any
change to a crawler or to matching logic, run the affected part of the pipeline
and diff the output:

1. Create an environment and install `crawling/requirements.txt`.
2. Run the stages your change depends on, in pipeline order, from the repo root.
   Most operator scripts are independent; `matchGtfs.py` needs `gtfs.json`
   (from `parseGtfs.py`, ~14 MB download) plus the relevant `routeList.<co>.json`.
3. Compare before/after — count routes per `bound`, diff stop counts, spot-check
   a route you can verify against the operator's own site.
4. Put those numbers in the PR body. "Before `{O: 156}` → after
   `{O: 124, I: 32}`" is what makes a data change reviewable.

Be considerate to the upstream APIs: they are public government endpoints, they
rate-limit, and `REQUEST_LIMIT` exists for a reason. Do not raise it to crawl
faster during development; lower it if anything, and prefer running a single
operator's script over the whole pipeline.

## Pull requests

- Branch from `master`; PRs target `master`.
- CI must be green — but read the Format-on-fork note above before assuming a red
  Format job is your code.
- PR body: what the data looked like before, what it looks like after, and how
  you produced those numbers.

## Licence

GPL-3.0-only.
