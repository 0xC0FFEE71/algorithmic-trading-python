# PRD: 1-Month Direction Model Selection Notebook

## 1. Product overview

### 1.1 Document title and version

- PRD: 1-Month Direction Model Selection Notebook
- Version: 1.0

### 1.2 Product summary

This project defines a pure comparison-and-decision Jupyter notebook that consumes six standardized evaluation JSON files and produces a compact model leaderboard for the one-month direction classifier with buy, hold, and sell classes. The notebook does not train models and does not run hyperparameter search. Its purpose is to compare baseline results consistently, identify promising candidates for a separate tuning notebook, and provide a provisional production recommendation.

The notebook will load all baseline metrics artifacts from 3_evaluate_model, validate schema consistency, normalize model metrics into a single table, and apply explicit selection logic based on validation macro F1 first, with test macro F1 and action-class guardrails used as risk controls. It will also produce structured outputs in 4_select_model for downstream tuning and final model-selection workflows.

At the current project state, all six existing model JSON files are treated as baseline by default. A model is only considered already tuned when it is the output of a documented and systematic model-selection process, such as TimeSeriesSplit with GridSearchCV or RandomizedSearchCV, followed by final re-evaluation and artifact save.

## 2. Goals

### 2.1 Business goals

- Create a repeatable and transparent model leaderboard process.
- Reduce subjective model choice by using explicit decision rules.
- Narrow six baseline models to one to three tuning candidates efficiently.
- Produce machine-readable comparison artifacts for downstream automation.

### 2.2 User goals

- Run one notebook that compares all model JSONs in one pass.
- Understand which models underperform overall or on buy and sell classes.
- Identify candidate models for focused tuning with clear rationale.
- See a provisional production candidate while acknowledging baseline status.

### 2.3 Non-goals

- Model fitting, retraining, or inference generation.
- Hyperparameter optimization execution.
- Data preparation or feature engineering changes.
- Final production promotion of untuned baseline models.

## 3. User personas

### 3.1 Key user types

- Quant researcher
- Retail systematic trader
- ML engineer supporting notebook-based experimentation

### 3.2 Basic persona details

- Quant researcher: needs defensible model comparison before spending compute on tuning.
- Retail systematic trader: needs practical guardrails so action classes are not ignored.
- ML engineer: needs structured outputs that feed a separate tuning notebook and audit trail.

### 3.3 Role-based access

- Notebook operator: can run comparison notebook, read metrics JSON files, and write outputs to 4_select_model.
- Project maintainer: can modify thresholds, ranking logic, and tuning recommendation presets.

## 4. Functional requirements

- Notebook setup and scope statement (Priority: High)
  - Add an opening markdown section that explains the notebook only compares and decides, without training.
  - State outputs: leaderboard tables, tuning recommendations, comparison JSON, and CSV leaderboard.

- Configuration block (Priority: High)
  - Support either explicit list of six JSON paths or directory plus glob pattern.
  - Define primary metric policy: validation macro F1 as primary, test macro F1 as guardrail.
  - Define hard action-class thresholds:
  - test_f1_buy greater than or equal to 0.20.
  - test_f1_sell greater than or equal to 0.15.
  - Define optional recall thresholds:
  - test_recall_buy greater than or equal to 0.18.
  - test_recall_sell greater than or equal to 0.13.
  - Define output directory as 4_select_model.

- Metrics ingestion and schema checks (Priority: High)
  - Load six JSON files into Python objects.
  - Validate required keys for each file: model_name, model_type, hyperparameters, data, baseline, metrics, notes.
  - Validate nested keys for validation and test metrics, including per-class metrics.
  - Fail fast with a clear error report if files are missing required keys.

- Leaderboard normalization (Priority: High)
  - Flatten each model artifact into one row in a pandas DataFrame.
  - Include validation and test columns for macro F1, weighted F1, balanced accuracy.
  - Include class-wise F1 and recall for buy, hold, sell.
  - Include metadata fields such as model_name, model_type, class_weight_strategy, and baseline versus tuned flags.

- Validation and test summary tables (Priority: High)
  - Build a validation summary table with core metrics and class-wise buy and sell F1.
  - Build a test summary table with the same structure.
  - Add rank columns for validation macro F1 and test macro F1.

- Overfitting and stability checks (Priority: High)
  - Compute validation-to-test drop metrics for macro F1 and buy and sell F1.
  - Flag potential instability when validation is materially stronger than test.
  - Surface these flags in the leaderboard output.

- Action-class viability checks (Priority: High)
  - Evaluate each model against hard minimum buy and sell F1 thresholds.
  - Evaluate optional buy and sell recall thresholds.
  - Add boolean eligibility columns and a compact reason code field for failed checks.

- Decision logic for tuning and provisional production (Priority: High)
  - Define is_baseline using the practical rule: manually chosen configuration without systematic search.
  - Define already_tuned only when produced by documented systematic search and final re-evaluation.
  - Mark all six current JSONs as baseline by default.
  - If no model is clearly dominant, select one to three tuning candidates using validation-first ranking constrained by action-class viability.
  - If one model is clearly superior on validation and acceptable on test guardrails, mark it as provisional production candidate.

- Tuning recommendation generator (Priority: High)
  - Provide model-type-specific parameter spaces.
  - Provide configurable search budget presets: small, medium, large.
  - Combine model space and budget preset into concrete RandomizedSearchCV or GridSearchCV suggestions.
  - Recommend TimeSeriesSplit with four to five folds on train plus validation data in the future tuning notebook.

- Baseline versus tuned governance section (Priority: Medium)
  - Add explicit markdown guidance distinguishing baseline artifacts from tuned artifacts.
  - State current status: all six artifacts are baseline runs and not final production approvals.

- Production selection policy specification (Priority: Medium)
  - Record post-tuning production criteria:
  - maximize test macro F1.
  - enforce minimum test buy and sell F1.
  - require validation-test stability.
  - use simplicity, training time, and inference cost as secondary criteria.

- Artifact outputs (Priority: High)
  - Save leaderboard CSV to 4_select_model/model_leaderboard_baselines.csv.
  - Save comparison JSON to 4_select_model/model_comparison_baselines.json.
  - Ensure comparison JSON includes models, ranks, candidate lists, selection rules, and notes.

## 5. User experience

### 5.1 Entry points and first-time user flow

- Open the selection notebook in 4_select_model.
- Confirm input JSON source path and output directory.
- Configure thresholds and budget preset.
- Run all cells in order.
- Review validation and test leaderboards, then decision markdown output.

### 5.2 Core experience

- Load and validate all model artifacts: catches schema drift and missing fields before analysis.
- Build unified leaderboard table: gives one-row-per-model comparison.
- Rank by validation macro F1 with test guardrails: aligns with validation-first strategy and robustness checks.
- Check buy and sell class viability: avoids selecting models that only perform on hold.
- Produce explicit decision: lists tuning candidates and provisional production candidate with reasons.
- Export JSON and CSV outputs: enables downstream automation and reproducibility.

### 5.3 Advanced features and edge cases

- Missing model files or malformed JSON structures.
- Metrics present but missing per-class buy or sell keys.
- Ties in validation macro F1 resolved by test macro F1 then balanced accuracy.
- Severe class imbalance where hold dominates weighted metrics.
- Optional recall thresholds toggled on or off for early experimentation.

### 5.4 UI/UX highlights

- Clear markdown rationale after each table.
- Side-by-side validation and test ranking views.
- Action-class eligibility badges or boolean columns.
- Final decision section written as a mini-spec for the next tuning notebook.

## 6. Narrative

The user runs one notebook that reads six standardized baseline metric files and converts them into a leaderboard. The notebook ranks models by validation macro F1, checks test metrics for guardrail violations, and verifies buy and sell class viability using lenient but practical thresholds. It then narrows the field to tuning candidates and records a provisional production candidate, while clearly marking that all current artifacts are baseline runs. Finally, it writes both a CSV leaderboard and a structured comparison JSON in 4_select_model so tuning and future final model selection can follow a consistent, auditable process.

## 7. Success metrics

### 7.1 User-centric metrics

- User can run comparison notebook end-to-end without editing core code.
- User receives one explicit shortlist of tuning candidates with reasons.
- User receives one provisional production candidate with caveats.

### 7.2 Business metrics

- Reduced time to select tuning targets from six models to one to three.
- Increased consistency of model-selection decisions across runs.
- Better traceability of why a model was or was not selected.

### 7.3 Technical metrics

- 100 percent of loaded artifacts pass required schema checks.
- Leaderboard exports generated on every successful run in CSV and JSON formats.
- Decision logic fields present for every model: ranks, eligibility, baseline versus tuned status.

## 8. Technical considerations

### 8.1 Integration points

- Input metrics source: 1-month-direction-classifier/3_evaluate_model.
- Notebook location: 1-month-direction-classifier/4_select_model.
- Output JSON: 1-month-direction-classifier/4_select_model/model_comparison_baselines.json.
- Output CSV: 1-month-direction-classifier/4_select_model/model_leaderboard_baselines.csv.
- Downstream dependency: tuning notebook consumes comparison JSON candidate list and parameter recommendations.

### 8.2 Data storage and privacy

- Local files only; no external data transfer required.
- No personal data expected in metrics artifacts.
- Avoid storing sensitive environment data in output metadata.

### 8.3 Scalability and performance

- Current design targets six to twenty model artifacts with low runtime overhead.
- Flattening and ranking should run in seconds on standard notebook environments.
- Logic should remain robust if additional future model JSON files are added.

### 8.4 Potential challenges

- Inconsistent JSON schema across future evaluation notebooks.
- Misleading aggregate metrics under class imbalance.
- Threshold brittleness when market regime changes shift class frequencies.
- Ambiguity in declaring tuned status without documented search metadata.

## 9. Milestones and sequencing

### 9.1 Project estimate

- Small: 1-2 working days

### 9.2 Team size and composition

- 1 person: notebook developer
- Optional reviewer: quant or ML peer for threshold validation

### 9.3 Suggested phases

- Phase 1: Notebook scaffold and config policy (0.25-0.5 day)
  - Key deliverables: intro, paths, thresholds, budget presets.
- Phase 2: JSON loading and leaderboard normalization (0.5 day)
  - Key deliverables: schema validation, flat DataFrame, validation and test summary tables.
- Phase 3: Decision logic and recommendation generation (0.5 day)
  - Key deliverables: eligibility flags, candidate selection, tuning mini-spec output.
- Phase 4: Export artifacts and polish (0.25-0.5 day)
  - Key deliverables: CSV and JSON exports, final markdown interpretation.

## 10. User stories

### 10.1 Configure model artifact inputs

- ID: GH-401
- Description: As a notebook operator, I want to configure the source of model metrics files so that I can compare exactly the models I intend to analyze.
- Acceptance criteria:
  - User can provide either explicit file paths or directory plus pattern.
  - Notebook validates that exactly six baseline files are found for the current phase.
  - Missing files generate actionable error messages.

### 10.2 Validate metrics artifact schema

- ID: GH-402
- Description: As a notebook operator, I want strict schema checks so that comparison logic is not run on malformed artifacts.
- Acceptance criteria:
  - Required top-level keys are validated for each JSON.
  - Required nested metric keys for validation and test are validated.
  - Notebook stops with a summary of schema violations.

### 10.3 Build unified leaderboard DataFrame

- ID: GH-403
- Description: As a user, I want one normalized table with one row per model so that I can compare models quickly.
- Acceptance criteria:
  - DataFrame includes overall and class-wise metrics for validation and test.
  - DataFrame includes model metadata and notes fields.
  - One row is produced for every valid input model artifact.

### 10.4 Rank models by validation-first policy

- ID: GH-404
- Description: As a user, I want ranks based on validation macro F1 and test guardrails so that model choice is aligned with robust selection logic.
- Acceptance criteria:
  - rank_val_macro_f1 is computed in descending order.
  - rank_test_macro_f1 is also computed for guardrail context.
  - Tie-break logic is applied consistently and documented.

### 10.5 Detect validation-test instability

- ID: GH-405
- Description: As a user, I want overfitting and instability indicators so that I avoid fragile models.
- Acceptance criteria:
  - Validation-test metric deltas are computed per model.
  - Models exceeding configured delta threshold are flagged.
  - Flags are visible in summary outputs and saved artifacts.

### 10.6 Enforce action-class hard minimums

- ID: GH-406
- Description: As a user, I want buy and sell minimum F1 thresholds so that selected candidates are usable for action classes.
- Acceptance criteria:
  - test_f1_buy threshold of 0.20 is applied.
  - test_f1_sell threshold of 0.15 is applied.
  - Eligibility pass or fail and reasons are recorded per model.

### 10.7 Apply optional action-class recall guardrails

- ID: GH-407
- Description: As a user, I want optional recall checks for buy and sell so that I can increase strictness when needed.
- Acceptance criteria:
  - Optional test_recall_buy threshold of 0.18 can be enabled.
  - Optional test_recall_sell threshold of 0.13 can be enabled.
  - Notebook clearly indicates whether optional recall filtering is active.

### 10.8 Label baseline versus tuned status

- ID: GH-408
- Description: As a project maintainer, I want explicit baseline and tuned definitions so that model status reflects process quality, not only hyperparameter defaults.
- Acceptance criteria:
  - is_baseline and already_tuned fields are generated for all models.
  - Current six model artifacts are marked baseline by default.
  - already_tuned requires documented systematic search and final re-evaluation evidence.

### 10.9 Select tuning candidates

- ID: GH-409
- Description: As a user, I want an explicit shortlist of one to three models for further tuning so that experimentation remains focused.
- Acceptance criteria:
  - Candidate selection prioritizes validation macro F1 among eligible models.
  - Candidate list includes rationale fields and ranking context.
  - Candidate count and selection rules are stored in output JSON.

### 10.10 Assign provisional production candidate

- ID: GH-410
- Description: As a user, I want one provisional production candidate from current baselines so that there is a clear temporary default while tuning is pending.
- Acceptance criteria:
  - Exactly one provisional candidate is identified when at least one model passes hard filters.
  - Candidate selection is documented as provisional until tuning completion.
  - If no model passes filters, notebook records no provisional candidate with explanation.

### 10.11 Generate budget-based tuning mini-spec

- ID: GH-411
- Description: As a user, I want model-specific tuning suggestions with small, medium, and large budgets so that I can choose search depth based on time.
- Acceptance criteria:
  - Parameter spaces are defined by model type.
  - Budget preset controls search width and trial count.
  - Recommendation includes TimeSeriesSplit folds, scoring metric, and search method.

### 10.12 Export comparison JSON and leaderboard CSV

- ID: GH-412
- Description: As a user, I want machine-readable outputs so that downstream notebooks and reports can reuse selection results.
- Acceptance criteria:
  - CSV leaderboard is saved to 4_select_model/model_leaderboard_baselines.csv.
  - JSON comparison is saved to 4_select_model/model_comparison_baselines.json.
  - Exported files include model ranks, filters, decisions, and selection rules.

### 10.13 Protect local artifact integrity and path safety

- ID: GH-413
- Description: As a maintainer, I want safe file handling so that the notebook reads and writes only intended project paths.
- Acceptance criteria:
  - Input file paths are resolved and constrained to project directories.
  - Output paths are constrained to 4_select_model.
  - Notebook does not execute untrusted code or deserialize arbitrary objects during comparison.