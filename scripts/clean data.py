"""
clean_data.py
Cleans the CBK Mobile Payments statistics CSV into a tidy, analysis-ready format.

Input : data/raw/Mobile_Payments.csv   (as downloaded from centralbank.go.ke)
Output: data/clean/mobile_payments_clean.csv   (wide, one row per month)
        data/clean/mobile_payments_long.csv    (long/tidy, one row per metric per month)
"""

import pandas as pd

RAW_PATH = "data/raw/Mobile_Payments.csv"
CLEAN_WIDE_PATH = "data/clean/mobile_payments_clean.csv"
CLEAN_LONG_PATH = "data/clean/mobile_payments_long.csv"


def load_raw(path: str) -> pd.DataFrame:
    # encoding='utf-8-sig' strips the BOM (﻿) that shows up in the first header cell
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # Standardise column names — short, snake_case, no units/parentheses
    df = df.rename(columns={
        "Year": "year",
        "Month": "month_name",
        "Active Agents": "active_agents",
        "Total Registered Mobile Money Accounts (Millions)": "registered_accounts_millions",
        "Total Agent Cash in Cash Out (Volume Million)": "cico_volume_millions",
        "Total Agent Cash in Cash Out (Value KSh billions)": "cico_value_ksh_billions",
    })

    # Build a proper date column (first of each month) so it sorts/plots correctly
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month_name"], format="%Y-%B"
    )

    # Numeric columns should already be numeric, but enforce it in case of stray strings
    numeric_cols = [
        "active_agents",
        "registered_accounts_millions",
        "cico_volume_millions",
        "cico_value_ksh_billions",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Sort chronologically (raw file is newest-first)
    df = df.sort_values("date").reset_index(drop=True)

    # Sanity check: flag any rows that failed numeric parsing
    n_missing = df[numeric_cols].isna().any(axis=1).sum()
    if n_missing:
        print(f"Warning: {n_missing} row(s) have missing/unparseable values after cleaning.")

    # --- Derived metrics (this is the "decision-useful" layer) ---

    # Average value per cash-in/cash-out transaction (KES) — proxy for typical transaction size
    df["avg_txn_value_ksh"] = (
        df["cico_value_ksh_billions"] * 1_000_000_000
        / (df["cico_volume_millions"] * 1_000_000)
    )

    # Registered accounts per agent — proxy for agent network load/efficiency
    df["accounts_per_agent"] = (
        df["registered_accounts_millions"] * 1_000_000 / df["active_agents"]
    )

    # Year-over-year growth (%) for the two headline metrics, using a 12-month shift
    df["accounts_yoy_growth_pct"] = (
        df["registered_accounts_millions"].pct_change(periods=12) * 100
    )
    df["cico_value_yoy_growth_pct"] = (
        df["cico_value_ksh_billions"].pct_change(periods=12) * 100
    )

    # Drop the redundant year/month_name columns now that we have a proper date
    df = df.drop(columns=["year", "month_name"])

    # Reorder for readability
    cols = ["date"] + [c for c in df.columns if c != "date"]
    df = df[cols]

    return df


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape wide -> long for tools (e.g. Power BI) that prefer one metric per row."""
    long_df = df.melt(id_vars="date", var_name="metric", value_name="value")
    long_df = long_df.sort_values(["metric", "date"]).reset_index(drop=True)
    return long_df


def main():
    raw = load_raw(RAW_PATH)
    clean_df = clean(raw)
    long_df = to_long(clean_df)

    clean_df.to_csv(CLEAN_WIDE_PATH, index=False)
    long_df.to_csv(CLEAN_LONG_PATH, index=False)

    print(f"Rows in: {len(raw)} | Rows out (wide): {len(clean_df)}")
    print(f"Date range: {clean_df['date'].min().date()} -> {clean_df['date'].max().date()}")
    print(f"Saved: {CLEAN_WIDE_PATH}")
    print(f"Saved: {CLEAN_LONG_PATH}")


if __name__ == "__main__":
    main()