"""
test_pipeline.py
Project Aura - Week 2 Test Script

Run with:
    python tests/test_pipeline.py
"""

import sys
import os

# Allow importing from the src/ folder
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from data_pipeline import (
    load_land_registry_data,
    get_property_history,
    calculate_cagr,
    calculate_rental_yield,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "pp-2024.csv")


def test_load_data():
    print("\n--- Test: Load Data ---")
    df = load_land_registry_data(DATA_PATH)
    print(f"Loaded {len(df)} rows")
    assert len(df) > 0, "Expected data to load successfully"
    print("PASS")
    return df


def test_valid_postcode(df):
    print("\n--- Test: Valid Postcode (DE6 1TW) ---")
    result = get_property_history(df, "DE6 1TW")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result["status"] in ("exact", "district_fallback")
    assert len(result["data"]) > 0
    print("PASS")
    return result["data"]


def test_invalid_postcode(df):
    print("\n--- Test: Invalid Postcode ('NOTREAL') ---")
    result = get_property_history(df, "NOTREAL")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result["status"] == "invalid_input"
    print("PASS - did not crash")


def test_nonexistent_postcode(df):
    print("\n--- Test: Well-formed but nonexistent postcode ('ZZ99 9ZZ') ---")
    result = get_property_history(df, "ZZ99 9ZZ")
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result["status"] == "not_found"
    print("PASS - did not crash")


def test_cagr(history_data):
    print("\n--- Test: CAGR Calculation ---")
    result = calculate_cagr(history_data)
    print(f"Status: {result['status']}")
    print(f"CAGR: {result['cagr_percent']}%")
    print(f"Message: {result['message']}")
    assert result["status"] == "ok"
    print("PASS")


def test_cagr_empty_data():
    print("\n--- Test: CAGR with Empty Data ---")
    import pandas as pd
    empty_df = pd.DataFrame(columns=["date_of_transfer", "price"])
    result = calculate_cagr(empty_df)
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result["status"] == "insufficient_data"
    print("PASS - did not crash")


def test_rental_yield_valid():
    print("\n--- Test: Rental Yield (valid input) ---")
    result = calculate_rental_yield(property_price=225000, monthly_rent=950, estimated_annual_costs=1500)
    print(f"Status: {result['status']}")
    print(f"Gross Yield: {result['gross_yield_percent']}%")
    print(f"Net Yield: {result['net_yield_percent']}%")
    assert result["status"] == "ok"
    print("PASS")


def test_rental_yield_invalid():
    print("\n--- Test: Rental Yield (invalid input - negative price) ---")
    result = calculate_rental_yield(property_price=-100, monthly_rent=950)
    print(f"Status: {result['status']}")
    print(f"Message: {result['message']}")
    assert result["status"] == "invalid_input"
    print("PASS - did not crash")


if __name__ == "__main__":
    df = test_load_data()
    history = test_valid_postcode(df)
    test_invalid_postcode(df)
    test_nonexistent_postcode(df)
    test_cagr(history)
    test_cagr_empty_data()
    test_rental_yield_valid()
    test_rental_yield_invalid()

    print("\n=== ALL TESTS PASSED ===")