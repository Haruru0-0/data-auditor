import json

from dataauditor.load import open_table
from dataauditor.profile import profile_columns


def profile(con, csv, text, name="t.csv"):
    return profile_columns(con, open_table(con, csv(name, text)))


def test_numeric_column(con, csv):
    p = profile(con, csv, "n\n1\n2\n3\n3\n\n")
    assert p["n"] == {"type": "BIGINT", "missing": 1, "distinct": 3, "min": 1, "max": 3, "mean": 2.25}


def test_text_column_has_no_min_max_mean(con, csv):
    p = profile(con, csv, "s\na\nb\na\n")
    assert p["s"] == {"type": "VARCHAR", "missing": 0, "distinct": 2}


def test_date_column_is_iso_strings(con, csv):
    p = profile(con, csv, "d\n2024-01-05\n2024-03-01\n")
    assert p["d"]["type"] == "DATE"
    assert p["d"]["min"] == "2024-01-05" and p["d"]["max"] == "2024-03-01"
    assert "mean" not in p["d"]


def test_timestamp_column(con, csv):
    p = profile(con, csv, "t\n2024-01-05 10:00:00\n2024-01-06 11:30:00\n")
    assert p["t"]["min"] == "2024-01-05T10:00:00"
    assert p["t"]["max"] == "2024-01-06T11:30:00"


def test_all_null_column(con, csv):
    p = profile(con, csv, "id,e\n1,\n2,\n")
    assert p["e"]["missing"] == 2 and p["e"]["distinct"] == 0
    assert p["e"].get("min") is None and p["e"].get("max") is None


def test_all_null_numeric_has_null_stats(con, csv, tmp_path):
    path = tmp_path / "n.parquet"
    con.execute(f"COPY (SELECT NULL::DOUBLE AS x) TO '{path.as_posix()}' (FORMAT parquet)")
    p = profile_columns(con, open_table(con, path))
    assert p["x"] == {"type": "DOUBLE", "missing": 1, "distinct": 0, "min": None, "max": None, "mean": None}


def test_odd_column_names_and_order(con, csv):
    p = profile(con, csv, 'z,"a ""q"" b",日本\n1,2,3\n')
    assert list(p) == ["z", 'a "q" b', "日本"]
    assert p['a "q" b']["max"] == 2


def test_empty_table(con, csv):
    p = profile(con, csv, "a,b\n")
    assert p["a"]["missing"] == 0 and p["a"]["distinct"] == 0
    assert set(p) == {"a", "b"}


def test_nan_and_inf_become_null_and_json_safe(con, tmp_path):
    path = tmp_path / "f.parquet"
    con.execute(
        f"COPY (SELECT * FROM (VALUES ('NaN'::DOUBLE), ('Infinity'::DOUBLE), (1.0)) v(x)) "
        f"TO '{path.as_posix()}' (FORMAT parquet)"
    )
    p = profile_columns(con, open_table(con, path))
    assert p["x"]["mean"] is None and p["x"]["max"] is None
    json.dumps(p, allow_nan=False)


def test_mean_rounded_to_four_decimals(con, csv):
    p = profile(con, csv, "n\n1\n1\n2\n")
    assert p["n"]["mean"] == 1.3333


def test_timestamptz_parquet_column_has_min_max(con, tmp_path):
    path = tmp_path / "tz.parquet"
    con.execute(
        f"COPY (SELECT TIMESTAMPTZ '2024-01-05 10:00:00+00' AS ts UNION ALL "
        f"SELECT TIMESTAMPTZ '2024-02-01 00:00:00+00') TO '{path.as_posix()}' (FORMAT parquet)"
    )
    table = open_table(con, path)
    assert "TIME ZONE" in table.columns["ts"].upper() or table.columns["ts"].upper().startswith("TIMESTAMP")
    p = profile_columns(con, table)
    assert p["ts"]["min"].startswith("2024-01-05") and p["ts"]["max"].startswith("2024-02-01")
    json.dumps(p, allow_nan=False)
