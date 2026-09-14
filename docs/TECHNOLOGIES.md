# Technologies Used

Every tool, library, and AI model involved in this project, with the reason for each choice.
Terms are explained in plain language on first use.

---

## Language and runtime

| Technology | Version | Purpose | Why |
|---|---|---|---|
| **Python** | 3.12 | All pipeline logic | Built-in `csv` and `json` handling removes the parsing work that would dominate the 4–8 hour budget in C or C++. |
| **Python standard library only** | — | Runtime dependencies | No third-party packages are needed at runtime. Fewer dependencies means a smaller image, faster builds, and nothing to audit for security. |

Standard library modules in use:

- `csv` — CSV parsing that correctly handles quoting and line terminators, including the Windows-style CRLF endings present in every sample file
- `json` — serialising output (turning in-memory values into text for a file)
- `pathlib` — filesystem paths as objects rather than strings; avoids manual separator handling
- `datetime` — ISO 8601 timestamps (the international standard format, e.g. `2026-09-14T12:00:00Z`, which sorts correctly as plain text)
- `logging` — warnings routed to `stderr`
- `os` — atomic rename, environment variable reads
- `argparse` — command-line argument parsing for each stage entry point

---

## Testing

| Technology | Purpose | Why |
|---|---|---|
| **pytest** | Test runner | Tests are plain functions with plain `assert` statements — no boilerplate class hierarchy. It discovers and runs them automatically. Development-time dependency only; not present in the runtime image. |

---

## Containerisation

*A **container** packages an application with everything it needs to run, so it behaves identically on any machine. An **image** is the saved template; a container is a running copy of it.*

| Technology | Purpose | Why |
|---|---|---|
| **Docker** | Builds and runs the pipeline image | Required by the brief — a reviewer must be able to run the project with Docker and nothing else. |
| **`python:3.12-slim`** | Base image | "Slim" strips documentation and build tooling from the standard Python image: smaller download, fewer packages that could carry vulnerabilities. |
| **Docker Compose v2** | Sequences the three stages | Runs the same image three times with different commands. Stages are chained with `depends_on` and `condition: service_completed_successfully`, because Compose otherwise starts all services at once and Aggregate would run against an empty directory. |

Container practices applied (each named explicitly in the assessment rubric):

- **Layer caching** — Docker builds in stacked steps and reuses unchanged ones. Dependencies are installed before source code is copied, so editing code does not re-run the install.
- **Non-root user** — a `USER` directive replaces the default all-powerful `root` account, limiting damage if the process misbehaves.
- **`.dockerignore`** — keeps `.git`, caches, and generated output out of the build context, so the image stays small and builds stay fast.

---

## Build and workflow

| Technology | Purpose | Why |
|---|---|---|
| **GNU Make** | `make run`, `make test`, `make clean` | A `Makefile` is a file of named shortcuts. It gives a reviewer one obvious command instead of a paragraph of instructions. |
| **Git** | Version control | The brief states the commit history is read as part of the review and must not be squashed ("squashing" means collapsing many commits into one, which destroys the record of how the work progressed). |
| **GitHub** | Submission | Repository under `github.com/faine1996`. |

---

## AI assistants

The brief requires disclosure of AI tool usage, including an example of correcting AI output.
This section is the factual record; the narrative version lives in the README.

| Tool / model | Interface | Used for | Outcome |
|---|---|---|---|
| *[previous assistant — fill in name and version]* | *[fill in]* | First draft of the pipeline design document | Reviewed against the brief; **16 issues found**, including 3 missing requirements, 5 factual errors, and 4 design defects. Logged in `DECISIONS.md` §4. |
| **Claude Opus 5** | claude.ai (web) | Reviewing that draft against the assessment PDF; inspecting the five sample CSVs directly; producing this revised plan | Produced the correction log and the approved plan. |
| *[coding assistant, if used — e.g. Claude Code]* | *[fill in]* | *[implementation, tests]* | *[fill in as work proceeds]* |

**Honest disclosure:** this document and `PLAN.md` were themselves AI-drafted and then reviewed. Three of the sixteen corrections came from inspecting the actual sample data rather than from reasoning about the brief — which is the practical summary of where these tools are strong and where they are not.

---

## Data characteristics relied upon

Verified by direct inspection of the supplied files, not assumed:

- Input CSVs use **CRLF line endings** — parsed with `open(path, newline='')` so no stray `\r` contaminates the `ALT` field
- **`REF` and `ALT` may be multi-base** (e.g. `GAAGTC → G`); validation accepts one or more characters from `A C G T`
- Sample set: 5 files, 161 valid rows, 24 chromosomes, 0 malformed rows — meaning error-handling paths require the brief's `variants_messy.csv` plus purpose-built test fixtures to exercise at all

---

## Deliberately not used

| Technology | Why not |
|---|---|
| **pandas** | A data-analysis library that loads whole tables into memory. Heavy dependency, large image, and it works against the row-at-a-time design. |
| **A database** | The brief specifies file outputs. A database would add setup a reviewer must perform, violating "no additional setup beyond Docker". |
| **A message queue / task framework** (Celery, Airflow) | Meaningful at cloud scale — which is Part 2's written sketch, not Part 1's implementation. Adding one here would be unnecessary abstraction, which the rubric penalises. |
| **Three separate Dockerfiles** | One image running three commands is simpler to build, cache, and explain. |
| **JSON Lines for Stage 1 output** | Considered and rejected for now: the brief asks for one output file per input, and streaming assembly of a single JSON object achieves the same flat memory usage. Revisit at production scale (Part 3). |
