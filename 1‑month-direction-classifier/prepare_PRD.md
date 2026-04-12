# PRD: Incremental stock price data updater for EODHD

## 1. Product overview

### 1.1 Document title and version

- PRD: Incremental stock price data updater for EODHD
- Version: 1.1

### 1.2 Product summary

This project defines a Python solution implemented as a Jupyter notebook to keep local end-of-day stock price datasets current for a list of ticker symbols. Tickers are loaded from a CSV file in the `data` folder and include exchange suffixes (for example, `AMZN.US`).

The notebook lives in the `prepare` folder and updates one CSV file per symbol inside a subfolder that matches the selected ticker-list CSV filename. For example, if the input is `data/S&P_500.csv`, symbol files are stored in `data/S&P_500/{SYMBOL}.csv` (for example, `data/S&P_500/AMZN.US.csv`). The workflow runs in two phases: first, it detects newly added ticker symbols and fetches each new symbol's full available history one by one from EODHD into newly created archive files; second, it computes the latest date in every symbol file, takes the oldest of those latest dates as a shared from date, and fetches updates to today in batches of 100 symbols.

The process is designed for manual execution (on demand), robust continuation on partial failures, and efficient re-runs that focus on incomplete or stale symbol datasets.

## 2. Goals

### 2.1 Business goals

- Maintain a reliable local market data store with minimal manual effort.
- Reduce API usage by performing incremental updates instead of full reloads.
- Support repeatable manual runs for research workflows in notebooks.

### 2.2 User goals

- Provide a ticker list once via CSV and update all symbol files in one run.
- Automatically detect missing date ranges from each symbol’s newest local record to today.
- Recover from failed symbols by re-running and updating only symbols still incomplete.

### 2.3 Non-goals

- Building a production scheduler or orchestration platform.
- Implementing intraday (minute-level) data ingestion.
- Building a UI beyond notebook cells and summary tables.

## 3. User personas

### 3.1 Key user types

- Quant researcher
- Retail algorithmic trader
- Data engineer supporting research notebooks

### 3.2 Basic persona details

- **Quant researcher**: Runs notebook-based workflows and needs fresh historical OHLCV data.
- **Retail algorithmic trader**: Maintains personal datasets and wants simple reruns after API/network failures.
- **Data engineer**: Ensures consistent file structure and data quality for downstream models.

### 3.3 Role-based access

- **Local notebook operator**: Can execute data update notebook in `prepare` and write files under `data/{LIST_NAME}`.
- **API key holder**: Provides and manages EODHD API key for notebook execution.

## 4. Functional requirements

- **Ticker input ingestion** (Priority: High)

	- Load ticker symbols from a user-provided CSV file.
	- Support ticker-list CSV files located in `data` (for example, `data/S&P_500.csv`, `data/STOXX_600.csv`).
	- Expect symbols in exchange-suffixed format (for example, `AMZN.US`).
	- Validate symbols are non-empty and normalize whitespace.

- **Per-symbol file management** (Priority: High)

	- Derive list scope folder name from the selected CSV filename (without extension).
	- Store each symbol’s history in `data/{LIST_NAME}/{SYMBOL}.csv`.
	- Create missing symbol CSV files automatically.
	- Create missing list scope folders automatically.
	- Read existing files to determine latest local date.

- **New symbol discovery and bootstrap** (Priority: High)

	- Detect ticker symbols present in the selected ticker-list CSV that do not yet have a corresponding symbol CSV file in the scope folder.
	- For each new symbol, fetch full available historical data from EODHD and store it in a newly created archive file.
	- Process multiple newly added symbols one by one before any incremental batch update starts.

- **Incremental period detection** (Priority: High)

	- Run this phase only after all newly added symbols are bootstrapped with full history.
	- Determine each symbol file's latest available date.
	- Set a shared batch fetch start date as the oldest value among all symbol latest dates.
	- Use this shared oldest-latest date as from for the incremental batch period.
	- Use current date as fetch end date.
	- Rely on EODHD response to naturally exclude non-trading days (weekends/holidays).

- **Batch API retrieval** (Priority: High)

	- Apply batching to the incremental phase using groups of up to 100 symbols per request.
	- Execute HTTP requests in batches of up to 100 symbols per request where endpoint supports batching.
	- Respect API key sourced from local notebook configuration.
	- Handle request timeout, non-200 responses, malformed payloads, and per-symbol data gaps.

- **Merge and quality controls** (Priority: High)

	- Persist columns: `Date`, `Open`, `High`, `Low`, `Close`, `Adjusted close`, `Volume`.
	- Append new data into symbol CSV files.
	- De-duplicate by `Date` and keep one authoritative row per date (latest fetched row wins).
	- Overwrite duplicate-date rows with newest fetched values to preserve data quality.
	- Sort records ascending by `Date` before save.

- **Failure tolerance and resumability** (Priority: High)

	- Continue processing remaining batches/symbols when a subset fails.
	- Emit run summary showing updated symbols, skipped up-to-date symbols, and failed symbols.
	- Ensure rerun updates only still-outdated symbols, enabling recovery without reprocessing complete files.

- **Notebook-first implementation** (Priority: High)

	- Deliver all logic in a Jupyter notebook.
	- Include clear execution cells for configuration, ingestion, update run, and summary output.

## 5. User experience

### 5.1 Entry points and first-time user flow

- Open `prepare/prepare.ipynb` in Jupyter.
- Set path to ticker list CSV in `data`.
- Verify API key is available to the notebook.
- Run notebook cells top-to-bottom.
- Review summary table and any failure list.

### 5.2 Core experience

- **Load universe**: User reads ticker CSV and validates symbol count.

	- Prevents silent failures due to malformed input.

- **Bootstrap new symbols**: Notebook detects newly added symbols and fetches full history one by one.

	- Ensures complete archive creation for newly introduced tickers.

- **Detect update windows**: Notebook inspects all symbol CSV files and computes a shared incremental fetch range.

	- Ensures all symbols are aligned to a single incremental period start.

- **Fetch in 100-symbol batches**: Notebook executes batched requests and parses payloads.

	- Improves throughput and API efficiency.

- **Write cleaned outputs**: Notebook merges, deduplicates, sorts, and saves each symbol file.

	- Preserves consistent datasets for downstream modeling.

- **Review results**: User sees success/skip/failure counts and symbol-level details.

	- Supports quick rerun decisions for unresolved symbols.

### 5.3 Advanced features and edge cases

- Skip symbols whose CSV already includes data through current date (or latest trading date available).
- Handle empty files and files with missing required columns.
- Tolerate symbol delistings or permanently unavailable API data with explicit status in report.
- Support manual run cadences (daily, weekly, monthly) with no code changes.

### 5.4 UI/UX highlights

- Notebook progress output by batch number and symbol count.
- Final pandas summary DataFrame with statuses and row deltas.
- Optional CSV log export of failed symbols for rerun input.

## 6. Narrative

The user opens a single notebook in `prepare`, points to a ticker CSV in `data`, and runs the workflow. The notebook derives the matching output scope folder from the selected file (for example, `S&P_500.csv` -> `data/S&P_500/`) and checks each symbol file there. If any ticker symbol is newly added and has no archive file yet, the notebook fetches full available history for that symbol and saves it first, one by one. After all new symbols are initialized, the notebook finds the latest available date in every symbol file, chooses the oldest of those latest dates as the shared from date, and fetches the incremental period from that date to today in batches of 100 symbols. New data is merged without duplicates, duplicate dates are overwritten with newest values, and each symbol CSV remains clean and sorted. If any symbols fail due to transient API issues, the run still completes and flags only those failures so a second run can efficiently catch up.

## 7. Success metrics

### 7.1 User-centric metrics

- At least 95% of symbols updated successfully per run under normal API availability.
- User can complete a manual update run with one notebook execution sequence.
- Failed symbol reruns complete without requiring full-universe refresh.

### 7.2 Business metrics

- Reduced API call volume versus full-history reload baseline.
- Increased data freshness coverage across tracked symbols.

### 7.3 Technical metrics

- Zero duplicate `Date` rows per symbol file after each run, with duplicate dates overwritten by newest fetched values.
- 100% of output files conform to required schema and date sort order.
- Batch failure does not terminate entire run.

## 8. Technical considerations

### 8.1 Integration points

- Notebook location: `prepare/prepare.ipynb`.
- Input universe: ticker-list CSV maintained by user in `data` (for example, `data/S&P_500.csv`).
- Output store: `data/{LIST_NAME}/{SYMBOL}.csv` where `LIST_NAME` is derived from selected input filename.
- API key source: notebook runtime configuration (for example, imported constant or environment value).
- Processing order: new symbol full-history bootstrap first, then shared-period incremental batching.

### 8.2 Data storage and privacy

- Local CSV storage only.
- No sensitive data beyond API credential in local config.
- Avoid logging full API key in notebook output.

### 8.3 Scalability and performance

- Use chunking of symbols into groups of 100.
- Minimize payload volume with incremental date windows.
- Optional future optimization: parallel batch requests with rate-limit controls.

### 8.4 Potential challenges

- EODHD endpoint behavior differences for multi-symbol vs single-symbol historical queries.
- Rate limits and transient HTTP/network errors.
- Inconsistent symbol coverage (delisted or newly listed securities).
- Large ticker universes increasing runtime on manual execution.

## 9. Milestones and sequencing

### 9.1 Project estimate

- Medium: 3-5 working days

### 9.2 Team size and composition

- 1-2 people: Python notebook developer, reviewer/tester

### 9.3 Suggested phases

- **Phase 1**: Notebook scaffold and file I/O foundation (1 day)

	- Key deliverables: ticker ingest, list-scope folder derivation, symbol file discovery/creation.

- **Phase 2**: Incremental fetch engine and batching (1-2 days)

	- Key deliverables: new symbol bootstrap flow, shared-period detection, 100-symbol chunk execution, API parsing.

- **Phase 3**: Merge logic, quality rules, and reporting (1 day)

	- Key deliverables: dedupe/replace-by-date behavior, sorted persistence, run summary.

- **Phase 4**: Validation and hardening (1 day)

	- Key deliverables: edge-case tests, rerun behavior verification, usage notes.

## 10. User stories

### 10.1 Load ticker universe from CSV

- **ID**: GH-001
- **Description**: As a user, I want to load ticker symbols with exchange suffixes from a CSV in the `data` folder so the notebook can process my selected universe.
- **Acceptance criteria**:

	- Notebook accepts a CSV input path in `data`.
	- Symbols such as `AMZN.US` are read correctly.
	- Empty or invalid symbol rows are reported and skipped.

### 10.2 Create and locate symbol files

- **ID**: GH-002
- **Description**: As a user, I want each symbol to map to one CSV in a scope folder named after the loaded ticker CSV file so data remains separated by universe.
- **Acceptance criteria**:

	- If input is `data/<LIST_NAME>.csv`, existing files are loaded from `data/<LIST_NAME>/{SYMBOL}.csv`.
	- Missing symbol files are created automatically.
	- Scope folder creation is handled if `data/<LIST_NAME>/` does not exist.

### 10.3 Detect incremental date ranges

- **ID**: GH-003
- **Description**: As a user, I want the notebook to derive one shared incremental period across all symbols after new symbols are initialized so updates are consistent.
- **Acceptance criteria**:

	- New symbols are excluded from this step because they are handled in a full-history bootstrap step first.
	- For each symbol file, notebook reads latest local `Date`.
	- Shared start date equals oldest value among all symbol latest dates.
	- End date equals run date.
	- Incremental requests use the shared start date through end date.

### 10.4 Fetch data in 100-symbol batches

- **ID**: GH-004
- **Description**: As a user, I want batched HTTP requests to EODHD so large universes update faster and with fewer calls.
- **Acceptance criteria**:

	- Symbols are chunked into batch size 100.
	- Batching is applied after new symbol bootstrap is completed.
	- Requests include configured EODHD API key from notebook runtime.
	- Batch-level failures are captured without stopping remaining batches.

### 10.9 Detect and initialize newly added symbols

- **ID**: GH-009
- **Description**: As a user, I want newly added ticker symbols in the list CSV to be detected automatically and initialized with full history before incremental updates run.
- **Acceptance criteria**:

	- Notebook compares ticker-list symbols against existing symbol CSV filenames in the target scope folder.
	- For each newly detected symbol, notebook fetches full available history from EODHD and creates `data/<LIST_NAME>/<SYMBOL>.csv`.
	- If multiple symbols are new, they are processed one by one.
	- Incremental batch update starts only after all new symbol bootstrap attempts complete.

### 10.5 Persist clean OHLCV datasets

- **ID**: GH-005
- **Description**: As a user, I want each symbol file updated with standardized OHLCV fields and no duplicate dates.
- **Acceptance criteria**:

	- Output columns include `Date`, `Open`, `High`, `Low`, `Close`, `Adjusted close`, `Volume`.
	- Duplicate dates are removed.
	- If same date exists with new values, stored row is replaced by latest fetched row.
	- Final file is sorted ascending by `Date`.

### 10.6 Continue on failure and support reruns

- **ID**: GH-006
- **Description**: As a user, I want the notebook to continue when some symbols fail so I can rerun only unresolved symbols later.
- **Acceptance criteria**:

	- Run completes even when subset of symbols fail.
	- Final summary lists `updated`, `skipped_up_to_date`, and `failed` symbols.
	- A second run updates previously failed symbols if API/data becomes available.

### 10.7 Manual execution cadence support

- **ID**: GH-007
- **Description**: As a user, I want to run updates manually on any cadence (daily, weekly, monthly) without changing core logic.
- **Acceptance criteria**:

	- Same notebook workflow supports any manual run date.
	- Incremental detection always uses latest local date to current run date.
	- No schedule configuration is required.

### 10.8 Secure API credential handling

- **ID**: GH-008
- **Description**: As a user, I want API key usage to be secure in notebook outputs so credentials are not exposed accidentally.
- **Acceptance criteria**:

	- API key is loaded from notebook configuration, not hardcoded in request logs.
	- Notebook output avoids printing full key value.
	- Missing key error is explicit and actionable.
