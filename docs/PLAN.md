# Variant Pipeline — Approved Implementation Plan

**Project:** Software Engineering Intern — Home Assessment (IdentifAI Genetics)
**Author:** Faine
**Status:** Approved, pre-implementation (rev. 2 — messy fixture expanded to cover all six validation rules)
**Time budget:** 4–8 hours total

---

## 1. Scope

Three deliverables, defined by the brief:

| Part | Requirement | Status in this plan |
|---|---|---|
| Part 1 | Three-stage local pipeline, containerised, tested | Full plan below |
| Part 2 | AWS scale sketch, maximum half a page | Outline in §9 |
| Part 3 | Optional self-review of the Convert stage | Outline in §10, time permitting |

**Rubric weighting** (from the brief, drives prioritisation):

- **High:** error handling, idempotency, AI workflow documentation
- **Medium:** code quality, testing, communication (README), containers
- **Low:** Part 2 sketch, git history

---

## 2. Terminology

Plain-language definitions of every technical term used in this document.

| Term | Meaning |
|---|---|
| **Pipeline** | A sequence of programs where each one's output is the next one's input. |
| **Stage** | One program in that sequence. Here: Convert, Process, Aggregate. |
| **Container** | An application packaged with everything it needs to run, so it behaves identically on any machine. |
| **Image** | The saved template a container is created from. One image, many running containers. |
| **Layer caching** | Docker builds images in stacked steps ("layers") and reuses unchanged ones. Ordering build steps so slow steps are cached speeds up rebuilds. |
| **Non-root user** | Containers run as the all-powerful `root` account by default. Running as an ordinary user limits damage if the process misbehaves. |
| **Streaming** | Processing one item at a time and discarding it, rather than loading everything into memory first. Reading a book page by page rather than photographing every page first. |
| **Serialise** | Convert an in-memory value into text that can be written to a file. |
| **Atomic write** | Write to a temporary file, then rename it into place. Renaming within one filesystem either fully happens or does not happen at all, so no reader ever sees a half-written file. |
| **Idempotent** | Running an operation twice produces the same result as running it once. A switch labelled "ON" is idempotent; one labelled "TOGGLE" is not. |
| **Environment variable** | A named setting handed to a program by whatever launches it — a knob turned from outside, without editing code. |
| **stdout / stderr** | Two output channels every program has. `stdout` carries normal results; `stderr` carries warnings and errors. Keeping them separate lets tooling route each independently. |
| **CRLF** | Windows line endings — two characters (`\r\n`) marking the end of a line, versus Unix's one (`\n`). |
| **Glob** | A wildcard filename pattern such as `*.json`. |
| **Fixture** | A small, deliberately-constructed input file that exists only so a test has something to run against. |
| **Regression test** | A test that catches a future change silently breaking something that already worked. |
| **Compute-bound / I/O-bound** | Compute-bound = speed limited by the processor. I/O-bound = limited by waiting on disk, network, or a timer. |
| **PEP 8** | The official Python style guide — naming, spacing, line length conventions. |
| **Type hints** | Optional annotations declaring what type a function takes and returns. Documentation the tooling can check. |

---

## 3. Input data — verified facts

Sample set inspected before planning. **These are measured, not assumed.**

| File | Data rows | Malformed rows |
|---|---|---|
| variants_1.csv | 30 | 0 |
| variants_2.csv | 25 | 0 |
| variants_3.csv | 25 | 0 |
| variants_4.csv | 28 | 0 |
| variants_5.csv | 53 | 0 |
| **Total** | **161** | **0** |

- 24 distinct chromosomes: chr1–chr22, chrX, chrY
- No duplicate `index` values within or across files
- **All five files use CRLF line endings.** Naive line splitting leaves a trailing `\r` glued to the `ALT` field.
- **`REF` and `ALT` are not always single characters.** Real multi-base values present: `GAAGTC→G` (variants_1), `ATCG→T` (variants_3), `GCAT→A` (variants_5).
- **None of the five contain a malformed row.** Error-handling code paths are therefore not exercised by them; the brief's `variants_messy.csv` and purpose-built test fixtures are required.

Expected combined chromosome tally (regression test target):

```
chr1:12  chr2:14  chr3:8   chr4:7   chr5:9   chr6:7   chr7:8   chr8:6
chr9:6   chr10:6  chr11:7  chr12:7  chr13:5  chr14:5  chr15:5  chr16:6
chr17:5  chr18:6  chr19:5  chr20:5  chr21:6  chr22:5  chrX:6   chrY:5
                                                          total = 161
```

**`variants_clean.csv`** (unmodified from the brief) → 6 valid, 0 skipped.

**`variants_messy.csv`** — extended beyond the brief's original three rows so that every one of the six validation rules in §5.1 is exercised at least once, including a row broken in two ways simultaneously:

| Row | Defect | Rule exercised |
|---|---|---|
| `,chr1,99281744,C,T` | empty `index` | non-empty index |
| `chr2:145827_G/A,chr2,not_a_number,G,A` | non-numeric `POS` | POS parses as integer |
| `chr4:60218733_A/G,chr4,60218733,A,` | empty `ALT` | non-empty, ACGT-only ALT |
| `chr3:71234567_N/T,chr3,71234567,N,T` | `N` in `REF` | ACGT-only REF |
| `chr5:80000001_C/G,chr5,80000001,C,G,extra_field` | 6 fields, not 5 | exact field count |
| `,chr6,-5,A,T` | empty index **and** negative POS | two rules at once |
| `chr7:90000002_G/1,chr7,90000002,G,1` | digit in `ALT` | ACGT-only ALT |

Result: **6 valid, 5 skipped, 11 data rows total.** The file deliberately does not end on a defective row, since that boundary is a common source of off-by-one bugs in hand-rolled parsers.

---

## 4. Data flow

```
data/input/*.csv
        │  Stage 1: Convert
        ▼
data/work/convert/<name>.json          one per input; variants + counts
        │  Stage 2: Process
        ▼
data/work/process/<name>.meta.json     one per input; timings + counts
        │  Stage 3: Aggregate
        ▼
data/output/summary.json               one file, whole run
```

Separate directories per stage are deliberate: Stage 2's files end in `.meta.json`, which any `*.json` glob would also match. Separate directories make the collision structurally impossible rather than relying on a careful pattern.

---

## 5. Stage specifications

### Stage 1 — Convert

**Input:** every `*.csv` in `data/input/`
**Output:** one `data/work/convert/<name>.json` per input

**Behaviour**

1. Clear `data/work/convert/` at start.
2. For each CSV: open with `newline=''` so the `csv` module handles CRLF terminators correctly; read the header; then read rows one at a time.
3. Strip surrounding whitespace from every field.
4. Validate (§5.1). Valid rows are serialised immediately; invalid rows are skipped and a warning is written to `stderr` naming file, line number, and reason.
5. Write output atomically.

**Output shape** — one file per input, streamed so only one row is held in memory at a time. Counts are written last, once known; JSON object key order is unconstrained.

```json
{
  "source_file": "variants_1.csv",
  "converted_at": "2026-09-14T12:00:00Z",
  "variants": [
    {"index": "chr1:17282953_G/T", "chrom": "chr1", "pos": 17282953, "ref": "G", "alt": "T"}
  ],
  "counts": {"valid": 30, "skipped": 0}
}
```

The `counts` block exists because only Stage 1 ever sees a bad row, and Stage 3 must report total skipped rows. Without it the number has no path forward.

#### 5.1 Validation policy

A row is **valid** only if all hold:

| Rule | Rejects |
|---|---|
| Exactly 5 fields | Truncated or extra-comma rows |
| `index` non-empty after stripping | Missing label |
| `CHROM` non-empty after stripping | Missing chromosome |
| `POS` parses as a positive integer | `not_a_number`, negative, empty |
| `REF` is 1+ characters, all from `A C G T` | Empty, `N`, stray `\r` |
| `ALT` is 1+ characters, all from `A C G T` | Empty, stray `\r` |

"1 or more characters" is load-bearing: a single-character rule would silently discard the three legitimate multi-base variants in the real data.

Every rejection logs one warning line and processing continues. The pipeline never exits non-zero because of a bad row.

### Stage 2 — Process

**Input:** every `data/work/convert/*.json`
**Output:** one `data/work/process/<name>.meta.json` per input

**Behaviour**

1. Clear `data/work/process/` at start.
2. For each converted file: record start time, sleep `SLEEP_SECONDS` (default **30**, overridable), record end time.
3. Write metrics atomically.

```json
{
  "source_file": "variants_1.csv",
  "started_at": "2026-09-14T12:00:00Z",
  "finished_at": "2026-09-14T12:00:30Z",
  "duration_seconds": 30.0,
  "row_count": 30,
  "skipped_count": 0
}
```

**Accuracy note:** the sleep simulates *elapsed time*, not processor load — a sleeping program uses no CPU. This is I/O-bound-shaped work, not compute-bound work, and the distinction drives the Part 2 scaling argument: waiting work packs many-per-machine, CPU-hungry work needs a core each.

**Known limit, documented rather than hidden:** this stage loads its input file whole rather than streaming it. Irrelevant at 161 rows; material at ten million. Called out in the README and in the Part 3 self-review.

### Stage 3 — Aggregate

**Input:** `data/work/convert/*.json` (chromosome tallies) and `data/work/process/*.meta.json` (timings, counts)
**Output:** `data/output/summary.json`

```json
{
  "generated_at": "2026-09-14T12:01:00Z",
  "input_files_processed": ["variants_1.csv", "variants_2.csv"],
  "total_variants": 161,
  "total_skipped_rows": 0,
  "total_processing_seconds": 150.0,
  "variants_per_chromosome": {"chr1": 12, "chr2": 14, "chrX": 6, "chrY": 5}
}
```

All five fields required by the brief are present, including `input_files_processed`.

**Chromosome ordering:** natural — chr1, chr2 … chr22, chrX, chrY. Plain alphabetical sorting places chr10 before chr2, which is visible and looks careless across 24 chromosomes.

**`total_processing_seconds`** is the sum of per-file durations, not wall-clock of the whole run. The two diverge the moment anything runs concurrently.

---

## 6. Idempotency strategy

Re-running the pipeline on unchanged input must produce a byte-identical summary (timestamps excepted), and re-running after an input is removed must not count the removed file.

**Mechanism:** each stage clears its own output directory at start, then writes every output atomically.

Overwrite-on-open alone is insufficient: it protects files that get rewritten, not files that do not. With five inputs, then one CSV deleted and a second run, the orphaned output from run 1 remains on disk — and Stage 3 scans directories, so it would count a file that was not part of run 2.

**Trade-off accepted:** no resuming a partially-completed run. Recorded as an assumption.

---

## 7. Containers and orchestration

One `Dockerfile`, one image, run three times with different commands. The brief containerises Convert at minimum and treats all three as a plus.

**Required practices (named explicitly in the rubric):**

- `python:3.12-slim` base — smaller image, smaller attack surface
- Dependency install before source copy, so editing code does not re-run the install (layer caching)
- `USER` directive — run as a non-root user
- `.dockerignore` excluding `.git`, `__pycache__`, `.pytest_cache`, `data/work`, `data/output`

**Sequencing:** Compose starts services concurrently by default; without explicit ordering, Aggregate would run against an empty directory. Stages are chained with `depends_on` + `condition: service_completed_successfully`.

**Entry point:** a `Makefile` providing `make run`, `make test`, `make clean`. A reviewer should need Docker and nothing else.

---

## 8. Test plan

Runner: **pytest**. Every test runs with `SLEEP_SECONDS=0`.

| Test file | Covers |
|---|---|
| `test_validation.py` | Each of the six validation rules, pass and fail; multi-base `REF`/`ALT` accepted; CRLF input yields no trailing `\r` |
| `test_convert.py` | One valid row → one output object; malformed rows skipped with a warning; counts block correct; output is valid JSON |
| `test_process.py` | Metrics file contains all six fields; `SLEEP_SECONDS` honoured; counts carried through from Stage 1 |
| `test_aggregate.py` | Tallies and totals from fixed inputs; natural chromosome ordering; `input_files_processed` populated |
| `test_idempotency.py` | Full run twice → identical summaries; run, remove an input, run again → removed file absent from summary |
| `test_sample_data.py` | Regression: all five numbered CSVs → 161 variants, 0 skipped, 24 chromosomes, tally matches §3; `variants_clean.csv` → 6/0; `variants_messy.csv` → 6 valid/5 skipped, one skip per rule in §5.1 |

Fixtures under `tests/fixtures/`: `valid_minimal.csv`, `malformed_rows.csv` (one row per defect type, including the double-defect and field-count cases), `crlf_endings.csv`, `multibase_alleles.csv`. These are separate from `data/input/variants_messy.csv` — the fixtures are minimal and used for unit tests of `validation.py` in isolation; `variants_messy.csv` is the full end-to-end input used by the pipeline itself and by the sample-data regression test.

---

## 9. Part 2 — AWS scale sketch (maximum half a page)

Three bullets and a short assumptions line. Depth belongs in the interview, not the document.

1. **Services and why** — object storage for input and output; a container runner for the three stages; an orchestrator to sequence them and fan out per file.
2. **One failure at scale and its mitigation** — a single unparseable or oversized file stalling the batch; mitigated by per-file isolation so one failure cannot block others, plus a dead-letter destination for inspection.
3. **One health metric** — end-to-end completion time per batch, or count of failed per-file tasks; either detects silent stalls that a success/failure flag alone would miss.

---

## 10. Part 3 — Self-review of Convert (optional)

Only if time remains within the 8-hour budget. Short written list:

- Stage 2 loads whole files; switch to streaming or JSON Lines at production scale
- Warnings to `stderr` are unstructured; structured JSON logs would be queryable
- No backpressure or parallelism; per-file concurrency would be the first change
- Validation rules are hard-coded; a declarative schema would scale to more columns
- Tests cover logic but not malformed-file-level failures (unreadable file, wrong header)

---

## 11. README requirements

Four sections mandated by the brief:

1. **How to build and run** — Docker only, one command
2. **Design decisions and assumptions** — summarised from `DECISIONS.md`
3. **AI workflow** — which tools, for what; a concrete example of correcting AI output; what AI is best and worst at for this work
4. **What I would improve with more time**

Section 3 is high-weight and is the one most candidates omit. The correction log in `DECISIONS.md` §4 is the source material.

---

## 12. Milestones

| # | Milestone | Rough effort |
|---|---|---|
| 1 | Repo skeleton, `.gitignore`, README stub, first commit | 20 min |
| 2 | `common/` — validation, atomic write, logging | 45 min |
| 3 | Stage 1 + its tests | 1 h |
| 4 | Stage 2 + its tests | 45 min |
| 5 | Stage 3 + its tests | 1 h |
| 6 | Dockerfile, Compose, Makefile, end-to-end run | 1 h |
| 7 | Idempotency + sample-data regression tests | 45 min |
| 8 | README, Part 2, docs finalisation | 1 h |
| 9 | Part 3 if time remains | 20 min |

Stop at 6 hours if reached, and write down what would come next — the brief explicitly invites this and values honest reflection over completeness.