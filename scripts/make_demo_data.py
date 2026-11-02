"""Write deterministic synthetic CSV files with known injected faults.

Layout under OUT_DIR:
    current/   the files to audit
    baseline/  the earlier version of each file (for schema drift)
    faults.json  (written by the command line entry only, outside both folders)

Run: python scripts/make_demo_data.py OUT_DIR [--seed N]
Only random.Random(seed) is used; there are no timestamps, so the same seed
always produces the same bytes.
"""
import argparse
import json
import random
from pathlib import Path

FIRST = ["Amira", "Ben", "Chen", "Dalia", "Elias", "Farah", "Gus", "Hana", "Ivo", "Jun"]
CITIES = ["Beirut", "Berlin", "Lagos", "Lima", "Oslo", "Pune", "Quito", "Turin"]
ACTIONS = ["view", "click", "scroll", "search", "logout"]
NOTES = ["fine", "slow delivery", "great", "would buy again", "late", "ok"]
ROWS = 200


def _write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(",".join(r) for r in [header, *rows]) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _date(rng: random.Random) -> str:
    return f"20{rng.randint(20, 25)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def _clean_customers(rng):
    rows = [
        [str(i), rng.choice(FIRST), str(rng.randint(18, 80)), rng.choice(CITIES),
         f"{rng.uniform(100, 900):.2f}", _date(rng)]
        for i in range(1, ROWS + 1)
    ]
    return ["customer_id", "name", "age", "city", "balance", "signup_date"], rows, []


def _orders(rng):
    rows = [[str(i), rng.choice(FIRST), str(rng.randint(1, 10)), f"{rng.uniform(10, 200):.2f}"]
            for i in range(1, ROWS + 1)]
    for i in (50, 120, 170):  # same order_id as an earlier row, different content
        rows[i][0] = rows[i - 40][0]
    return ["order_id", "customer", "quantity", "total"], rows, ["dup_key:order_id"]


def _events(rng):
    rows = [[str(i), f"2024-03-{rng.randint(1, 28):02d} {rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}:00",
             rng.choice(FIRST), rng.choice(ACTIONS)] for i in range(1, ROWS + 1)]
    for i in (30, 90, 150):  # exact copies of earlier rows
        rows.append(list(rows[i]))
    return ["seq", "ts", "user", "action"], rows, ["dup_rows"]


def _products(rng):
    rows = [[str(1000 + i), f"{rng.uniform(5, 95):.2f}", str(rng.randint(0, 50))]
            for i in range(ROWS)]
    for i in (10, 60, 110, 160):  # 2% of prices are text
        rows[i][1] = "n/a"
    return ["product_id", "price", "stock"], rows, ["text_numbers:price"]


def _payments(rng):
    rows = [[str(i), f"{rng.uniform(20, 120):.2f}", rng.choice(FIRST)] for i in range(1, ROWS + 1)]
    for i, big in ((25, "5000.00"), (100, "7500.00"), (175, "9900.00")):
        rows[i][1] = big
    return ["payment_id", "amount", "payer"], rows, ["outlier:amount"]


def _survey(rng):
    rows = [[str(i), str(rng.randint(1, 5)), rng.choice(NOTES)] for i in range(1, ROWS + 1)]
    for i in range(ROWS):  # exactly 40% of notes are missing
        if i % 5 in (0, 2):
            rows[i][2] = ""
    return ["respondent_id", "score", "notes"], rows, ["null_column:notes"]


def _inventory(rng):
    base_rows = [[f"SKU{i:03d}", rng.choice(CITIES), str(rng.randint(1, 99)), rng.choice(["N", "S", "E", "W"])]
                 for i in range(ROWS)]
    baseline = (["sku", "warehouse", "qty", "region"], base_rows)
    cur_rows = [[r[0], r[1], f"{r[2]} pcs"] for r in base_rows]  # region dropped, qty becomes text
    return ["sku", "warehouse", "qty"], cur_rows, ["schema_dropped:region", "schema_retyped:qty"], baseline


FILES = {
    "clean_customers.csv": _clean_customers,
    "events.csv": _events,
    "inventory.csv": _inventory,
    "orders.csv": _orders,
    "payments.csv": _payments,
    "products.csv": _products,
    "survey.csv": _survey,
}


def make_demo(out_dir: Path, seed: int = 7) -> dict[str, list[str]]:
    out_dir = Path(out_dir)
    rng = random.Random(seed)
    faults: dict[str, list[str]] = {}
    for name in sorted(FILES):
        result = FILES[name](rng)
        header, rows, injected = result[:3]
        _write(out_dir / "current" / name, header, rows)
        base_header, base_rows = result[3] if len(result) > 3 else (header, rows)
        _write(out_dir / "baseline" / name, base_header, base_rows)
        faults[name] = list(injected)
    return faults


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write synthetic demo CSV files with injected faults.")
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    faults = make_demo(args.out_dir, args.seed)
    with open(args.out_dir / "faults.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump(faults, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(f"wrote {len(faults)} files to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
