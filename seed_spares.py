"""
Seed spares database from May 2026 Stock Codes Excel file.

Usage:
    python seed_spares.py

Requirements:
    pip install openpyxl requests

The script reads the Excel file, extracts stock codes, descriptions,
categories, quantities, and unit prices, then posts them to the API
in batches of 50.

IMPORTANT: Run this ONCE. Re-running will skip existing stock codes.
"""

import openpyxl
import json
import requests
import time
import sys
import os

EXCEL_PATH = r"C:\Users\JosphatDandira\OneDrive - Dallaglio\2025 REPORTS FOLDER\DAILY REPORTS 2026\MAY\STOCK CODES list.xlsx"
API_URL = os.environ.get("API_URL", "http://localhost:8000")
BULK_ENDPOINT = f"{API_URL}/api/spares/bulk"
BATCH_SIZE = 50


def extract_items(path: str) -> list[dict]:
    print(f"Reading: {path}")
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    items: list[dict] = []
    seen: set[str] = set()
    current_category = ""

    for row in ws.iter_rows(min_row=2, values_only=True):
        a, b, c, d, e, f = (row[i] if i < len(row) else None for i in range(6))

        # Detect category header rows
        if a == "Category :" and b:
            current_category = str(b).strip()
            continue

        # Skip meta/header rows
        if a is None or a in ("Product", "Site :", "Company total :", "Consumables",
                               "Crusher Spares"):
            continue
        if isinstance(a, str) and (len(a) > 25 or " " in a[:4]):
            continue

        # Data rows: A=stock_code, B=description, C=category, D=qty, E=uom, F=unit_price
        try:
            stock_code = str(a).strip()
            if not stock_code or stock_code in seen:
                continue
            desc = str(b).strip() if b else ""
            if not desc or desc == "Description":
                continue
            if not isinstance(f, (int, float)):
                continue

            unit_price = round(float(f), 4)
            qty = int(d) if isinstance(d, (int, float)) else 0
            uom = str(e).strip() if e and not isinstance(e, (int, float)) else "UN"
            cat = str(c).strip() if c and not isinstance(c, (int, float)) else current_category

            seen.add(stock_code)
            items.append({
                "stock_code": stock_code,
                "description": desc,
                "category": cat or None,
                "current_quantity": qty,
                "unit_of_measure": uom,
                "unit_price": unit_price,
                "min_quantity": 1,
                "max_quantity": max(qty * 2, 5),
                "priority": "medium",
                "safety_stock": False,
            })
        except Exception:
            continue

    print(f"Extracted {len(items)} unique items from Excel")
    return items


def seed(items: list[dict]) -> None:
    total_created = 0
    total_skipped = 0
    total_errors = 0

    batches = [items[i : i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    print(f"Posting {len(batches)} batches of up to {BATCH_SIZE} items to {BULK_ENDPOINT}")
    print()

    for idx, batch in enumerate(batches, 1):
        payload = {"items": batch, "skip_existing": True}
        try:
            resp = requests.post(BULK_ENDPOINT, json=payload, timeout=30)
            if resp.status_code == 201:
                result = resp.json()
                total_created += result.get("created", 0)
                total_skipped += result.get("skipped", 0)
                total_errors += result.get("errors", 0)
                print(
                    f"  Batch {idx:3d}/{len(batches)} — "
                    f"created: {result.get('created',0):3d}, "
                    f"skipped: {result.get('skipped',0):3d}, "
                    f"errors: {result.get('errors',0):2d}"
                )
            else:
                print(f"  Batch {idx} FAILED: {resp.status_code} — {resp.text[:200]}")
                total_errors += len(batch)
        except requests.RequestException as e:
            print(f"  Batch {idx} REQUEST ERROR: {e}")
            total_errors += len(batch)

        # Small delay to avoid overwhelming the server
        time.sleep(0.1)

    print()
    print("=" * 50)
    print(f"DONE — Created: {total_created} | Skipped: {total_skipped} | Errors: {total_errors}")
    print(f"Total processed: {total_created + total_skipped + total_errors} / {len(items)}")


if __name__ == "__main__":
    # Allow overriding the Excel path via command line
    excel_path = sys.argv[1] if len(sys.argv) > 1 else EXCEL_PATH

    if not os.path.exists(excel_path):
        print(f"ERROR: File not found: {excel_path}")
        print("Usage: python seed_spares.py [path_to_excel]")
        sys.exit(1)

    items = extract_items(excel_path)
    if not items:
        print("No items extracted. Exiting.")
        sys.exit(1)

    print(f"\nReady to seed {len(items)} items into {API_URL}")
    confirm = input("Proceed? (y/N): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    seed(items)
