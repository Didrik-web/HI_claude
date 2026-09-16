import pandas as pd
from .. import config

SOURCE_START = pd.Timestamp("2024-01-01 00:00:00")
SOURCE_END = pd.Timestamp("2024-01-15 00:00:00")
EXPECTED_HOURS = 336


def build_processed_prices():
    raw = pd.read_csv(config.RAW_PRICES)
    required = {"MTU (CET/CEST)", "Area", "Day-ahead Price (EUR/MWh)"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Raw ENTSO-E file missing columns: {sorted(missing)}")

    raw = raw.loc[raw["Area"].eq("BZN|SE1")].copy()
    raw["source_time"] = pd.to_datetime(
        raw["MTU (CET/CEST)"].str.split(" - ").str[0],
        format="%d/%m/%Y %H:%M:%S",
        errors="raise",
    )
    raw = raw.loc[
        (raw.source_time >= SOURCE_START) & (raw.source_time < SOURCE_END)
    ].sort_values("source_time")
    raw = raw.rename(columns={"Day-ahead Price (EUR/MWh)": "price_EUR_MWh"})

    if len(raw) != EXPECTED_HOURS or raw.price_EUR_MWh.isna().any():
        raise ValueError(f"Expected {EXPECTED_HOURS} complete hourly prices")

    fleet = pd.read_csv(config.FLEET_INTERFACE)
    sim_time = (
        pd.to_datetime(fleet["time"], errors="raise", utc=True)
        .drop_duplicates().sort_values().reset_index(drop=True)
    )
    if len(sim_time) != EXPECTED_HOURS:
        raise ValueError("Fleet horizon must contain 336 unique hours")

    out = pd.DataFrame({
        "time": sim_time,
        "source_time": raw["source_time"].reset_index(drop=True),
        "price_EUR_MWh": raw["price_EUR_MWh"].reset_index(drop=True),
    })
    config.MARKET_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(config.PRICE_DATA, index=False)
    return out


if __name__ == "__main__":
    out = build_processed_prices()
    print(f"Wrote {len(out)} rows to {config.PRICE_DATA}")
