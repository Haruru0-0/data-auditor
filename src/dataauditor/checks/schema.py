from dataauditor.findings import Finding
from dataauditor.load import Table


def compare_schemas(old: Table, new: Table) -> list[Finding]:
    removed = []
    retyped = []
    added = []
    for name, old_type in old.columns.items():
        if name not in new.columns:
            removed.append(
                Finding("schema", "error", name, f"column removed (was {old_type})", 1)
            )
        elif new.columns[name] != old_type:
            retyped.append(
                Finding(
                    "schema",
                    "warning",
                    name,
                    f"type changed from {old_type} to {new.columns[name]}",
                    1,
                )
            )
    for name, new_type in new.columns.items():
        if name not in old.columns:
            added.append(Finding("schema", "info", name, f"column added ({new_type})", 1))
    return removed + retyped + added
