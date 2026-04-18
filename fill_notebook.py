import json, sys

NB_PATH = sys.argv[1]

# cell index (0-based) -> source lines
CELLS = {
    2: r"""import warnings
import logging
import math
import json
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import pyarrow  # noqa: F401
    _PARQUET_ENGINE = "pyarrow"
except ImportError:
    try:
        import fastparquet  # noqa: F401
        _PARQUET_ENGINE = "fastparquet"
    except ImportError:
        raise ImportError(
            "Parquet I/O requires 'pyarrow' or 'fastparquet'. "
            "Install with: pip install pyarrow"
        )

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=FutureWarning)
pd.options.display.float_format = "{:.6f}".format

print(f"pandas {pd.__version__} | numpy {np.__version__} | Parquet engine: {_PARQUET_ENGINE}")
""",

    4: r"""# ── User-configurable variables ───────────────────────────────────────────────
UNIVERSE_CSV_NAME             = "DEMO_003"   # stem of the universe file
LOOKBACK_YEARS                = 6
MIN_HISTORY_DAYS              = 252
MAX_MISSING_FRAC_PER_SYMBOL   = 0.05
ROW_MISSING_POLICY            = "drop"       # "drop" | "ffill_selected"
MIN_MEDIAN_VALUE_TRADED_20D   = 1_000_000
NEAR_CONSTANT_STD_THRESHOLD   = 1e-8
DROP_NEAR_CONSTANT_FEATURES   = True
SAVE_PARQUET                  = True
SAVE_CSV                      = False
OUTPUT_BASENAME               = "prepared_dataset"

# ── Derived filesystem paths ───────────────────────────────────────────────────
try:
    NOTEBOOK_DIR = Path(__file__).parent.resolve()
except NameError:
    NOTEBOOK_DIR = Path.cwd().resolve()

BASE_DIR          = NOTEBOOK_DIR.parent
DATA_DIR          = BASE_DIR / "data"
UNIVERSE_CSV_PATH = DATA_DIR / f"{UNIVERSE_CSV_NAME}.csv"
SYMBOL_DATA_DIR   = DATA_DIR / UNIVERSE_CSV_NAME
OUTPUT_DIR        = NOTEBOOK_DIR

# ── Stage-level audit counters ────────────────────────────────────────────────
stage_counts: dict = {}

print(f"Universe CSV  : {UNIVERSE_CSV_PATH}")
print(f"Symbol data   : {SYMBOL_DATA_DIR}")
print(f"Output dir    : {OUTPUT_DIR}")
""",

    6: r"""if not UNIVERSE_CSV_PATH.exists():
    raise FileNotFoundError(
        f"Universe file not found at resolved path: {UNIVERSE_CSV_PATH.resolve()}"
    )

df_universe_raw = pd.read_csv(UNIVERSE_CSV_PATH)

if "Symbol" not in df_universe_raw.columns:
    raise ValueError(
        f"Mandatory 'Symbol' column not found. "
        f"Columns present: {list(df_universe_raw.columns)}"
    )

stage_counts["raw_universe"] = {"symbols": len(df_universe_raw), "rows": None}

print(f"Raw universe entries: {len(df_universe_raw)}")
display(df_universe_raw.head())
""",

    8: r"""exclusion_log: list[dict] = []

symbols_raw = df_universe_raw["Symbol"].copy()

# Strip whitespace
symbols_stripped = symbols_raw.str.strip()

# Remove null / empty symbols
null_mask  = symbols_stripped.isna() | (symbols_stripped == "")
null_count = int(null_mask.sum())
if null_count:
    logger.warning(f"Removing {null_count} null/empty symbol(s).")
    for sym in symbols_stripped[null_mask]:
        exclusion_log.append({"symbol": str(sym), "reason": "empty_symbol"})
symbols_clean = symbols_stripped[~null_mask].reset_index(drop=True)

# Remove duplicates (keep first)
dup_mask  = symbols_clean.duplicated(keep="first")
dup_count = int(dup_mask.sum())
if dup_count:
    logger.warning(f"Removing {dup_count} duplicate symbol(s): {list(symbols_clean[dup_mask])}")

symbol_list: list[str] = symbols_clean[~dup_mask].tolist()

stage_counts["after_symbol_normalisation"] = {"symbols": len(symbol_list), "rows": None}

print(f"Symbols before normalisation : {len(symbols_raw)}")
print(f"Symbols after  normalisation : {len(symbol_list)}")
print(f"  excluded (null/empty)      : {null_count}")
print(f"  excluded (duplicates)      : {dup_count}")
""",

    10: r"""valid_symbols: list[str] = []

for sym in symbol_list:
    fpath = SYMBOL_DATA_DIR / f"{sym}.csv"
    if fpath.exists():
        valid_symbols.append(sym)
    else:
        exclusion_log.append({"symbol": sym, "reason": "file_not_found"})
        logger.warning(f"File not found for {sym}: {fpath}")

stage_counts["after_file_resolution"] = {"symbols": len(valid_symbols), "rows": None}

print(f"Total symbols  : {len(symbol_list)}")
print(f"Files found    : {len(valid_symbols)}")
print(f"Files missing  : {len(symbol_list) - len(valid_symbols)}")
""",

    12: r"""REQUIRED_COLS  = ["date", "open", "high", "low", "close", "adj_close", "volume"]
COL_RENAME_MAP = {"adjusted_close": "adj_close"}

raw_frames: list[pd.DataFrame] = []
_passed_symbols: list[str] = []

for sym in valid_symbols:
    fpath = SYMBOL_DATA_DIR / f"{sym}.csv"

    try:
        df = pd.read_csv(fpath)
    except Exception as exc:
        exclusion_log.append({"symbol": sym, "reason": "schema_mismatch"})
        logger.warning(f"{sym}: Failed to read CSV — {exc}")
        continue

    # Normalise column names
    df.columns = [c.strip().lower() for c in df.columns]
    df.rename(columns=COL_RENAME_MAP, inplace=True)

    # Schema check
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        exclusion_log.append({"symbol": sym, "reason": "schema_mismatch"})
        logger.warning(f"{sym}: Missing columns {missing_cols}. Found: {list(df.columns)}")
        continue

    # Date parsing
    try:
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        exclusion_log.append({"symbol": sym, "reason": "date_parse_failure"})
        logger.warning(f"{sym}: Date parsing failed.")
        continue

    # Sort ascending by date
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Trim to LOOKBACK_YEARS from latest available date
    latest_date = df["date"].max()
    cutoff_date = latest_date - pd.DateOffset(years=LOOKBACK_YEARS)
    df = df[df["date"] >= cutoff_date].copy()
    df.reset_index(drop=True, inplace=True)

    df.insert(0, "symbol", sym)
    raw_frames.append(df)
    _passed_symbols.append(sym)

valid_symbols = _passed_symbols
total_rows_raw = sum(len(df) for df in raw_frames)
stage_counts["after_schema_date_checks"] = {"symbols": len(valid_symbols), "rows": total_rows_raw}

print(f"Symbols passed schema/date checks : {len(valid_symbols)}")
print(f"Total rows loaded                 : {total_rows_raw:,}")
""",

    14: r"""dup_summary: dict[str, int] = {}
cleaned_frames: list[pd.DataFrame] = []

for df in raw_frames:
    sym   = df["symbol"].iloc[0]
    n_dup = int(df.duplicated(subset=["symbol", "date"]).sum())
    if n_dup:
        dup_summary[sym] = n_dup
        logger.warning(f"{sym}: {n_dup} duplicate (symbol, date) row(s) removed.")
    df = df.drop_duplicates(subset=["symbol", "date"], keep="first").reset_index(drop=True)
    cleaned_frames.append(df)

raw_frames = cleaned_frames

if dup_summary:
    print("Duplicates removed per symbol:")
    for sym, cnt in dup_summary.items():
        print(f"  {sym}: {cnt}")
else:
    print("No duplicate (symbol, date) rows found.")
""",

    16: r"""passed_frames: list[pd.DataFrame] = []

for df in raw_frames:
    sym = df["symbol"].iloc[0]
    if not df["date"].is_monotonic_increasing:
        exclusion_log.append({"symbol": sym, "reason": "non_monotonic_dates"})
        logger.warning(f"{sym}: Non-monotonic dates — excluded.")
    else:
        passed_frames.append(df)

raw_frames = passed_frames
print(f"Symbols after monotonic-date check: {len(raw_frames)}")
""",

    18: r"""PRICE_VOL_COLS = ["open", "high", "low", "close", "adj_close", "volume"]
neg_summary: dict[str, int] = {}
cleaned_frames = []

for df in raw_frames:
    sym      = df["symbol"].iloc[0]
    neg_mask = (df[PRICE_VOL_COLS] < 0).any(axis=1)
    n_neg    = int(neg_mask.sum())

    if n_neg:
        neg_summary[sym] = n_neg
        logger.warning(f"{sym}: {n_neg} row(s) with negative price/volume — treated as NaN.")
        df = df.copy()
        df.loc[neg_mask, PRICE_VOL_COLS] = np.nan

    if ROW_MISSING_POLICY == "drop":
        df = df.dropna(subset=PRICE_VOL_COLS).reset_index(drop=True)
    elif ROW_MISSING_POLICY == "ffill_selected":
        df[PRICE_VOL_COLS] = df[PRICE_VOL_COLS].ffill()
        df = df.dropna(subset=PRICE_VOL_COLS).reset_index(drop=True)

    cleaned_frames.append(df)

raw_frames = cleaned_frames

if neg_summary:
    print("Rows with negative values per symbol:")
    for sym, cnt in neg_summary.items():
        print(f"  {sym}: {cnt}")
else:
    print("No negative price/volume values detected.")
""",

    20: r"""required_non_date = [c for c in REQUIRED_COLS if c != "date"]
passed_frames     = []
missing_report: list[dict] = []

for df in raw_frames:
    sym           = df["symbol"].iloc[0]
    total_cells   = df[required_non_date].size
    missing_cells = int(df[required_non_date].isna().sum().sum())
    missing_frac  = missing_cells / total_cells if total_cells else 0.0
    missing_report.append({"symbol": sym, "missing_frac": round(missing_frac, 6)})

    if missing_frac > MAX_MISSING_FRAC_PER_SYMBOL:
        exclusion_log.append({"symbol": sym, "reason": "excessive_missing"})
        logger.warning(
            f"{sym}: Missing fraction {missing_frac:.2%} exceeds threshold "
            f"{MAX_MISSING_FRAC_PER_SYMBOL:.2%} — excluded."
        )
        continue

    df = df.copy()
    if ROW_MISSING_POLICY == "drop":
        df = df.dropna(subset=required_non_date).reset_index(drop=True)
    elif ROW_MISSING_POLICY == "ffill_selected":
        df[required_non_date] = df[required_non_date].ffill()
        df = df.dropna(subset=required_non_date).reset_index(drop=True)

    passed_frames.append(df)

raw_frames = passed_frames

print(f"Symbols after missing-value policy: {len(raw_frames)}")
print()
print(pd.DataFrame(missing_report).to_string(index=False))
""",

    22: r"""passed_frames = []

for df in raw_frames:
    sym    = df["symbol"].iloc[0]
    n_rows = len(df)
    if n_rows < MIN_HISTORY_DAYS:
        exclusion_log.append({"symbol": sym, "reason": "insufficient_history"})
        logger.warning(
            f"{sym}: {n_rows} rows < minimum {MIN_HISTORY_DAYS} — excluded."
        )
    else:
        passed_frames.append(df)

raw_frames = passed_frames
total_rows_qf = sum(len(df) for df in raw_frames)
stage_counts["after_quality_filtering"] = {"symbols": len(raw_frames), "rows": total_rows_qf}

print(f"Symbols after minimum history filter : {len(raw_frames)}")
print(f"Total rows                           : {total_rows_qf:,}")
""",

    24: r"""passed_frames = []

for df in raw_frames:
    sym            = df["symbol"].iloc[0]
    value_traded   = df["close"] * df["volume"]
    rolling_med_20 = value_traded.rolling(window=20, min_periods=1).median()
    overall_median = float(rolling_med_20.median())

    if overall_median < MIN_MEDIAN_VALUE_TRADED_20D:
        exclusion_log.append({"symbol": sym, "reason": "low_liquidity"})
        logger.warning(
            f"{sym}: Median 20-day value traded {overall_median:,.0f} "
            f"< threshold {MIN_MEDIAN_VALUE_TRADED_20D:,} — excluded."
        )
    else:
        passed_frames.append(df)

raw_frames = passed_frames
print(f"Symbols after liquidity filter: {len(raw_frames)}")
""",

    26: r"""for i, df in enumerate(raw_frames):
    c = df["close"]
    df["ret_1d"]      = c / c.shift(1)  - 1
    df["log_ret_1d"]  = np.log(c / c.shift(1))
    df["ret_5d"]      = c / c.shift(5)  - 1
    df["ret_10d"]     = c / c.shift(10) - 1
    df["ret_20d"]     = c / c.shift(20) - 1
    df["ret_60d"]     = c / c.shift(60) - 1
    df["log_ret_5d"]  = np.log(c / c.shift(5))
    df["log_ret_20d"] = np.log(c / c.shift(20))
    raw_frames[i] = df

print("Return features computed.")
""",

    28: r"""for i, df in enumerate(raw_frames):
    prev_close       = df["close"].shift(1)
    df["tr_range"]   = df["high"] - df["low"]
    df["true_range"] = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"]  - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    raw_frames[i] = df

print("Intraday range features computed.")
""",

    30: r"""for i, df in enumerate(raw_frames):
    c = df["close"]
    df["sma_5"]   = c.rolling(5).mean()
    df["sma_20"]  = c.rolling(20).mean()
    df["sma_50"]  = c.rolling(50).mean()
    df["sma_200"] = c.rolling(200).mean()

    df["close_over_sma_20"]  = c / df["sma_20"]
    df["close_over_sma_50"]  = c / df["sma_50"]
    df["close_over_sma_200"] = c / df["sma_200"]

    df["sma_20_slope_5d"] = df["sma_20"] / df["sma_20"].shift(5) - 1
    df["sma_50_slope_5d"] = df["sma_50"] / df["sma_50"].shift(5) - 1
    raw_frames[i] = df

print("Trend / moving-average features computed.")
""",

    32: r"""for i, df in enumerate(raw_frames):
    df["vol_ret_5d"]  = df["ret_1d"].rolling(5).std()
    df["vol_ret_20d"] = df["ret_1d"].rolling(20).std()
    df["vol_ret_60d"] = df["ret_1d"].rolling(60).std()
    df["vol_tr_5d"]   = df["true_range"].rolling(5).std()
    df["vol_tr_20d"]  = df["true_range"].rolling(20).std()
    raw_frames[i] = df

print("Volatility features computed.")
""",

    34: r"""for i, df in enumerate(raw_frames):
    df["value_traded"]        = df["close"] * df["volume"]
    df["vol_ma_20"]           = df["volume"].rolling(20).mean()
    df["vol_ma_60"]           = df["volume"].rolling(60).mean()
    df["vol_rel_20"]          = df["volume"] / df["vol_ma_20"]
    df["value_traded_ma_20"]  = df["value_traded"].rolling(20).mean()
    df["value_traded_rel_20"] = df["value_traded"] / df["value_traded_ma_20"]
    raw_frames[i] = df

print("Volume and liquidity features computed.")
""",

    36: r"""_WILDER_ALPHA = 1 / 14

for i, df in enumerate(raw_frames):
    c = df["close"]

    # RSI-14 (Wilder smoothing)
    delta    = c.diff()
    gains    = delta.clip(lower=0)
    losses   = (-delta).clip(lower=0)
    avg_gain = gains.ewm(alpha=_WILDER_ALPHA, min_periods=14, adjust=False).mean()
    avg_loss = losses.ewm(alpha=_WILDER_ALPHA, min_periods=14, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # MACD
    ema12             = c.ewm(span=12, adjust=False).mean()
    ema26             = c.ewm(span=26, adjust=False).mean()
    df["macd"]        = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]   = df["macd"] - df["macd_signal"]

    # ATR-14 (Wilder smoothing)
    df["atr_14"] = df["true_range"].ewm(
        alpha=_WILDER_ALPHA, min_periods=14, adjust=False
    ).mean()

    raw_frames[i] = df

print("Technical indicator features computed.")
""",

    38: r"""for i, df in enumerate(raw_frames):
    df["hh_20d"]             = df["high"].rolling(20).max()
    df["ll_20d"]             = df["low"].rolling(20).min()
    df["dist_from_20d_high"] = (df["close"] / df["hh_20d"]) - 1
    df["dist_from_20d_low"]  = (df["close"] / df["ll_20d"]) - 1
    raw_frames[i] = df

print("High/low context features computed.")
""",

    40: r"""FEATURE_COLS: list[str] = [
    "ret_1d", "log_ret_1d", "ret_5d", "ret_10d", "ret_20d", "ret_60d",
    "log_ret_5d", "log_ret_20d",
    "tr_range", "true_range",
    "sma_5", "sma_20", "sma_50", "sma_200",
    "close_over_sma_20", "close_over_sma_50", "close_over_sma_200",
    "sma_20_slope_5d", "sma_50_slope_5d",
    "vol_ret_5d", "vol_ret_20d", "vol_ret_60d", "vol_tr_5d", "vol_tr_20d",
    "value_traded", "vol_ma_20", "vol_ma_60", "vol_rel_20",
    "value_traded_ma_20", "value_traded_rel_20",
    "rsi_14", "macd", "macd_signal", "macd_hist", "atr_14",
    "hh_20d", "ll_20d", "dist_from_20d_high", "dist_from_20d_low",
]

passed_frames      = []
align_drop_report: list[dict] = []

for df in raw_frames:
    sym      = df["symbol"].iloc[0]
    n_before = len(df)
    df       = df.dropna(subset=FEATURE_COLS).reset_index(drop=True)
    n_after  = len(df)
    align_drop_report.append({
        "symbol": sym, "rows_before": n_before,
        "rows_dropped": n_before - n_after, "rows_after": n_after,
    })

    if n_after < MIN_HISTORY_DAYS:
        exclusion_log.append({
            "symbol": sym,
            "reason": "insufficient_rows_after_feature_alignment",
        })
        logger.warning(
            f"{sym}: Only {n_after} rows after feature alignment "
            f"(minimum: {MIN_HISTORY_DAYS}) — excluded."
        )
    else:
        passed_frames.append(df)

raw_frames = passed_frames
total_rows_fa = sum(len(df) for df in raw_frames)
stage_counts["after_feature_alignment"] = {"symbols": len(raw_frames), "rows": total_rows_fa}

print(f"Symbols after feature alignment : {len(raw_frames)}")
print(f"Total rows                      : {total_rows_fa:,}")
print()
print(pd.DataFrame(align_drop_report).to_string(index=False))
""",

    42: r"""if raw_frames:
    df_pool_check = pd.concat(raw_frames, ignore_index=True)
    feature_stds  = df_pool_check[FEATURE_COLS].std()
    near_constant = feature_stds[feature_stds < NEAR_CONSTANT_STD_THRESHOLD].index.tolist()

    print(f"Near-constant check (threshold std < {NEAR_CONSTANT_STD_THRESHOLD}):")
    if near_constant:
        for col in near_constant:
            print(f"  {col}: std = {feature_stds[col]:.2e}")
        if DROP_NEAR_CONSTANT_FEATURES:
            raw_frames   = [df.drop(columns=near_constant) for df in raw_frames]
            FEATURE_COLS = [c for c in FEATURE_COLS if c not in near_constant]
            print(f"Dropped {len(near_constant)} near-constant column(s). "
                  f"Final feature count: {len(FEATURE_COLS)}")
        else:
            logger.warning(f"Near-constant features retained: {near_constant}")
    else:
        print("  None detected — no columns dropped.")
else:
    print("No frames to process.")
""",

    44: r"""for i, df in enumerate(raw_frames):
    df["fwd_ret_20d"] = df["close"].shift(-20) / df["close"] - 1
    raw_frames[i] = df

print("Forward 20-trading-day return computed.")
""",

    46: r"""passed_frames = []

for df in raw_frames:
    df = df.dropna(subset=["fwd_ret_20d"]).copy()

    df["label"] = "hold"
    df.loc[df["fwd_ret_20d"] >  0.05, "label"] = "buy"
    df.loc[df["fwd_ret_20d"] < -0.05, "label"] = "sell"

    passed_frames.append(df)

raw_frames = passed_frames
total_rows_la = sum(len(df) for df in raw_frames)
stage_counts["after_label_assignment"] = {"symbols": len(raw_frames), "rows": total_rows_la}

print(f"Symbols after label assignment : {len(raw_frames)}")
print(f"Total rows                     : {total_rows_la:,}")
""",

    48: r"""df_prepared = pd.concat(raw_frames, ignore_index=True)
df_prepared.reset_index(drop=True, inplace=True)

print(f"Pooled dataset shape : {df_prepared.shape}")
print(f"Symbols              : {df_prepared['symbol'].nunique()}")
""",

    50: r"""integrity_ok = True

# 1. Duplicate (symbol, date) pairs
n_dups = df_prepared.duplicated(subset=["symbol", "date"]).sum()
if n_dups:
    integrity_ok = False
    dup_detail = df_prepared[df_prepared.duplicated(subset=["symbol", "date"], keep=False)]
    raise AssertionError(f"Found {n_dups} duplicate (symbol, date) pairs:\n{dup_detail.head(10)}")
else:
    print("PASS  No duplicate (symbol, date) pairs.")

# 2. Required columns present and fully populated
all_required    = FEATURE_COLS + ["label"]
missing_from_df = [c for c in all_required if c not in df_prepared.columns]
if missing_from_df:
    integrity_ok = False
    print(f"FAIL  Missing columns: {missing_from_df}")
else:
    print(f"PASS  All {len(all_required)} required columns present.")

null_counts = df_prepared[all_required].isna().sum()
null_cols   = null_counts[null_counts > 0]
if not null_cols.empty:
    integrity_ok = False
    print(f"FAIL  Null values found:\n{null_cols.to_string()}")
else:
    print("PASS  No null values in feature or label columns.")

# 3. Label domain check
valid_labels = {"buy", "sell", "hold"}
label_vals   = set(df_prepared["label"].unique())
if not label_vals.issubset(valid_labels):
    integrity_ok = False
    print(f"FAIL  Unexpected label values: {label_vals - valid_labels}")
else:
    print(f"PASS  Label values valid: {sorted(label_vals)}")

print()
print("All integrity checks passed." if integrity_ok else "One or more integrity checks FAILED.")
""",

    52: r"""OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
saved_paths: list[Path] = []

if SAVE_PARQUET:
    parquet_path = OUTPUT_DIR / f"{OUTPUT_BASENAME}.parquet"
    df_prepared.to_parquet(parquet_path, engine=_PARQUET_ENGINE, index=False)
    saved_paths.append(parquet_path)
    print(f"Saved Parquet : {parquet_path}")

if SAVE_CSV:
    csv_path = OUTPUT_DIR / f"{OUTPUT_BASENAME}.csv"
    df_prepared.to_csv(csv_path, index=False)
    saved_paths.append(csv_path)
    print(f"Saved CSV     : {csv_path}")

if not saved_paths:
    print("No output files saved (SAVE_PARQUET=False and SAVE_CSV=False).")
""",

    54: r"""metadata = {
    "run_timestamp": datetime.utcnow().isoformat() + "Z",
    "universe_csv_name": UNIVERSE_CSV_NAME,
    "configuration": {
        "LOOKBACK_YEARS":               LOOKBACK_YEARS,
        "MIN_HISTORY_DAYS":             MIN_HISTORY_DAYS,
        "MAX_MISSING_FRAC_PER_SYMBOL":  MAX_MISSING_FRAC_PER_SYMBOL,
        "ROW_MISSING_POLICY":           ROW_MISSING_POLICY,
        "MIN_MEDIAN_VALUE_TRADED_20D":  MIN_MEDIAN_VALUE_TRADED_20D,
        "NEAR_CONSTANT_STD_THRESHOLD":  NEAR_CONSTANT_STD_THRESHOLD,
        "DROP_NEAR_CONSTANT_FEATURES":  DROP_NEAR_CONSTANT_FEATURES,
        "SAVE_PARQUET":                 SAVE_PARQUET,
        "SAVE_CSV":                     SAVE_CSV,
        "OUTPUT_BASENAME":              OUTPUT_BASENAME,
    },
    "stage_counts": {
        stage: {k: v for k, v in counts.items() if v is not None}
        for stage, counts in stage_counts.items()
    },
    "exclusion_log": exclusion_log,
    "final_dataset": {
        "n_rows":         int(len(df_prepared)),
        "n_symbols":      int(df_prepared["symbol"].nunique()),
        "n_feature_cols": len(FEATURE_COLS),
        "output_files":   [str(p) for p in saved_paths],
    },
}

metadata_path = OUTPUT_DIR / "run_metadata.json"
with open(metadata_path, "w", encoding="utf-8") as fh:
    json.dump(metadata, fh, indent=2)

print(f"Metadata saved: {metadata_path}")
""",

    56: r"""_stage_labels = {
    "raw_universe":               "Raw universe",
    "after_symbol_normalisation": "After symbol normalisation",
    "after_file_resolution":      "After file resolution",
    "after_schema_date_checks":   "After schema & date checks",
    "after_quality_filtering":    "After quality filtering",
    "after_feature_alignment":    "After feature alignment",
    "after_label_assignment":     "After label assignment",
}

rows = []
for key, label in _stage_labels.items():
    counts = stage_counts.get(key, {})
    rows.append({
        "Stage":   label,
        "Symbols": counts.get("symbols", "—"),
        "Rows":    counts.get("rows",    "—"),
    })
rows.append({
    "Stage":   "Final prepared dataset",
    "Symbols": int(df_prepared["symbol"].nunique()),
    "Rows":    int(len(df_prepared)),
})

display(pd.DataFrame(rows))
""",

    58: r"""if exclusion_log:
    df_excl = pd.DataFrame(exclusion_log)

    print("=== Exclusion Summary (by reason) ===")
    summary = (
        df_excl.groupby("reason", sort=False)
               .size()
               .rename("count")
               .reset_index()
               .sort_values("count", ascending=False)
    )
    display(summary)

    print("\n=== Full Exclusion Detail ===")
    display(df_excl)
else:
    print("No symbols were excluded.")
""",

    60: r"""desc_stats = df_prepared[FEATURE_COLS].describe().T
display(desc_stats)

key_features = [f for f in [
    "ret_1d", "ret_5d", "ret_20d", "ret_60d",
    "vol_ret_20d", "rsi_14", "macd", "atr_14",
    "close_over_sma_20", "close_over_sma_200",
    "dist_from_20d_high", "dist_from_20d_low",
] if f in df_prepared.columns]

corr = df_prepared[key_features].corr()

fig, ax = plt.subplots(figsize=(12, 9))
im = ax.imshow(corr.values, cmap="coolwarm", vmin=-1, vmax=1)
plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
ax.set_xticks(range(len(key_features)))
ax.set_yticks(range(len(key_features)))
ax.set_xticklabels(key_features, rotation=45, ha="right", fontsize=8)
ax.set_yticklabels(key_features, fontsize=8)
ax.set_title("Feature Correlation Heatmap (representative subset)", fontsize=12)
plt.tight_layout()
plt.show()
""",

    62: r"""label_order  = ["buy", "hold", "sell"]
label_counts = df_prepared["label"].value_counts().reindex(label_order, fill_value=0)
label_pct    = (label_counts / label_counts.sum() * 100).round(2)

df_label_dist = pd.DataFrame({"count": label_counts, "pct (%)": label_pct})
print("Label distribution:")
display(df_label_dist)

colors = {"buy": "seagreen", "hold": "steelblue", "sell": "firebrick"}
fig, ax = plt.subplots(figsize=(6, 4))
bars = ax.bar(
    label_counts.index,
    label_counts.values,
    color=[colors[l] for l in label_counts.index],
)
ax.set_xlabel("Label")
ax.set_ylabel("Count")
ax.set_title("Label Distribution  (buy / hold / sell)")
for bar, val, pct in zip(bars, label_counts.values, label_pct.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(label_counts) * 0.01,
        f"{val:,}\n({pct:.1f}%)",
        ha="center", va="bottom", fontsize=9,
    )
ax.set_ylim(0, label_counts.max() * 1.15)
plt.tight_layout()
plt.show()
""",
}

with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell_idx_0based, source_str in CELLS.items():
    cell = nb["cells"][cell_idx_0based]
    assert cell["cell_type"] == "code", f"Cell {cell_idx_0based} is not a code cell!"
    lines = source_str.split("\n")
    # Re-join as notebook source lines (each line ends with \n except the last)
    source_lines = [line + "\n" for line in lines[:-1]]
    if lines[-1]:  # last element after split
        source_lines.append(lines[-1])
    cell["source"] = source_lines
    cell["outputs"] = []
    cell["execution_count"] = None

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"Done. Wrote {len(CELLS)} code cells.")
