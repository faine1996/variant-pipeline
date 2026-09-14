# Decisions, Assumptions, and Corrections

A running log. New entries are appended as work proceeds — this is the record the README's
"design decisions" and "AI workflow" sections are written from.

---

## 1. Design decisions

Each entry states the decision, the reasoning, and the alternative that was rejected.

### D1 — Python over C or C++

**Decision:** Python 3.12, standard library only at runtime.
**Reasoning:** `csv` and `json` handling is built in. Writing a correct CSV parser in C — quoting, embedded commas, CRLF terminators — would consume most of the 4–8 hour budget and demonstrate nothing the brief asks for. Row-at-a-time processing keeps memory flat regardless of language.
**Rejected:** C or C++. Better raw throughput, far worse time-to-correct-solution here.

### D2 — One Dockerfile, one image, three commands

**Decision:** A single image; Docker Compose runs it three times with different commands.
**Reasoning:** The three stages share all their dependencies. Three Dockerfiles would triple the build time and the maintenance surface to express one difference — the command line.
**Rejected:** Separate images per stage. Justified only when dependencies genuinely diverge.

### D3 — Explicit stage sequencing in Compose

**Decision:** Chain stages with `depends_on` + `condition: service_completed_successfully`.
**Reasoning:** Compose starts all services concurrently by default. Without explicit ordering, Aggregate runs against an empty directory and reports zero variants — a silent wrong answer, not a crash.
**Rejected:** A shell script calling `docker run` three times. Works, but Compose expresses the dependency declaratively and is what the brief names first.

### D4 — Warnings to `stderr`, not a log file

**Decision:** All warnings and errors go to `stderr`; normal output goes to files.
**Reasoning:** Every program has two output channels — `stdout` for results, `stderr` for problems. Writing to `stderr` lets Docker capture and route logs natively, with no log file to mount, rotate, or clean up. This follows the Twelve-Factor App convention that applications should not manage their own log files.
**Rejected:** An internal `error.log`. Creates state inside the container that disappears when it exits.

### D5 — Atomic writes for every stage output

**Decision:** Write to a temporary file, then rename into place. Applied to all three stages, not only the final summary.
**Reasoning:** Renaming a file within one filesystem either completes fully or does not happen — so no reader ever sees a half-written file, even if the container is killed mid-write. The same helper function serves all three call sites, so consistency costs nothing.
**Rejected:** Atomic writes only for `summary.json`. Leaves the intermediate files exposed to exactly the same failure.

### D6 — Each stage clears its own output directory at start

**Decision:** Clean-slate per stage, rather than relying on overwrite-on-open.
**Reasoning:** Overwriting protects files that get rewritten, not files that do not. Run with five inputs, delete one CSV, run again: the orphaned output from the first run is still on disk, and Aggregate scans directories — so it would count a file that was not part of the second run. Idempotency is a high-weight rubric item and this is the realistic way to break it.
**Rejected:** Overwrite-only. Simpler, and wrong.
**Cost accepted:** No resuming a partially-completed run. See A6.

### D7 — Separate working directory per stage

**Decision:** `data/work/convert/` and `data/work/process/` rather than one shared output folder.
**Reasoning:** Stage 2's files end in `.meta.json`, which any `*.json` glob also matches. Separate directories make the collision structurally impossible instead of depending on a carefully-written pattern that a later edit could break.
**Rejected:** One folder with pattern-based filtering.

### D8 — Stage 1 carries its own counts in its output

**Decision:** Each converted file contains a `counts` block with valid and skipped totals.
**Reasoning:** Only Stage 1 ever sees a malformed row, and its output contains only the good rows. Stage 3 must report total skipped rows across the run. Without counts written at Stage 1, the number has no path forward.
**Rejected:** Recomputing skipped counts later — impossible by construction.

### D9 — Single JSON object per input, assembled by streaming

**Decision:** One `<name>.json` per input containing `source_file`, `variants`, and `counts`, written progressively rather than assembled in memory.
**Reasoning:** Satisfies the brief's "one output file per input" while keeping one row in memory at a time. Counts are written last, once known; JSON object key order is unconstrained.
**Rejected:** JSON Lines (one object per line). Equally streamable and arguably cleaner, but produces a data file plus a separate counts file, which sits awkwardly against "one output file per input". Recorded as the production-scale alternative in Part 3.

### D10 — Validation policy written down before any code

**Decision:** Six explicit rules (see `PLAN.md` §5.1), applied uniformly.
**Reasoning:** The brief's messy sample contains three *different* defect types — empty `index`, non-numeric `POS`, empty `ALT`. Handling only the obvious one passes the sample and fails the intent. A stated rule is testable; ad-hoc checks are not.

### D11 — `REF`/`ALT` accept one or more bases

**Decision:** Valid = 1+ characters, all from `A C G T`.
**Reasoning:** The real data contains legitimate multi-base variants (`GAAGTC→G`, `ATCG→T`, `GCAT→A`). A single-character rule would silently discard valid rows — the worst class of bug, because the pipeline reports success.

### D12 — Natural chromosome ordering in the summary

**Decision:** chr1, chr2 … chr22, chrX, chrY.
**Reasoning:** Alphabetical ordering places chr10 before chr2. Across 24 chromosomes this is immediately visible in the output and reads as carelessness.

### D13 — `total_processing_seconds` = sum of per-file durations

**Decision:** Sum the per-file durations rather than measuring wall-clock for the whole run.
**Reasoning:** The two are identical only while everything runs sequentially, and diverge the moment anything runs concurrently. Stating which one is meant makes the number interpretable.

### D14 — Sleep duration configurable, defaulting to 30 seconds

**Decision:** `SLEEP_SECONDS` environment variable, default 30, set to 0 in tests.
**Reasoning:** The brief specifies 30 seconds and explicitly permits making it configurable so development and testing are faster. A test suite that takes minutes does not get run.

---

## 2. Assumptions

Stated because the brief asks for assumptions to be named.

- **A1 — Batch, not daemon.** The pipeline starts, processes whatever is in `data/input/`, writes the summary, and exits. It does not watch for new files.
- **A2 — Input stability.** No external process modifies or deletes the source CSVs while a run is in progress.
- **A3 — POSIX host.** Volume mounts and atomic renames behave predictably between host and container. Rename atomicity holds within a single filesystem.
- **A4 — Every input CSV has the documented header** (`index,CHROM,POS,REF,ALT`). A file with an unexpected header is a file-level failure, not a row-level one.
- **A5 — No cross-file deduplication.** A variant appearing in two input files is counted twice. The brief asks for counts per chromosome, not distinct variants. (The supplied samples contain no duplicates, so this is invisible in practice — but the choice is real.)
- **A6 — No partial-run resume.** Re-running reprocesses everything from scratch. Acceptable at this scale; the cost of D6.
- **A7 — `chrM` / non-standard contigs.** Not present in the samples. Any non-empty `CHROM` value is accepted and tallied under its own key rather than rejected.
- **A8 — Output directory is writable** and mounted from the host, so results survive container exit.
- **A9 — Timestamps in UTC**, ISO 8601 format, so summaries from different machines are comparable and sort correctly as text.

---

## 3. Open questions

To raise in the interview rather than guess at:

- Should a variant appearing in multiple input files be deduplicated? (A5 assumes no.)
- Is an empty `ALT` genuinely invalid, or does it represent a reference-only call in the source system? (Treated as invalid; the brief's messy sample implies this is intended.)
- Should the pipeline exit non-zero if *every* row in a file is skipped, as a signal that something upstream is broken?

---

## 4. Corrections made to AI-generated output

The first design document for this project was drafted by an AI assistant and reviewed before
implementation. Sixteen issues were found. This table is the evidence for the README's
required "example where you had to correct or override the AI's output".

### Missing requirements (3)

| # | Draft said | Problem |
|---|---|---|
| 1 | Summary contains four fields | The brief requires five — `list of input files processed` was omitted |
| 2 | No test plan | Tests are explicitly required and separately weighted |
| 3 | No README, AI-usage, or Part 2 content | AI workflow is a high-weight rubric row; Part 2 is mandatory |

### Factual errors (5)

| # | Draft claimed | Why it is wrong |
|---|---|---|
| 4 | `sleep()` simulates a compute-bound bottleneck | A sleeping program uses no processor at all. It simulates elapsed time, not CPU load — and the distinction decides how the workload would be scaled in Part 2 |
| 5 | Metrics files are "100% deterministic" | They contain start and end timestamps, which change every run. The property actually wanted is idempotency |
| 6 | Python integer parsing "acts like `strtol()`" | `strtol("12abc")` returns `12` silently — precisely the silent-bad-data failure the draft claimed it avoided. Python's `int()` rejects the whole string |
| 7 | "O(1) memory via generators" and "reads the file to load data back into memory" | Two sections of the same document contradicting each other |
| 8 | Overwrite mode "ensures idempotency" | It protects rewritten files only; orphaned outputs from earlier runs survive and get counted |

### Design defects (4)

| # | Draft design | Failure it produces |
|---|---|---|
| 9 | Aggregate scans one folder for `*.json` and `*.meta.json` | The glob matches both; metrics files get parsed as variant data |
| 10 | Stage 2 reports the skipped-row count | Stage 2 never sees a bad row and its input contains only good rows — the number has no source |
| 11 | Compose runs the image "three times in sequence" | Compose starts services concurrently by default; Aggregate would run on an empty directory |
| 12 | Only `POS` type validation described | The messy sample contains three distinct defect types |

### Found only by inspecting the actual data (4)

| # | Finding | Consequence if missed |
|---|---|---|
| 13 | All sample files use CRLF line endings | Naive line splitting leaves `\r` glued to `ALT`; every downstream comparison silently fails |
| 14 | `REF`/`ALT` are sometimes multi-base (`GAAGTC→G`) | A single-character validation rule silently discards valid rows |
| 15 | None of the five supplied files contain a malformed row | Error handling — the highest-weighted rubric item — would never execute during testing |
| 16 | No container practices specified | The rubric names slim images, layer caching, and non-root users by title |

**Pattern worth stating in the README:** items 1–12 came from checking AI output against the source brief; items 13–16 came from opening the data files. The draft was fluent and internally plausible throughout — including where it was wrong. Fluency was not a signal of correctness in either direction.
