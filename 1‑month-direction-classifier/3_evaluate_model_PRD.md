# PRD: 1-Month Direction Classification Notebook

## 1. Product overview

### 1.1 Document title and version

- PRD: 1-Month Direction Classification Notebook
- Version: 1.1

### 1.2 Product summary

This project delivers a single end-to-end Jupyter notebook that loads historical OHLCV stock data from per-symbol CSV files, engineers predictive features, trains and compares multiple machine learning models, and evaluates final performance on a hold-out test set. The notebook predicts 1-month directional actions as a 3-class problem: buy, hold/wait, or sell.

The target is based on forward 20-trading-day returns. Labels are fixed as: buy if return is greater than +5%, sell if return is less than -5%, and hold otherwise. The notebook uses a time-aware approach (no shuffling), pooled cross-sectional data across many symbols, and model comparison against benchmark algorithms.

The universe is loaded from a symbol CSV file in the data folder under 1-month-direction-classifier. The CSV filename defines the matching subfolder containing per-symbol historical files (one CSV per symbol, for example AMZN.US.csv). The end-to-end output includes a clear recommendation of which evaluated model to use, why it was selected, and which hyperparameters to use.

## 2. Goals

### 2.1 Business goals

- Build a repeatable ML workflow to classify 1-month stock direction for many symbols.
- Compare benchmark models under a consistent evaluation protocol.
- Produce actionable diagnostics focused on buy and sell class quality.
- Create a reusable research template that can be rerun as new data arrives.

### 2.2 User goals

- Run one notebook from start to finish without manual handoffs.
- Load a symbol universe from CSV in the local data folder.
- Train, validate, tune, and test models with time-aware data splits.
- Understand model behavior via metrics, confusion matrices, and feature relevance.
- Receive a final model recommendation that includes rationale and exact parameter settings.
- Review a simple strategy-level diagnostic from predicted actions.

### 2.3 Non-goals

- Full production trading system deployment.
- Execution, slippage, fee, and market impact modeling.
- Intraday prediction or tick-level microstructure modeling.
- Causal inference about drivers of returns.

## 3. User personas

### 3.1 Key user types

- Quant researcher
- Data scientist in finance
- Advanced learner building portfolio ML skills

### 3.2 Basic persona details

- **Quant researcher**: needs reproducible experiments and robust time-aware evaluation.
- **Finance data scientist**: needs feature-rich pooled data modeling and comparative baselines.
- **Advanced learner**: needs interpretable workflow with clear diagnostics and outputs.

### 3.3 Role-based access

- **Notebook user**: can configure universe CSV, thresholds, model settings, and run all cells.
- **Project maintainer**: can update feature set, model set, hyperparameter space, and evaluation outputs.

## 4. Functional requirements

- **Configurable universe loading from CSV** (Priority: High)
  - Load symbol list from a user-selected CSV file in 1-month-direction-classifier/data.
  - Enforce naming convention: if the symbol list is NAME.csv, historical per-symbol files are read from data/NAME/.
  - Validate symbol file schema and report invalid rows.

- **Historical data ingestion from per-symbol files** (Priority: High)
  - Load one CSV per symbol using file naming convention SYMBOL.csv.
  - Restrict data to last 6 years from latest available trading date.
  - Enforce expected raw columns: date, open, high, low, close, adj_close, volume.

- **Data quality checks and filtering** (Priority: High)
  - Detect duplicates, missing values, non-monotonic dates, and implausible negative values.
  - Apply missing value policy and symbol-level exclusions for excessive missingness.
  - Apply minimum history and liquidity filters before modeling.

- **Feature engineering pipeline** (Priority: High)
  - Compute per-symbol features (returns, trend, volatility, volume/liquidity, technical signals).
  - Align all features by symbol-date and remove rows lacking required feature history.
  - Identify near-constant features for optional removal.

- **Target labeling** (Priority: High)
  - Compute forward 20-trading-day return per symbol.
  - Apply fixed label rules: buy if > +5%, sell if < -5%, else hold.
  - Drop rows where forward return is undefined.

- **Time-aware data splitting and CV** (Priority: High)
  - Chronological split into train (~70%), validation (~15%), test (~15%).
  - Record split cutoff dates in notebook output.
  - Use TimeSeriesSplit for tuning within train plus validation horizon.

- **Model training and comparison** (Priority: High)
  - Train baseline and candidate models: Logistic Regression, Random Forest, Extra Trees, HistGradientBoosting, LinearSVC, MLP.
  - Use pipelines to prevent leakage and apply scaling only where needed.
  - Rank models by validation macro F1 and buy or sell class performance.

- **Hyperparameter tuning and final model freeze** (Priority: Medium)
  - Select top two models from first-pass validation.
  - Run moderate time-aware hyperparameter search.
  - Freeze chosen model and parameter set for final test evaluation.

- **Evaluation and strategy diagnostics** (Priority: High)
  - Report macro F1, weighted F1, balanced accuracy, class-wise precision/recall/F1.
  - Produce confusion matrices for validation and test.
  - Include a simple long/flat/short cumulative return diagnostic on test predictions.

- **Recommendation output** (Priority: High)
  - At the end of the run, produce a clear recommended model from evaluated candidates.
  - Provide explicit rationale for the recommendation (metric performance, class-wise behavior, stability, and complexity or runtime trade-offs).
  - Print and save the exact chosen hyperparameters needed to reproduce the final model.

- **Run reporting and artifacts** (Priority: Medium)
  - Save summary tables for splits, class balance, model metrics, selected model settings, and final recommendation.
  - Optionally save trained model artifact and feature importance outputs.

- **Security and configuration hygiene** (Priority: Medium)
  - Keep secrets out of notebook outputs.
  - Load API keys or sensitive config from config.py or environment variables when required.

## 5. Feature engineering

### 5.1 Base return and range features

- **Daily returns**
  - ret_1d: simple daily return from close.
  - log_ret_1d: log return.

- **Ranges**
  - tr_range: high - low.
  - true_range: max of range and gaps vs previous close (for volatility).

### 5.2 Multi-horizon return features

- **Short and medium horizon returns**
  - ret_5d, ret_10d, ret_20d, ret_60d.
  - log_ret_5d, log_ret_20d.

- **Design note**
  - These capture momentum at different horizons and are key predictors for a 1-month label.

### 5.3 Trend features (moving averages and relative position)

- **Moving averages**
  - sma_5, sma_20, sma_50, sma_200 on close.

- **Relative-position features**
  - close_over_sma_20, close_over_sma_50, close_over_sma_200 as close / sma_x.

- **Trend slope approximations**
  - sma_20_slope_5d, sma_50_slope_5d: relative change in SMA over last 5 days.

### 5.4 Volatility features

- **Rolling return volatility**
  - vol_ret_5d, vol_ret_20d, vol_ret_60d: rolling std of ret_1d over respective windows.

- **True-range volatility**
  - vol_tr_5d, vol_tr_20d: rolling std of true_range.

### 5.5 Volume and liquidity features

- **Base and rolling volume**
  - value_traded: close * volume.
  - vol_ma_20, vol_ma_60: moving averages of volume.
  - vol_rel_20: volume / vol_ma_20.
  - value_traded_ma_20, value_traded_rel_20: similar for value_traded.

- **Rationale**
  - These help capture unusual trading activity or illiquidity.

### 5.6 Technical indicators

- **RSI**
  - rsi_14: 14-day RSI on close.

- **MACD**
  - macd: EMA 12 - EMA 26.
  - macd_signal: 9-day EMA of macd.
  - macd_hist: difference between MACD and signal.

- **ATR**
  - atr_14: 14-day Average True Range (EMA of true_range).

### 5.7 High/low context

- **Rolling highs and lows**
  - hh_20d, ll_20d: 20-day highest high and lowest low.
  - dist_from_20d_high: (close / hh_20d) - 1.
  - dist_from_20d_low: (close / ll_20d) - 1.

### 5.8 Feature consolidation and final dataset

- **How to merge all features**
  - Ensure features for each symbol are aligned by date.
  - Drop rows where any required feature cannot be computed due to insufficient history.

- **Feature sanity checks**
  - Inspect distributions and correlations.
  - Check for constant or near-constant features to potentially drop.

## 6. User experience

### 6.1 Entry points and first-time user flow

- User opens notebook in 1-month-direction-classifier/train.
- User selects universe CSV path in data folder and confirms date horizon.
- User runs notebook top-to-bottom in one execution.
- User reviews data quality summary, feature readiness, model comparison, final recommendation, and strategy diagnostics.

### 6.2 Core experience

- **Configure and validate inputs**: user sets paths and key parameters; notebook validates schema and files.
  - This ensures immediate visibility into broken inputs before expensive training starts.
- **Prepare modeling dataset**: notebook cleans, filters, engineers features, and constructs labels.
  - This ensures features and targets are aligned and leakage-safe.
- **Train and compare models**: notebook runs baseline and candidate models with consistent metrics.
  - This ensures fair model comparison and transparent model ranking.
- **Tune finalists and evaluate test set**: notebook tunes top models and runs untouched hold-out test.
  - This ensures realistic performance estimates.
- **Recommend final model and parameters**: notebook outputs the selected model name, why it was chosen, and the exact parameter set.
  - This ensures the notebook ends with a directly actionable decision.
- **Review strategy diagnostics**: notebook maps predictions to long/flat/short and plots cumulative returns.
  - This ensures model quality is interpreted in an action-oriented context.

### 6.3 Advanced features and edge cases

- Handle sparse symbol histories and drop non-compliant symbols.
- Handle rolling-window warm-up periods for long lookback features.
- Handle severe class imbalance with class weights and threshold review diagnostics.
- Handle missing per-symbol files while continuing execution with warnings.
- Handle unstable metrics in low-sample periods by reporting per-year class support.

### 6.4 UI and UX highlights

- Clear sectioned notebook structure matching data-to-model lifecycle.
- Compact validation prints and summary tables for each stage.
- Plot outputs for class balance, confusion matrices, and strategy curves.
- Deterministic ordering and reproducible random seeds.
- Final decision block with recommendation, rationale, and full parameter dictionary.

## 7. Narrative

The user selects a universe CSV from the data folder and runs the notebook once end-to-end. The notebook ingests and validates six years of per-symbol OHLCV history, filters symbols by quality and liquidity, and builds a pooled feature matrix with forward 20-day labels. It then performs time-aware model comparison, tunes top candidates, and evaluates finalists on a hold-out test horizon. The output includes ML metrics, strategy diagnostics, and a final explicit recommendation that states which model to use, why it is preferred, and which exact hyperparameters to apply.

## 8. Success metrics

### 8.1 User-centric metrics

- Notebook completes end-to-end run without manual intervention.
- All stage summaries are generated (data quality, class balance, model scores, and recommendation block).
- Final outputs are understandable and reproducible with fixed seeds.

### 8.2 Business metrics

- Final model outperforms majority-class baseline on macro F1 by a meaningful margin.
- Buy and sell class F1 exceed minimum acceptable thresholds defined by the team.
- Strategy diagnostic indicates improvement over naive hold-only baseline.

### 8.3 Technical metrics

- Primary metric: macro F1 on validation and test.
- Secondary metrics: weighted F1, balanced accuracy, class-wise precision/recall/F1.
- Data quality pass rate: percentage of symbols retained after filtering.
- Runtime and memory usage within acceptable notebook limits.
- Recommendation reproducibility: selected model parameters are fully logged and serializable.

## 9. Technical considerations

### 9.1 Integration points

- Universe list file in 1-month-direction-classifier/data.
- Per-symbol OHLCV archives in matching data subfolder named after universe CSV.
- Existing configuration patterns (config.py, local paths, and environment variables).

### 9.2 Data storage and privacy

- Inputs and outputs remain local in project directories.
- No sensitive credentials written to notebook outputs.
- Respect .gitignore rules for generated data artifacts where applicable.

### 9.3 Scalability and performance

- Use vectorized pandas operations and groupby-by-symbol transformations.
- Avoid redundant recomputation by caching intermediate frames in memory.
- Keep hyperparameter searches moderate to preserve notebook runtime.

### 9.4 Potential challenges

- Class imbalance from fixed +-5% thresholds.
- Regime shifts reducing model stability over time.
- Data quality heterogeneity across symbols and exchanges.
- Overfitting risk during tuning without strict chronological validation.

## 10. Milestones and sequencing

### 10.1 Project estimate

- Medium: 1 to 2 weeks

### 10.2 Team size and composition

- 1 to 2 people: quant or data scientist, optional reviewer

### 10.3 Suggested phases

- **Phase 1**: Data ingestion, cleaning, and filtering (2 to 3 days)
  - Key deliverables: validated pooled dataset and universe summary.
- **Phase 2**: Feature and target engineering (2 to 3 days)
  - Key deliverables: complete feature matrix and class balance diagnostics.
- **Phase 3**: Baseline and candidate model training (2 days)
  - Key deliverables: validation leaderboard and shortlisted models.
- **Phase 4**: Tuning, recommendation output, final test, and strategy diagnostics (2 to 3 days)
  - Key deliverables: final model recommendation with rationale and parameters, confusion matrices, and action-level return chart.

## 11. User stories

### 11.1 Configure and run notebook end-to-end

- **ID**: GH-001
- **Description**: As a notebook user, I want to run one notebook from start to finish so I can ingest data, train models, and see final test results in one execution.
- **Acceptance criteria**:
  - Notebook executes top-to-bottom without requiring out-of-band scripts.
  - Required inputs are validated before model training begins.
  - End-of-run summary includes selected model and final test metrics.

### 11.2 Select universe from CSV in data folder

- **ID**: GH-002
- **Description**: As a user, I want to choose any valid universe CSV from the data folder so I can run the notebook on different symbol sets without rewriting logic.
- **Acceptance criteria**:
  - User can point to a symbol CSV file in 1-month-direction-classifier/data.
  - If the symbol list is NAME.csv, the notebook reads historical files from data/NAME/.
  - Invalid or missing symbol rows are reported and excluded.

### 11.3 Enforce six-year rolling horizon

- **ID**: GH-003
- **Description**: As a user, I want the notebook to use the latest six years of data so models stay relevant to current regimes.
- **Acceptance criteria**:
  - Date range is computed from latest available trading date minus six years.
  - Rows outside the horizon are excluded before feature engineering.
  - Notebook prints actual start and end dates used.

### 11.4 Apply data quality and liquidity filters

- **ID**: GH-004
- **Description**: As a user, I want poor-quality symbols excluded so model training data is reliable.
- **Acceptance criteria**:
  - Symbols failing minimum history threshold are excluded.
  - Symbols failing median volume threshold are excluded.
  - Final universe count and pooled row count are reported.

### 11.5 Engineer per-symbol feature set

- **ID**: GH-005
- **Description**: As a user, I want a rich and consistent feature set so the models can learn trend, momentum, volatility, and liquidity behavior.
- **Acceptance criteria**:
  - All features defined in sections 5.1 to 5.8 are computed per symbol.
  - Features are aligned by symbol-date and concatenated into one pooled dataset.
  - Rows with insufficient lookback history for required features are dropped.

### 11.6 Construct fixed-threshold 3-class labels

- **ID**: GH-006
- **Description**: As a user, I want labels based on forward 20-day returns with fixed thresholds so predictions map directly to buy/hold/sell decisions.
- **Acceptance criteria**:
  - fwd_ret_20d is computed as (close_t+20 / close_t) - 1.
  - Label rule is fixed: buy if > +5%, sell if < -5%, hold otherwise.
  - Last 20 rows per symbol are excluded from modeling.

### 11.7 Report class imbalance diagnostics

- **ID**: GH-007
- **Description**: As a user, I want class distribution diagnostics so I can understand minority class challenges.
- **Acceptance criteria**:
  - Class proportions are reported globally and by year.
  - Notebook highlights buy and sell minority class support.
  - Optional mitigation knobs (class weight usage notes, threshold sensitivity analysis) are shown.

### 11.8 Use time-aware train/validation/test split

- **ID**: GH-008
- **Description**: As a user, I want chronological splitting so no future information leaks into training.
- **Acceptance criteria**:
  - Rows are sorted chronologically before split.
  - Split proportions target approximately 70/15/15 by time.
  - Actual cutoff dates are printed.

### 11.9 Tune with TimeSeriesSplit

- **ID**: GH-009
- **Description**: As a user, I want time-aware CV during tuning so hyperparameter selection reflects temporal constraints.
- **Acceptance criteria**:
  - TimeSeriesSplit is used for tuning on training plus validation period only.
  - Final test data is untouched until final evaluation.
  - Fold-level validation metrics are logged.

### 11.10 Compare baseline and candidate models

- **ID**: GH-010
- **Description**: As a user, I want a model leaderboard so I can compare algorithms fairly.
- **Acceptance criteria**:
  - Baseline includes at least majority-class predictor.
  - Candidate set includes Logistic Regression, Random Forest, Extra Trees, HistGradientBoosting, LinearSVC, and MLP.
  - Validation leaderboard includes macro F1 and class-wise buy and sell metrics.

### 11.11 Apply leakage-safe preprocessing pipelines

- **ID**: GH-011
- **Description**: As a user, I want preprocessing bundled with models so scaling and transforms are fit only on training data.
- **Acceptance criteria**:
  - Pipeline is used for models requiring scaling.
  - Tree models can run without scaling.
  - No transformation is fit on validation or test subsets directly.

### 11.12 Final test evaluation and error analysis

- **ID**: GH-012
- **Description**: As a user, I want final hold-out results and error patterns so I can judge real-world readiness.
- **Acceptance criteria**:
  - Finalists are refit on training plus validation only.
  - Test report includes macro F1, weighted F1, balanced accuracy, class-wise precision/recall/F1, and confusion matrix.
  - Misclassification patterns (especially buy vs hold and sell vs hold) are summarized.

### 11.13 Include strategy diagnostics

- **ID**: GH-013
- **Description**: As a user, I want a simple action-based performance view so I can contextualize model predictions in trading terms.
- **Acceptance criteria**:
  - Predicted labels map to long/flat/short actions.
  - Test-period cumulative return curve is computed and displayed with stated assumptions.
  - Diagnostic is marked as simplified and non-production.

### 11.14 Protect configuration and secrets

- **ID**: GH-014
- **Description**: As a maintainer, I want secure handling of credentials so sensitive data is not exposed.
- **Acceptance criteria**:
  - Secrets are loaded from config.py or environment variables.
  - Notebook does not print full secret values.
  - Missing credentials produce actionable validation messages.

### 11.15 Produce final model recommendation output

- **ID**: GH-015
- **Description**: As a user, I want a final explicit recommendation so I know exactly which model to deploy for the 1-month direction task.
- **Acceptance criteria**:
  - Notebook ends with a recommendation block naming the chosen model.
  - Recommendation block states why this model was selected versus alternatives (macro F1, buy/sell class metrics, stability across folds, and complexity/runtime trade-off).
  - Recommendation block includes full reproducible parameter dictionary for the selected model.
  - Recommendation block includes runner-up model and the metric deltas to make the decision transparent.

After generating the PRD, I will ask if you want to proceed with creating GitHub issues for the user stories. If you agree, I will create them and provide you with the links.