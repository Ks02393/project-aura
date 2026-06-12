"""
data_pipeline.py
Project Aura - Data Ingestion & Financial Calculation Module (Week 2)

Implements:
- FR-2: Data Ingestion Module (Land Registry lookups, CAGR)
- FR-3: Financial Calculation Engine (Gross/Net Rental Yield)
- Section 6: Reliability (graceful handling of invalid postcodes)
"""

import pandas as pd

# Column names for the raw Land Registry CSV (no header row in the file)
COLUMNS = [
    "transaction_id", "price", "date_of_transfer", "postcode",
    "property_type", "old_new", "duration", "paon", "saon",
    "street", "locality", "town_city", "district", "county",
    "ppd_category", "record_status"
]

MIN_ROWS_FOR_EXACT_MATCH = 5


def load_land_registry_data(csv_paths) -> pd.DataFrame:
    """
    Load one or more Land Registry CSVs and combine them into a single
    DataFrame with proper column names and parsed dates.

    Args:
        csv_paths: a single file path (str) or a list of file paths.

    Returns:
        A combined pandas DataFrame, or an empty DataFrame if nothing
        could be loaded.
    """
    if isinstance(csv_paths, str):
        csv_paths = [csv_paths]

    frames = []
    for path in csv_paths:
        try:
            df = pd.read_csv(path, names=COLUMNS, header=None)
            frames.append(df)
        except FileNotFoundError:
            print(f"[WARNING] File not found, skipping: {path}")
        except Exception as e:
            print(f"[WARNING] Failed to load {path}, skipping: {e}")

    if not frames:
        print("[ERROR] No data files could be loaded.")
        return pd.DataFrame(columns=COLUMNS)

    combined = pd.concat(frames, ignore_index=True)
    combined["date_of_transfer"] = pd.to_datetime(combined["date_of_transfer"], errors="coerce")
    return combined


def is_valid_postcode_format(postcode: str) -> bool:
    """
    Very basic UK postcode format check (not a full validation,
    just enough to catch obviously wrong input like empty strings
    or random text).
    """
    if not isinstance(postcode, str):
        return False
    postcode = postcode.strip()
    if len(postcode) < 5 or len(postcode) > 8:
        return False
    if " " not in postcode:
        return False
    return True


def get_property_history(df: pd.DataFrame, postcode: str) -> dict:
    """
    Get historical transaction data for a postcode, falling back to
    the postcode district if there's not enough exact-match data.

    Returns a dict with:
        - status: "exact", "district_fallback", "not_found", or "invalid_input"
        - data: filtered DataFrame (empty if not_found or invalid_input)
        - message: human-readable explanation
    """
    if not is_valid_postcode_format(postcode):
        return {
            "status": "invalid_input",
            "data": pd.DataFrame(columns=COLUMNS),
            "message": f"'{postcode}' doesn't look like a valid UK postcode (expected format e.g. 'DE6 1TW')."
        }

    postcode = postcode.strip().upper()

    # Try exact match first
    exact_matches = df[df["postcode"] == postcode]

    if len(exact_matches) >= MIN_ROWS_FOR_EXACT_MATCH:
        return {
            "status": "exact",
            "data": exact_matches,
            "message": f"Found {len(exact_matches)} transactions for postcode {postcode}."
        }

    # Fall back to the postcode district (e.g. "DE6" from "DE6 1TW")
    district = postcode.split(" ")[0]
    district_matches = df[df["postcode"].str.startswith(district + " ")]

    if len(district_matches) > 0:
        return {
            "status": "district_fallback",
            "data": district_matches,
            "message": (
                f"Only {len(exact_matches)} exact match(es) for {postcode}. "
                f"Using {len(district_matches)} transactions from district '{district}' instead."
            )
        }

    return {
        "status": "not_found",
        "data": pd.DataFrame(columns=COLUMNS),
        "message": f"No transaction data found for postcode {postcode} or district '{district}'."
    }


def calculate_cagr(data: pd.DataFrame) -> dict:
    """
    Calculate annualized capital appreciation (CAGR) from a set of
    transactions, by comparing average prices in the earliest vs
    latest 90-day windows of the data.

    Returns a dict with:
        - status: "ok" or "insufficient_data"
        - cagr_percent: float or None
        - message: human-readable explanation
    """
    if data.empty:
        return {
            "status": "insufficient_data",
            "cagr_percent": None,
            "message": "No data available to calculate CAGR."
        }

    earliest_date = data["date_of_transfer"].min()
    latest_date = data["date_of_transfer"].max()

    years_diff = (latest_date - earliest_date).days / 365.25

    start_window = data[data["date_of_transfer"] <= earliest_date + pd.Timedelta(days=90)]
    end_window = data[data["date_of_transfer"] >= latest_date - pd.Timedelta(days=90)]

    start_price = start_window["price"].mean()
    end_price = end_window["price"].mean()

    if years_diff <= 0 or pd.isna(start_price) or start_price <= 0:
        return {
            "status": "insufficient_data",
            "cagr_percent": None,
            "message": "Not enough date range or price data to calculate CAGR."
        }

    cagr = (end_price / start_price) ** (1 / years_diff) - 1

    return {
        "status": "ok",
        "cagr_percent": round(cagr * 100, 2),
        "message": f"CAGR calculated over {years_diff:.2f} years."
    }


def calculate_rental_yield(property_price: float, monthly_rent: float, estimated_annual_costs: float = 0.0) -> dict:
    """
    Calculate Gross and Net Rental Yield (FR-3).

    Args:
        property_price: asking/purchase price of the property (must be > 0)
        monthly_rent: estimated monthly rental income (must be >= 0)
        estimated_annual_costs: estimated annual running costs (default 0)

    Returns a dict with:
        - status: "ok" or "invalid_input"
        - gross_yield_percent: float or None
        - net_yield_percent: float or None
        - message: human-readable explanation
    """
    if property_price is None or property_price <= 0:
        return {
            "status": "invalid_input",
            "gross_yield_percent": None,
            "net_yield_percent": None,
            "message": "Property price must be a positive number."
        }

    if monthly_rent is None or monthly_rent < 0:
        return {
            "status": "invalid_input",
            "gross_yield_percent": None,
            "net_yield_percent": None,
            "message": "Monthly rent must be zero or a positive number."
        }

    annual_rent = monthly_rent * 12

    gross_yield = (annual_rent / property_price) * 100
    net_yield = ((annual_rent - estimated_annual_costs) / property_price) * 100

    return {
        "status": "ok",
        "gross_yield_percent": round(gross_yield, 2),
        "net_yield_percent": round(net_yield, 2),
        "message": "Yield calculated successfully."
    }