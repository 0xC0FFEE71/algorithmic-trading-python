# PRD: 1-month direction model evaluation notebook

## 1. Product overview

### 1.1 Document title and version

- PRD: 1-month direction model evaluation notebook
- Version: 1.0

### 1.2 Product summary

This project defines a Jupyter notebook that trains and evaluates one machine learning model for the 1-month stock direction classifier. The notebook is designed as a reusable template: duplicating it and changing the model class, its hyperparameters, and a single `MODEL_NAME` identifier string is all that is needed to evaluate any of the 5–6 candidate classifiers.

The notebook reads the already-prepared Parquet dataset from `1-month-direction-classifier/2_prepare_data`, splits it in a strictly time-aware fashion (no shuffling), trains the chosen model inside a scikit-learn Pipeline, evaluates it against a simple baseline, and writes all results to a standardized JSON artifact and optional CSV file under `1-month-direction-classifier/3_evaluate_model`. These artifacts are intentionally uniform across notebooks so a separate comparison step can load and rank all models without parsing free-form output.

The notebook does not perform hyperparameter tuning. Tuning is the responsibility of a separate future notebook that uses `TimeSeriesSplit`-based search. This notebook records the chosen hyperparameters (even if they are defaults) so results are fully reproducible.

## 2. Goals

### 2.1 Business goals

- Produce comparable, machine-readable evaluation artifacts for every candidate model.
- Establish a rigorous baseline so model value over naive rules is always measured.
- Enable parallel model development by making the template self-contained per notebook.

### 2.2 User goals

- Run one notebook end-to-end to get train/validation/test performance for a single model.
- Change as little as possible (model class + `MODEL_NAME`) to evaluate a different candidate.
- Trust results because time-aware splits guarantee no future information leakage.

### 2.3 Non-goals

- Hyperparameter search or cross-validated tuning (separate notebook).
- Multi-model comparison or ranking (separate aggregation step).
- Production deployment or inference pipelines.
- Downloading or re-engineering data (handled by earlier notebooks).

## 3. User personas

### 3.1 Key user types

- Quant researcher
- Retail systematic trader
- Data scientist iterating on ML model selection

### 3.2 Basic persona details

- **Quant researcher**: Needs rigorous, leakage-free evaluation and standardized metrics to compare model families fairly.
- **Retail systematic trader**: Wants a clear template they can duplicate for each model with minimal code changes.
- **Data scientist**: Uses saved JSON metrics artifacts to aggregate model performance programmatically.

### 3.3 Role-based access

- **Notebook operator**: Can configure model, execute all cells, and write evaluation artifacts to `3_evaluate_model`.
- **Project maintainer**: Can modify the template notebook structure and result schema definitions.

## 4. Functional requirements

- **Notebook configuration and model identifier** (Priority: High)

	- Expose a dedicated configuration section defining:
		- Path to the prepared Parquet dataset (default: `1-month-direction-classifier/2_prepare_data/prepared_dataset.parquet`).
		- Output directory for all evaluation artifacts (default: `1-month-direction-classifier/3_evaluate_model`).
		- `MODEL_NAME` string used in all output file names (for example, `hist_gradient_boosting_baseline`).
		- Random seed(s) for reproducibility.
	- Document that changing `MODEL_NAME` and the model configuration in Section 6 is the only edit required to adapt the notebook for a different candidate.

- **Library imports** (Priority: High)

	- Import `pandas`, `numpy`, `pathlib`, `json`, `time`, `matplotlib`, `seaborn`, and all required scikit-learn components.
	- Import at the top of the notebook in a single dedicated cell.

- **Dataset loading and validation** (Priority: High)

	- Load the single Parquet file into `df_raw`.
	- Verify that all expected raw columns and engineered feature columns are present, including `label`.
	- Verify that `date` is parsed as a datetime type.
	- Print overall shape, date range, and number of unique symbols as a quick sanity check.

- **Feature and target selection** (Priority: High)

	- Explicitly define the list of feature columns: all engineered predictors except `fwd_ret_20d`, `label`, `symbol`, and `date`.
	- Create `X` (features DataFrame), `y` (target Series), and a `meta` DataFrame retaining `symbol` and `date`.
	- Remove rows where `label` is missing or not in `{buy, hold, sell}`.
	- Remove rows where any required feature is NaN.
	- Report remaining row count and class distribution after cleaning.

- **Time-aware train/validation/test split** (Priority: High)

	- Sort the dataset by `date` (then `symbol` for stability) before splitting.
	- Split chronologically with no shuffling:
		- Train: earliest ~70% of the time span.
		- Validation: next ~15%.
		- Test: most recent ~15%.
	- Record actual split boundary dates in named variables (`train_end_date`, `val_end_date`, `test_start_date`, `test_end_date`).
	- Create `X_train`, `y_train`, `X_val`, `y_val`, `X_test`, `y_test`.
	- Confirm no date overlap between splits.
	- Log row counts and class distributions for each split.

- **Baseline classifier** (Priority: High)

	- Define a trivial baseline (for example: always predict the majority class from the training set).
	- Evaluate the baseline on both validation and test sets.
	- Compute macro F1, weighted F1, balanced accuracy, per-class precision/recall/F1, and confusion matrix.
	- Store results in a `baseline_results` dictionary in the same schema as model results.

- **Model definition inside a scikit-learn Pipeline** (Priority: High)

	- Specify the model class and all key hyperparameters explicitly (even if defaults are kept).
	- Document whether the model requires feature scaling and configure accordingly:
		- Models requiring scaling (Logistic Regression, LinearSVC, MLPClassifier): include `StandardScaler` fitted on training data only.
		- Tree-based models (RandomForest, ExtraTrees, HistGradientBoosting): no scaling step.
	- Build a `Pipeline` that encapsulates preprocessing and the estimator to prevent any data leakage.
	- Document `class_weight` strategy used to handle `hold`-class dominance.

- **Model training** (Priority: High)

	- Fit the pipeline on `X_train` and `y_train`.
	- Record approximate training duration.
	- Note any convergence warnings or other diagnostics.

- **Validation performance evaluation** (Priority: High)

	- Predict class labels (`y_val_pred`) and, where available, class probabilities (`y_val_proba`) on the validation set.
	- Compute and display:
		- Macro F1.
		- Weighted F1.
		- Balanced accuracy.
		- Per-class precision, recall, and F1 for `buy`, `hold`, and `sell`.
		- Confusion matrix.
	- Store all metrics in a Python dict `val_metrics` keyed by metric name.
	- Display a normalized confusion matrix heatmap and a class-wise F1 bar chart as optional diagnostic plots.

- **Test performance evaluation** (Priority: High)

	- Predict class labels (`y_test_pred`) and optionally class probabilities (`y_test_proba`) on the test set.
	- Compute the same metric set as for validation.
	- Store in a dict `test_metrics` using the same schema as `val_metrics`.
	- For the initial template notebook, use the model trained on `X_train` only (Option A) and document the choice clearly.

- **Standardized result packaging and saving** (Priority: High)

	- Build a single result dict with the following top-level keys:
		- `model_name`: value of `MODEL_NAME`.
		- `model_type`: full scikit-learn class name string.
		- `hyperparameters`: dict of model params from `get_params()`.
		- `data`: date range and row count information for all three splits.
		- `class_labels`: `["buy", "hold", "sell"]`.
		- `baseline`: nested `val` and `test` metric dicts.
		- `metrics`: nested `val` and `test` metric dicts.
		- `notes`: label definition, buy/sell thresholds, class weight strategy.
	- Serialize the result dict to a JSON file at `3_evaluate_model/{MODEL_NAME}_metrics.json`.
	- Optionally save test-set predictions (with `symbol`, `date`, `y_true`, `y_pred`) to `3_evaluate_model/{MODEL_NAME}_test_predictions.csv`.
	- Optionally pickle the trained model to `3_evaluate_model/{MODEL_NAME}_model.pkl`.

- **Notebook summary section** (Priority: High)

	- Summarize the chosen model, key hyperparameters, and macro F1 / class-wise metrics for validation and test.
	- Compare results to baseline.
	- Document how to duplicate the notebook for another model.

## 5. User experience

### 5.1 Entry points and first-time user flow

- Open `1-month-direction-classifier/3_evaluate_model/evaluate_model.ipynb`.
- Set `MODEL_NAME` and model configuration in the configuration cell.
- Verify the Parquet input path points to the correct prepared dataset.
- Run all cells top to bottom.
- Review validation and test metrics, confusion matrix plots, and saved artifact paths.

### 5.2 Core experience

- **Configure and import**: User sets `MODEL_NAME` and libraries are loaded in one cell.
	- Ensures the rest of the notebook uses consistent identifiers and paths.
- **Load and validate dataset**: Notebook reads Parquet and confirms schema.
	- Catches schema drift from a re-run of the preparation notebook before training starts.
- **Split data chronologically**: Notebook slices train/validation/test by date with no shuffling.
	- Prevents future information leakage, which would invalidate all reported metrics.
- **Train model in Pipeline**: Notebook fits a leakage-safe Pipeline on training data.
	- Scaling is applied after splitting so validation and test data are never seen during `fit`.
- **Evaluate and compare to baseline**: Notebook reports all metrics and compares against the trivial baseline.
	- Ensures any claimed model lift is measured against a meaningful reference.
- **Save standardized artifacts**: Notebook writes JSON metrics and optional prediction CSV.
	- Enables downstream comparison across all candidate models.

### 5.3 Advanced features and edge cases

- Class imbalance dominated by `hold`: handle via `class_weight` parameter and report balanced accuracy alongside F1.
- Models that do not support `predict_proba` (for example, `LinearSVC`): skip probability output gracefully without error.
- Empty validation or test splits due to unusual date distributions: surface a clear error before attempting evaluation.
- `MODEL_NAME` containing path-unsafe characters: sanitize or document naming constraints.

### 5.4 UI/UX highlights

- Single configuration block at the top of the notebook for all user-facing settings.
- Printed sanity checks after data load, after splitting, and after training.
- Confusion matrix heatmap and class-wise bar chart as inline notebook outputs.
- Clear summary cell at the end stating key numbers and next steps.

## 6. Narrative

The user opens the evaluation notebook template, sets `MODEL_NAME` to `hist_gradient_boosting_baseline`, and runs all cells. The notebook loads the prepared Parquet dataset, confirms schema, drops the small fraction of rows with missing features or labels, and splits the data strictly by calendar date into train, validation, and test. A trivial majority-class baseline is evaluated first to anchor expectations. The chosen model is wrapped in a scikit-learn Pipeline and fitted on training data. Validation metrics reveal macro F1 and per-class performance; a normalized confusion matrix shows where the model confuses `buy` with `hold`. Test metrics confirm whether validation results hold on unseen data. All numbers are serialized to a JSON file named after the model. To evaluate `random_forest_baseline`, the user duplicates the notebook, changes `MODEL_NAME` and the model configuration block, and runs again. A future aggregation step loads every JSON artifact and produces the final comparison table.

## 7. Success metrics

### 7.1 User-centric metrics

- Notebook runs end-to-end without errors on any valid prepared dataset.
- Duplicating the notebook and changing `MODEL_NAME` is sufficient to evaluate a new model with zero other required changes.
- Saved JSON artifact is parseable and contains all required fields without manual post-processing.

### 7.2 Business metrics

- Evaluated models demonstrate measurable macro F1 lift over the trivial baseline on the test set.
- All candidate models are evaluated using identical split dates and metric schemas for fair comparison.

### 7.3 Technical metrics

- Zero data leakage: validation and test data are never seen by any `fit` call.
- Confusion matrix row sums match split class counts.
- JSON artifact passes schema validation against the defined result structure.

## 8. Technical considerations

### 8.1 Integration points

- Input dataset: `1-month-direction-classifier/2_prepare_data/prepared_dataset.parquet`.
- Output metrics JSON: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_metrics.json`.
- Optional output CSV: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_test_predictions.csv`.
- Optional output model pickle: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_model.pkl`.
- All output paths are derived from `MODEL_NAME` so files from different model notebooks never collide.

### 8.2 Data storage and privacy

- Local filesystem storage only.
- No PII in the dataset.
- Pickled model files should be treated as local research artifacts and not shared without review.

### 8.3 Scalability and performance

- Use scikit-learn's `n_jobs=-1` where available to parallelize training on multi-core machines.
- For large universes (S&P 500+, 6 years), expect training times in the range of seconds to a few minutes depending on model.
- Parquet read is fast; no streaming or chunked loading is needed at this data scale.

### 8.4 Potential challenges

- Severe class imbalance (hold dominates): macro F1 may be misleading without balanced accuracy as a cross-check.
- Tree-based models with very deep trees may overfit on training data; document validation vs training F1 gap.
- `TimeSeriesSplit` for tuning (future notebook) requires the combined train+validation set, so split boundary dates must be preserved.
- Serializing numpy types (for example, `int64`, `float32`) to JSON requires a custom encoder or explicit conversion to Python native types.

## 9. Milestones and sequencing

### 9.1 Project estimate

- Small: 2-3 working days

### 9.2 Team size and composition

- 1 person: notebook developer (plus optional peer review)

### 9.3 Suggested phases

- **Phase 1**: Notebook scaffold, configuration, data load, and split (0.5 day)
	- Key deliverables: config cell, Parquet load, schema check, chronological split with sanity checks.
- **Phase 2**: Baseline and model training (0.5 day)
	- Key deliverables: majority-class baseline, Pipeline definition and fit for one candidate model.
- **Phase 3**: Evaluation and artifacts (1 day)
	- Key deliverables: validation metrics, test metrics, confusion matrix plots, JSON save, prediction CSV save.
- **Phase 4**: Summary section and template documentation (0.5 day)
	- Key deliverables: summary cell, duplication instructions, file naming convention documentation.

## 10. User stories

### 10.1 Configure notebook for a single model

- **ID**: GH-001
- **Description**: As a notebook operator, I want a single configuration block where I set `MODEL_NAME` and model hyperparameters so I can adapt the template for any candidate model without editing scattered code.
- **Acceptance criteria**:
	- A dedicated configuration cell at the top defines `MODEL_NAME`, dataset path, output directory, and random seed.
	- Changing `MODEL_NAME` causes all output file names to update automatically.
	- No hardcoded model-specific values appear outside the configuration and model definition cells.

### 10.2 Load and validate the prepared dataset

- **ID**: GH-002
- **Description**: As a user, I want the notebook to load and validate the prepared Parquet dataset so I am confident the input matches expectations before any training begins.
- **Acceptance criteria**:
	- Notebook reads the Parquet file into `df_raw` using the configured path.
	- Presence of all expected raw and engineered feature columns, including `label`, is verified.
	- `date` column dtype is confirmed as datetime.
	- Shape, date range, and unique symbol count are printed.
	- Missing columns raise a descriptive error before any downstream cell runs.

### 10.3 Select features, target, and clean the dataset

- **ID**: GH-003
- **Description**: As a user, I want features and target explicitly separated and rows with invalid labels or missing feature values removed so the model trains on clean data.
- **Acceptance criteria**:
	- Feature list excludes `fwd_ret_20d`, `label`, `symbol`, and `date`.
	- `y` contains only `buy`, `hold`, or `sell` values; rows with other or null labels are dropped.
	- Rows with any NaN in the feature set are dropped.
	- Remaining row count and class distribution are printed.

### 10.4 Split data chronologically without shuffling

- **ID**: GH-004
- **Description**: As a user, I want a strictly time-aware train/validation/test split so no future information leaks into training.
- **Acceptance criteria**:
	- Dataset is sorted by `date` before splitting.
	- Splits are determined by calendar date: ~70% train, ~15% validation, ~15% test.
	- Actual boundary dates are stored in named variables and printed.
	- No `date` value appears in more than one split.
	- Row counts and class distributions are logged for each split.

### 10.5 Evaluate a trivial baseline classifier

- **ID**: GH-005
- **Description**: As a user, I want a simple baseline evaluated on both validation and test sets so I can measure genuine model lift.
- **Acceptance criteria**:
	- Baseline is defined using training data only (for example, majority-class predictor).
	- Macro F1, weighted F1, balanced accuracy, per-class precision/recall/F1, and confusion matrix are computed for both validation and test.
	- Results are stored in `baseline_results` using the same schema as model results.

### 10.6 Define and train the candidate model in a Pipeline

- **ID**: GH-006
- **Description**: As a user, I want the model and any preprocessing encapsulated in a scikit-learn Pipeline so preprocessing is leakage-safe and the notebook is reproducible.
- **Acceptance criteria**:
	- Model class, key hyperparameters, and class weight strategy are documented in the model configuration cell.
	- `StandardScaler` is included in the Pipeline only for models that require scaling.
	- Pipeline is fitted on `X_train` and `y_train` only.
	- Training duration is recorded and printed.

### 10.7 Evaluate model performance on the validation set

- **ID**: GH-007
- **Description**: As a user, I want comprehensive validation metrics displayed so I can assess model quality before committing to the test set evaluation.
- **Acceptance criteria**:
	- `y_val_pred` is produced via `pipeline.predict(X_val)`.
	- Computed metrics include macro F1, weighted F1, balanced accuracy, and per-class precision/recall/F1.
	- Confusion matrix is computed and displayed as a normalized heatmap.
	- All metrics are stored in `val_metrics` dict.

### 10.8 Evaluate model performance on the hold-out test set

- **ID**: GH-008
- **Description**: As a user, I want final test-set metrics evaluated so the notebook produces an honest out-of-sample performance estimate.
- **Acceptance criteria**:
	- Test set is not used until after all configuration and hyperparameter decisions are finalized.
	- The same metric set as validation is computed and stored in `test_metrics`.
	- Which training data variant was used for the final fit (train only vs train+val) is documented.

### 10.9 Save standardized evaluation artifacts

- **ID**: GH-009
- **Description**: As a user, I want all results saved in a consistent, machine-readable format so a downstream comparison step can load results from all model notebooks without custom parsing.
- **Acceptance criteria**:
	- A result dict is built containing `model_name`, `model_type`, `hyperparameters`, `data`, `class_labels`, `baseline`, `metrics`, and `notes` keys.
	- Result dict is serialized to `3_evaluate_model/{MODEL_NAME}_metrics.json` with Python-native numeric types (no numpy types).
	- Optional test prediction CSV is saved to `3_evaluate_model/{MODEL_NAME}_test_predictions.csv` with `symbol`, `date`, `y_true`, and `y_pred` columns.
	- Optional model pickle is saved to `3_evaluate_model/{MODEL_NAME}_model.pkl`.

### 10.10 Provide a notebook summary and template guidance

- **ID**: GH-010
- **Description**: As a user, I want a final summary cell that recaps key metrics and documents how to duplicate the notebook for a different model so the template is self-explanatory.
- **Acceptance criteria**:
	- Summary cell states chosen model, key hyperparameters, macro F1 and buy/sell F1 for validation and test.
	- Summary states whether the model beats the baseline and by how much.
	- Instructions for creating a new model notebook (duplicate, change model class + `MODEL_NAME`) are present.

### 10.11 Ensure no data leakage across splits

- **ID**: GH-011
- **Description**: As a maintainer, I want explicit guardrails confirming that the validation and test sets are never used during any fitting step so reported metrics are trustworthy.
- **Acceptance criteria**:
	- `StandardScaler.fit` (when used) is called only on training data.
	- `pipeline.fit` is called only with training data.
	- A sanity check cell confirms no date overlap between splits and prints confirmation.
	- Any future refit on train+val is documented as a deliberate post-selection step.

## 11. Standardized result schema

### 11.1 Result dictionary structure

The following top-level keys are required in the result dict written to `{MODEL_NAME}_metrics.json`:

- **model_name**: String matching `MODEL_NAME` configuration variable.
- **model_type**: Full scikit-learn class path string (for example, `sklearn.ensemble.HistGradientBoostingClassifier`).
- **hyperparameters**: Dict returned by `model.get_params()` (Python-native types only).
- **data**: Dict with `train_start`, `train_end`, `val_start`, `val_end`, `test_start`, `test_end`, `n_train`, `n_val`, `n_test` keys.
- **class_labels**: Fixed list `["buy", "hold", "sell"]`.
- **baseline**: Dict with `val` and `test` keys, each containing the full metric set.
- **metrics**: Dict with `val` and `test` keys, each containing the full metric set.
- **notes**: Dict with `threshold_buy`, `threshold_sell`, `label_definition`, and `class_weight_strategy` keys.

### 11.2 Metric set schema (per split)

Each metric set (validation or test) must contain:

- **macro_f1**: Macro-averaged F1 score.
- **weighted_f1**: Weighted-averaged F1 score.
- **balanced_accuracy**: Balanced accuracy score.
- **per_class**: Nested dict keyed by `buy`, `hold`, `sell`, each with `precision`, `recall`, and `f1` keys.
- **confusion_matrix**: 2D list of integer counts (row = true label, column = predicted label, order matching `class_labels`).

### 11.3 File naming convention

- JSON metrics: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_metrics.json`
- Test predictions CSV: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_test_predictions.csv`
- Model pickle: `1-month-direction-classifier/3_evaluate_model/{MODEL_NAME}_model.pkl`
