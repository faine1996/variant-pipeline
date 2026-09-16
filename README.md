# Variant Pipeline

A three-stage, containerised pipeline that validates and aggregates genomic variant
data from CSV into a per-chromosome summary. Built for the IdentifAI Genetics
Software Engineering Intern take-home assessment.

---

## 1. How to build and run

**Requirements: Git, Docker, and Docker Compose v2. Nothing else.**

```bash
git clone <this-repository-url>
cd variant-pipeline
make run
```

This builds one image and runs it three times — Convert, then Process, then
Aggregate, in that order — writing results to `data/work/` and
`data/output/summary.json` on your host machine.

**No `make` available?** (common on a default Windows PowerShell/CMD prompt —
`make` isn't installed there by default). Run the underlying command directly
instead; it does exactly the same thing:

```bash
docker compose up --build
```

By default, Process sleeps 30 seconds per input file (see [Design decisions](#2-design-decisions-and-assumptions),
D14). To run the demo faster, override it via the environment — no file edits
needed:

```bash
SLEEP_SECONDS=2 make run
# or, without make:
SLEEP_SECONDS=2 docker compose up --build
```

**Other commands, with their no-`make` equivalents:**

| `make` target | What it does | Without `make` |
|---|---|---|
| `make test` | Runs the test suite (requires Python 3.12 + `pip install -r requirements-dev.txt`; dev-only, not needed to run the pipeline) | `pytest` |
| `make clean` | Stops/removes containers, clears `data/work/` and `data/output/` | `docker compose down --remove-orphans` (then manually clear `data/work/` and `data/output/` if desired) |

**Capturing full logs beyond the container's lifetime:** Docker discards a
container's logs once it's removed (e.g. after `make clean`). To keep a
permanent copy of a run's full output — warnings included — redirect it to a
file while still seeing it live in your terminal:

```bash
docker compose up --build 2>&1 | tee run.log
```

---

## 2. Design decisions and assumptions

Every non-obvious decision made during implementation — and every assumption
the brief left open — is logged with its reasoning and the alternative that
was rejected in [`docs/DECISIONS.md`](docs/DECISIONS.md) (19 decisions, 10
assumptions). The highlights most relevant to how this pipeline behaves:

- **Idempotency (D5, D6):** every stage clears its own output directory at
  start and writes atomically (temp file + rename), so a re-run — even after
  an input file is deleted — never mixes stale output with fresh output.
- **Validation (D10, D11):** exactly six independently-testable rules, with
  `REF`/`ALT` explicitly accepting multi-base values — the real sample data
  contains variants like `GAAGTC → G`, and a single-character rule would
  silently discard them.
- **CRLF handling:** all sample CSVs use Windows line endings; every file is
  opened with `newline=''` and every field is stripped, so no stray `\r`
  reaches the `ALT` column.
- **Separate work directories per stage (D7):** Convert's and Process's
  outputs never share a folder, so a `*.json` glob can never accidentally
  match both `variants_1.json` and `variants_1.meta.json`.
- **Natural chromosome ordering (D12):** `chr1 … chr22, chrX, chrY` — plain
  alphabetical sorting would put `chr10` before `chr2`.

Full rationale for all of the above, plus assumptions like "no cross-file
deduplication" and "batch, not daemon," is in `DECISIONS.md`.
- **Container best practices (Dockerfile):** single `python:3.12-slim` image,
  layer ordering that keeps dependency installs cached when only source changes,
  and a dedicated non-root `appuser` — so the container never runs as root even
  if an input file triggers unexpected behaviour.
---

## 3. AI workflow

**Tools used:**

| Tool | Used for |
|---|---|
| Gemini Pro Extended | First draft of the design/planning document |
| Claude Opus 5 (web) | Reviewing that draft against the brief and actual sample data; producing the corrected, approved plan (`PLAN.md`) |
| Claude Code | Implementation: every source file, test, and Docker artefact, built one file at a time with my review and sign-off at each step |

**A concrete example of correcting AI output:** `PLAN.md` stated the
`variants_messy.csv` fixture would produce "6 valid, 5 skipped," with each
skip exercising a different validation rule. Running the real Convert stage
against the real file gave 4 valid, 7 skipped — the plan's own numbers didn't
match its own fixture, and rule 3 (empty `CHROM`) was never exercised by any
row. This only surfaced by running code against the actual data and checking
the arithmetic, not by reviewing prose. Logged as D16 in `DECISIONS.md`.

**What AI is best at:** generating well-specified, mechanical code once a rule
is precisely stated (the six validation functions, CLI argument wiring, JSON
serialisation), and explaining unfamiliar language mechanisms clearly on
request. Also useful as a second pass — Claude Opus 5's review caught 12 of
the 16 logged issues just from comparing the draft against the brief.

**What AI is worst at:** verifying its own claims against ground truth without
being explicitly told to check. The first draft asserted things that sounded
authoritative and were simply wrong (e.g. that Python's `int()` behaves like
C's `strtol()` — it doesn't; `strtol("12abc")` silently returns `12`, while
Python's `int()` raises on the whole string). The remaining 4 of the 16
issues — including CRLF line endings and multi-base alleles — were only found
by opening the actual data files. Fluent, confident-sounding text was not a
reliable signal of correctness in either drafting pass.
---

## 4. Part 3 — Convert stage code review

If the Convert stage were handling millions of rows daily in production, these
are the changes I would prioritise:

- **Memory:** Convert already streams input row-by-row, so peak memory stays
  low regardless of file size. Stage 2, however, loads each converted JSON
  file whole — that would be the first bottleneck to fix (streaming or JSON
  Lines).
- **Performance:** validation is six independent function calls per row. At
  millions of rows the call overhead adds up; a single-pass validator that
  short-circuits on the first failure would reduce work per invalid row.
  Per-file parallelism across input files would also help throughput.
- **Logging:** warnings are currently unstructured text on `stderr`. Structured
  JSON log lines (with file name, row number, rule violated) would make them
  queryable by a log aggregator instead of only grep-able.
- **Testing:** tests cover row-level and stage-level logic well, but not
  file-level failure modes — an unreadable file, a file with an unexpected
  header, or a zero-byte file — which matter more against real-world,
  untrusted input.
- **Validation rules** are hard-coded functions, not a declarative schema.
  Fine for five fixed columns; wouldn't scale cleanly to more without
  becoming difficult to audit.

---

## 5. AWS scale sketch (Part 2)

*(Three bullets, per the brief's half-page limit — depth belongs in the
interview, not here.)*

1. **Services:** S3 for input/output storage, a container runner (ECS
   Fargate or similar) for the three stages, and an orchestrator (Step
   Functions, or an equivalent DAG tool) to sequence them and fan out per
   input file.
2. **One failure mode and its mitigation:** a single unparseable or
   oversized file stalling the whole batch — mitigated by per-file
   isolation (one failed file can't block the others) plus a dead-letter
   destination for inspection.
3. **One health metric:** end-to-end completion time per batch, or count of
   failed per-file tasks — either detects a silent stall that a simple
   success/failure flag alone would miss.

**Assumption:** input files arrive independently and can be processed in any
order or in parallel — nothing in this pipeline's logic depends on
cross-file ordering.
