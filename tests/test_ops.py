import pandas as pd

from socrata_toolkit.ops.core import (
    apply_grace_period_updates,
    generate_burndown,
    permit_lookahead_sql,
    flag_high_priority_trigger_sql,
)


def test_apply_grace_period_updates_triggers():
    df = pd.DataFrame({
        "issued_date": ["2020-01-01", "2099-01-01"],
        "GRACE_PD": [75, 75],
        "status": ["Pending Repair", "Pending Repair"],
    })
    out = apply_grace_period_updates(df)
    # The 2020 row should have triggered (>75 days ago)
    assert bool(out.loc[0, "_grace_trigger"]) is True
    assert out.loc[0, "status"] == "City-Initiated"
    # The 2099 row should NOT have triggered (in the future)
    assert bool(out.loc[1, "_grace_trigger"]) is False
    assert out.loc[1, "status"] == "Pending Repair"


def test_apply_grace_period_updates_override_days():
    df = pd.DataFrame({
        "issued_date": ["2020-01-01"],
        "GRACE_PD": [None],
        "status": ["Pending Repair"],
    })
    out = apply_grace_period_updates(df, override_days=75)
    assert bool(out.loc[0, "_grace_trigger"]) is True


def test_generate_burndown():
    df = pd.DataFrame({"area_sqft": [5000.0, 3000.0]})
    result = generate_burndown(df, daily_capacity_sqft=1000.0)
    assert result["days_to_complete"] == 8
    assert result["remaining_sqft"] == 8000.0


def test_permit_lookahead_sql():
    sql = permit_lookahead_sql("proposed", "permits", days=30)
    assert "ST_DWithin" in sql
    assert "proposed" in sql
    assert "30 days" in sql


def test_flag_high_priority_trigger_sql():
    sql = flag_high_priority_trigger_sql("complaints")
    assert "CREATE OR REPLACE FUNCTION" in sql
    assert "complaints" in sql
    assert "is_high_priority" in sql
