# Variant Pipeline

A three-stage, containerised pipeline that validates and aggregates genomic variant
data from CSV into a per-chromosome summary. Built for the IdentifAI Genetics
Software Engineering Intern take-home assessment.

---

## 1. How to build and run

**Requirements: Docker and Docker Compose v2. Nothing else.**

```bash
make run
```

This builds one image and runs it three times — Convert, then Process, then
Aggregate, in that order — writing results to `data/work/` and
`data/output/summary.json` on your host machine.

By default, Process sleeps 30 seconds per input file (see [Design decisions](#2-design-decisions-and-assumptions),
D14). To run the demo faster, override it via the environment — no file edits
needed:

```bash
SLEEP_SECONDS=2 make run
```

**Other commands:**

```bash
make test    # runs the test suite (requires Python 3.12 + pytest, dev-only —
             # not needed to run the pipeline itself)
make clean   # stops and removes containers, clears data/work/ and data/output/
```

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

---

## 3. AI workflow

**Tools used:**

| Tool | Used for |
|---|---|
| Gemini Pro Extended | First draft of the design/planning document |
| Claude Opus 5 (web) | Reviewing that draft against the brief and the actual sample data; producing the corrected, approved plan (`PLAN.md`) |
| Claude Code | Implementation: every source file, test, and Docker artefact, built one file at a time with my review and sign-off at each step |

**A concrete example of correcting AI output:** `PLAN.md`'s own description of
the `variants_messy.csv` fixture stated a result of "6 valid, 5 skipped,"
with each skip attributable to a different one of the six validation rules.
While implementing the test suite, I ran the actual file through the real
Convert stage and got 4 valid, 7 skipped instead — the plan's own numbers
didn't match its own fixture, and rule 3 (empty `CHROM`) was never exercised
by any row at all. This wasn't caught by reviewing the plan as prose; it only
surfaced by running real code against the real file and checking the
arithmetic. Logged as D16 in `DECISIONS.md`, with the fix (one added row) and
the corrected target.

**What AI is best at, for this kind of work:** generating well-specified,
mechanical code once a rule is precisely stated (the six validation
functions, CLI argument wiring, JSON serialisation), and explaining unfamiliar
language mechanisms clearly on request. It's also useful as a second pass —
Claude Opus 5's review of the first draft caught 12 of the 16 logged issues
just from comparing it against the brief.

**What AI is worst at:** verifying its own claims against ground truth without
being explicitly told to check. The first draft asserted things that sounded
authoritative and were simply wrong (e.g. that Python's `int()` behaves like
C's `strtol()` — it doesn't; `strtol("12abc")` silently returns `12`, while
Python's `int()` raises on the whole string). The remaining 4 of the 16 issues
— including the CRLF line endings and the multi-base alleles — were only
found by opening the actual data files, not by reasoning about the brief.
Fluent, confident-sounding text was not a reliable signal of correctness in
either direction, in either drafting pass.

---

## 4. What I would improve with more time

- **Stage 2 loads each converted file whole**, rather than streaming it the
  way Stage 1 does. Fine at 161 rows; would need to switch to streaming or
  JSON Lines before this could handle a realistically large batch.
- **Warnings are unstructured text on `stderr`.** Structured JSON log lines
  would make them queryable by a log aggregator instead of only grep-able.
- **No per-file parallelism.** All three stages process their inputs strictly
  one file at a time; concurrency would be the first thing to add for a much
  larger batch.
- **Validation rules are hard-coded functions**, not a declarative schema.
  Fine for five fixed columns; wouldn't scale cleanly to more.
- **Tests cover row-level and stage-level logic well, but not file-level
  failure modes** — an unreadable file, or one with an unexpected header
  (A4 assumes the header is always correct) — which would matter more against
  real-world, untrusted input.

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
