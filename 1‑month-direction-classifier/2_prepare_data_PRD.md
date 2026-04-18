# PRD: 1-month direction data-preparation notebook

## 1. Product overview

### 1.1 Document title and version

- PRD: 1-month direction data-preparation notebook
- Version: 1.0

### 1.2 Product summary

This project defines a Jupyter notebook that prepares a machine-learning-ready dataset from locally stored per-symbol historical stock CSV files. The notebook reads a user-selected universe file in `1-month-direction-classifier/data` that must include a `Symbol` column (for example, `AMZN.US`, `TSLA.US`), validates input quality, loads raw OHLCV history for each symbol, computes features, creates 20-trading-day forward direction labels, and saves the final dataset for downstream model training.

The notebook scope is strictly data preparation. It does not train, evaluate, or tune machine learning models. All quality thresholds and filtering policies are configurable in a dedicated configuration section at the beginning of the notebook so users can adapt the workflow for different universes while keeping a stable, reproducible pipeline.

The final prepared dataset is saved into `1-month-direction-classifier/2_prepare_data`. Default output format is Parquet for efficient pandas workflows (fast I/O, typed columns, smaller files), with an optional CSV export toggle for interoperability.

## 2. Goals

### 2.1 Business goals

- Produce a consistent, high-quality feature dataset suitable for a 1-month direction classification task.
- Reduce data leakage and preprocessing errors before model training.
- Standardize preprocessing so repeated runs are reproducible across universes.

### 2.2 User goals

- Select any valid symbol-universe CSV in `data` and run one notebook end-to-end.
- Detect and report bad symbols, schema issues, and symbol-level quality failures.
- Receive a final pooled DataFrame with engineered features, labels, and summary diagnostics.

### 2.3 Non-goals

- Building model training, cross-validation, or backtesting logic.
- Downloading market data from external APIs (input data is local CSV files only).
- Creating a production scheduler or orchestration service.

## 3. User personas

### 3.1 Key user types

- Quant researcher
- Retail systematic trader
- Data analyst supporting model development

### 3.2 Basic persona details

- **Quant researcher**: Needs clean, feature-rich, leakage-safe inputs to iterate quickly on ML models.
- **Retail systematic trader**: Wants transparent notebook logic and configurable filters without changing deep code.
- **Data analyst**: Validates data quality and ensures feature consistency across many symbols.

### 3.3 Role-based access

- **Notebook operator**: Can select input universe CSV, execute notebook, and write outputs to `2_prepare_data`.
- **Project maintainer**: Can modify thresholds, feature toggles, and schema rules in configuration cells.

## 4. Functional requirements

- **Introduction and overview section** (Priority: High)

	- Provide notebook objective, scope boundaries, and expected input/output paths.
	- Explain naming convention: `NAME.csv` in `data` maps to per-symbol files in `data/NAME/{SYMBOL}.csv`.

- **Imports and environment setup** (Priority: High)

	- Import required libraries (`pandas`, `numpy`, `pathlib`, plotting/stats libraries, optional `pyarrow`).
	- Check required package availability and provide actionable error messaging.

- **Configurable universe loading from CSV** (Priority: High)

	- Allow user to select a universe CSV path in `1-month-direction-classifier/data`.
	- Validate existence of mandatory `Symbol` column.
	- Normalize symbols (trim spaces, uppercase as configured), detect duplicates, and report invalid rows.
	- Define user-configurable variables at notebook start, including:
	- lookback years (default 6),
	- missing-value thresholds,
	- minimum history length,
	- minimum liquidity,
	- near-constant feature threshold,
	- output format toggles.

- **Historical data ingestion from per-symbol files** (Priority: High)

	- For each valid symbol, read `data/NAME/{SYMBOL}.csv`.
	- Enforce expected raw columns: `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`.
	- Parse and sort dates ascending; restrict rows to last 6 years from each symbol's latest available trading date.

- **Data quality checks and filtering** (Priority: High)

	- Detect duplicates, missing values, non-monotonic dates, and implausible negative values.
	- Apply configurable missing-value policy (drop rows, forward fill selected fields, or symbol exclusion).
	- Exclude symbols exceeding missingness threshold.
	- Apply minimum history and liquidity filters before feature pooling.

- **Feature engineering pipeline** (Priority: High)

	- Compute all required per-symbol features in temporal order.
	- Align features by symbol-date and remove rows without sufficient history.
	- Detect constant and near-constant features and optionally remove them.

- **Target labeling** (Priority: High)

	- Compute forward 20-trading-day return per symbol.
	- Assign labels using fixed rule:
	- `buy` if forward return > +5%,
	- `sell` if forward return < -5%,
	- `hold` otherwise.
	- Drop rows where forward return is undefined.

- **Save DataFrame for later use** (Priority: High)

	- Save final pooled dataset in `1-month-direction-classifier/2_prepare_data`.
	- Default output: Parquet (`prepared_dataset.parquet`).
	- Optional output: CSV (`prepared_dataset.csv`) if enabled.
	- Save metadata summary file with row counts, symbol counts, and filtering statistics.

- **Statistical summary and metrics reporting** (Priority: High)

	- Provide summary of row counts before/after each major pipeline stage.
	- Report exclusion reasons at symbol level.
	- Show feature distribution snapshot and label distribution.

- **Glossary generation** (Priority: Medium)

	- Provide a glossary table in notebook output or markdown that includes:
	- variable name,
	- full feature name,
	- formula,
	- detailed description.

## 5. User experience

### 5.1 Entry points and first-time user flow

- Open notebook in `1-month-direction-classifier/2_prepare_data`.
- Set input universe CSV path and configuration variables in first config cell.
- Run notebook top to bottom.
- Review validation/exclusion report.
- Inspect summary metrics and saved output locations.

### 5.2 Core experience

- **Select universe file**: User sets one path to `data/NAME.csv`.
	- Ensures symbol source is explicit and reproducible.
- **Validate symbols and discover files**: Notebook validates schema and maps symbols to `data/NAME/{SYMBOL}.csv`.
	- Prevents silent ingestion failures.
- **Ingest and clean raw OHLCV**: Notebook applies schema checks and quality policies.
	- Improves downstream feature reliability.
- **Engineer features and labels**: Notebook computes all configured features and 20-day forward labels.
	- Produces model-ready supervised learning dataset.
- **Save and summarize**: Notebook writes final dataset and metrics artifacts.
	- Supports immediate handoff to training notebook.

### 5.3 Advanced features and edge cases

- Universe CSV contains additional columns beyond `Symbol`.
- Missing per-symbol file for a listed symbol.
- Symbol file with partial schema mismatch.
- Symbol with insufficient history for 200-day features.
- Extremely low-liquidity symbols failing configurable liquidity thresholds.

### 5.4 UI/UX highlights

- One configuration block at top of notebook for all thresholds.
- Clear stage-by-stage logging with row and symbol deltas.
- Final compact dashboard-style metrics tables (data quality, feature stats, labels).

## 6. Narrative

The user chooses a universe CSV in `data`, sets thresholds in a single configuration section, and runs the notebook. The pipeline validates symbols, ingests each matching per-symbol file from `data/NAME`, trims history to the latest six years, and enforces schema and quality checks. It then computes a complete feature set per symbol, creates 20-trading-day direction labels with fixed buy/sell/hold rules, removes unusable rows, and pools all symbols into one final dataset. The notebook saves this prepared DataFrame to `2_prepare_data` (Parquet by default) and provides transparent metrics that explain exactly what was filtered, calculated, and retained.

## 7. Success metrics

### 7.1 User-centric metrics

- 100% of successful runs produce a saved prepared dataset and summary artifact.
- User can configure thresholds without editing core processing functions.
- Validation report clearly identifies invalid symbols and exclusion reasons.

### 7.2 Business metrics

- Reduced downstream model-training failures caused by bad input data.
- Faster experiment iteration due to consistent preprocessing outputs.

### 7.3 Technical metrics

- 0 duplicate (`symbol`, `date`) rows in final dataset.
- 100% of retained rows have all required engineered features and labels populated.
- Data quality checks executed for all symbols and logged in summary.

## 8. Technical considerations

### 8.1 Integration points

- Input universe path: `1-month-direction-classifier/data/{NAME}.csv`.
- Per-symbol history path: `1-month-direction-classifier/data/{NAME}/{SYMBOL}.csv`.
- Output dataset path: `1-month-direction-classifier/2_prepare_data/prepared_dataset.parquet`.
- Optional output CSV path: `1-month-direction-classifier/2_prepare_data/prepared_dataset.csv`.
- Handoff expectation: downstream training notebook reads prepared output directly with pandas.

### 8.2 Data storage and privacy

- Local filesystem storage only.
- No PII expected.
- Preserve deterministic column names and data types for reproducibility.

### 8.3 Scalability and performance

- Prefer vectorized pandas operations and grouped rolling computations.
- Use Parquet default for faster read/write and reduced storage.
- Keep optional CSV export for compatibility when needed.

### 8.4 Potential challenges

- Heterogeneous symbol files (schema/type drift across universes).
- Warm-up period loss from long-window indicators (for example, 200-day SMA).
- Memory pressure when pooling very large universes in one DataFrame.

## 9. Milestones and sequencing

### 9.1 Project estimate

- Medium: 4-6 working days

### 9.2 Team size and composition

- 1-2 people: notebook developer and reviewer/tester

### 9.3 Suggested phases

- **Phase 1**: Notebook scaffold and configuration layer (0.5-1 day)
	- Key deliverables: imports, config variables, path handling, universe schema validation.
- **Phase 2**: Ingestion and data quality filtering (1-2 days)
	- Key deliverables: per-symbol loading, six-year trimming, data checks, exclusions.
- **Phase 3**: Feature engineering and target labeling (1.5-2 days)
	- Key deliverables: complete feature set, forward return labels, row alignment.
- **Phase 4**: Output artifacts and diagnostics (1 day)
	- Key deliverables: Parquet/CSV save, quality summaries, glossary output.

## 10. User stories

### 10.1 Load configurable symbol universe

- **ID**: GH-001
- **Description**: As a notebook operator, I want to load a user-selected universe CSV from `data` so I can prepare different stock universes without changing notebook code.
- **Acceptance criteria**:
	- Notebook accepts a configurable path to `data/{NAME}.csv`.
	- CSV must contain `Symbol`; additional columns are allowed.
	- Invalid symbol rows are reported with reason and excluded.

### 10.2 Enforce universe-to-folder naming convention

- **ID**: GH-002
- **Description**: As a user, I want per-symbol files resolved using the universe file name so the correct data folder is always used.
- **Acceptance criteria**:
	- If input is `data/{NAME}.csv`, symbol files are loaded from `data/{NAME}/{SYMBOL}.csv`.
	- Missing symbol files are reported in diagnostics.
	- Processing continues for available symbols.

### 10.3 Validate and ingest historical symbol files

- **ID**: GH-003
- **Description**: As a user, I want each symbol file validated against the expected raw schema so downstream features are computed reliably.
- **Acceptance criteria**:
	- Required raw columns are exactly checked: `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`.
	- Date parsing failures or missing required columns mark symbol as invalid.
	- Retained rows are restricted to last 6 years from symbol-local latest trading date.

### 10.4 Apply data quality checks and exclusions

- **ID**: GH-004
- **Description**: As a user, I want configurable quality checks so poor data does not degrade the training dataset.
- **Acceptance criteria**:
	- Duplicates, missingness, non-monotonic dates, and negative-value anomalies are detected.
	- Configurable thresholds determine row-level fixes vs symbol-level exclusion.
	- Symbol exclusion report includes explicit reason codes.

### 10.5 Enforce minimum history and liquidity filters

- **ID**: GH-005
- **Description**: As a user, I want symbols filtered by history depth and liquidity so model inputs remain meaningful.
- **Acceptance criteria**:
	- Minimum history threshold is configurable and applied before feature pooling.
	- Liquidity threshold (for example, median 20-day value traded) is configurable.
	- Filtered symbols are removed and logged.

### 10.6 Compute required feature set per symbol

- **ID**: GH-006
- **Description**: As a user, I want all specified returns, trend, volatility, volume/liquidity, technical, and high/low context features computed per symbol.
- **Acceptance criteria**:
	- All features listed in Section 11 glossary are computed using defined formulas.
	- Computations are grouped by symbol and preserve temporal ordering.
	- Rows without sufficient history for required features are dropped.

### 10.7 Remove constant and near-constant features optionally

- **ID**: GH-007
- **Description**: As a user, I want optional near-constant feature removal to reduce low-information predictors.
- **Acceptance criteria**:
	- Near-constant threshold is configurable.
	- Removed feature list is output in diagnostics.
	- Default behavior is configurable (on/off).

### 10.8 Generate forward 20-day target labels

- **ID**: GH-008
- **Description**: As a user, I want labels generated from future 20-trading-day returns using fixed buy/sell/hold thresholds.
- **Acceptance criteria**:
	- `fwd_ret_20d = close(t+20) / close(t) - 1` computed per symbol.
	- Label rules are fixed: buy > +5%, sell < -5%, otherwise hold.
	- Rows with undefined forward return are dropped.

### 10.9 Save prepared dataset and metrics artifacts

- **ID**: GH-009
- **Description**: As a user, I want prepared outputs written to `2_prepare_data` so the next notebook can load them directly.
- **Acceptance criteria**:
	- Default output is Parquet file in `2_prepare_data`.
	- Optional CSV output is available via configuration.
	- Run metadata includes counts before/after each major stage and label distribution.

### 10.10 Ensure secure and controlled execution

- **ID**: GH-010
- **Description**: As a maintainer, I want controlled local execution and safe logging so no sensitive environment details are exposed.
- **Acceptance criteria**:
	- Notebook does not print sensitive environment values.
	- File access is limited to project-relative input/output paths.
	- Errors surface actionable messages without exposing sensitive system data.

## 11. Glossary

### 11.1 Required raw columns

- **symbol**: Ticker symbol with exchange suffix from universe CSV (`Symbol`), standardized for joins.
- **date**: Trading date.
- **open**: Opening price.
- **high**: Highest price of day.
- **low**: Lowest price of day.
- **close**: Closing price.
- **adj_close**: Adjusted closing price.
- **volume**: Traded share volume.

### 11.2 Engineered features and targets

- **ret_1d**: Daily simple return. Formula: `close_t / close_{t-1} - 1`.
- **log_ret_1d**: Daily log return. Formula: `ln(close_t / close_{t-1})`.
- **tr_range**: Intraday range. Formula: `high_t - low_t`.
- **true_range**: True range. Formula: `max(high_t - low_t, abs(high_t - close_{t-1}), abs(low_t - close_{t-1}))`.
- **ret_5d**: 5-day return. Formula: `close_t / close_{t-5} - 1`.
- **ret_10d**: 10-day return. Formula: `close_t / close_{t-10} - 1`.
- **ret_20d**: 20-day return. Formula: `close_t / close_{t-20} - 1`.
- **ret_60d**: 60-day return. Formula: `close_t / close_{t-60} - 1`.
- **log_ret_5d**: 5-day log return. Formula: `ln(close_t / close_{t-5})`.
- **log_ret_20d**: 20-day log return. Formula: `ln(close_t / close_{t-20})`.
- **sma_5**: 5-day simple moving average of close.
- **sma_20**: 20-day simple moving average of close.
- **sma_50**: 50-day simple moving average of close.
- **sma_200**: 200-day simple moving average of close.
- **close_over_sma_20**: Relative position to short trend. Formula: `close_t / sma_20_t`.
- **close_over_sma_50**: Relative position to medium trend. Formula: `close_t / sma_50_t`.
- **close_over_sma_200**: Relative position to long trend. Formula: `close_t / sma_200_t`.
- **sma_20_slope_5d**: 5-day SMA20 slope approximation. Formula: `sma_20_t / sma_20_{t-5} - 1`.
- **sma_50_slope_5d**: 5-day SMA50 slope approximation. Formula: `sma_50_t / sma_50_{t-5} - 1`.
- **vol_ret_5d**: 5-day rolling std of `ret_1d`.
- **vol_ret_20d**: 20-day rolling std of `ret_1d`.
- **vol_ret_60d**: 60-day rolling std of `ret_1d`.
- **vol_tr_5d**: 5-day rolling std of `true_range`.
- **vol_tr_20d**: 20-day rolling std of `true_range`.
- **value_traded**: Daily traded value. Formula: `close_t * volume_t`.
- **vol_ma_20**: 20-day moving average of volume.
- **vol_ma_60**: 60-day moving average of volume.
- **vol_rel_20**: Relative volume. Formula: `volume_t / vol_ma_20_t`.
- **value_traded_ma_20**: 20-day moving average of `value_traded`.
- **value_traded_rel_20**: Relative traded value. Formula: `value_traded_t / value_traded_ma_20_t`.
- **rsi_14**: 14-day RSI of close using standard Wilder smoothing.
- **macd**: Moving Average Convergence Divergence. Formula: `EMA_12(close) - EMA_26(close)`.
- **macd_signal**: Signal line. Formula: `EMA_9(macd)`.
- **macd_hist**: MACD histogram. Formula: `macd - macd_signal`.
- **atr_14**: 14-day ATR from exponentially smoothed `true_range`.
- **hh_20d**: 20-day rolling highest high.
- **ll_20d**: 20-day rolling lowest low.
- **dist_from_20d_high**: Distance from rolling high. Formula: `(close_t / hh_20d_t) - 1`.
- **dist_from_20d_low**: Distance from rolling low. Formula: `(close_t / ll_20d_t) - 1`.
- **fwd_ret_20d**: Forward 20-trading-day return target precursor. Formula: `close_{t+20} / close_t - 1`.
- **label**: Classification target where `buy` if `fwd_ret_20d > 0.05`, `sell` if `fwd_ret_20d < -0.05`, else `hold`.

### 11.3 Recommended default configurable variables

- **LOOKBACK_YEARS = 6**: Historical window per symbol.
- **MIN_HISTORY_DAYS = 252**: Minimum rows required after cleaning.
- **MAX_MISSING_FRAC_PER_SYMBOL = 0.05**: Maximum allowed missing fraction before exclusion.
- **ROW_MISSING_POLICY = "drop"**: Row-level missing handling (`drop`, `ffill_selected`, configurable custom).
- **MIN_MEDIAN_VALUE_TRADED_20D = 1_000_000**: Liquidity floor.
- **NEAR_CONSTANT_STD_THRESHOLD = 1e-8**: Near-constant feature detection threshold.
- **DROP_NEAR_CONSTANT_FEATURES = True**: Toggle feature removal.
- **SAVE_PARQUET = True**: Primary output toggle.
- **SAVE_CSV = False**: Optional compatibility output.
- **OUTPUT_BASENAME = "prepared_dataset"**: Shared output file stem.
