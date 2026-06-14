from socrata_toolkit.core import (
    _quote_value,
    and_join,
    equals_clause,
    in_clause,
    like_clause,
    or_join,
)


def test_quote_value_string():
    assert _quote_value("hello") == "'hello'"

def test_quote_value_escapes_quotes():
    assert _quote_value("it's") == "'it''s'"

def test_quote_value_int():
    assert _quote_value(42) == "42"

def test_quote_value_none():
    assert _quote_value(None) == "NULL"

def test_quote_value_bool():
    assert _quote_value(True) == "true"
    assert _quote_value(False) == "false"

def test_in_clause_strings():
    result = in_clause("name", ["Alice", "Bob"])
    assert result == "name IN ('Alice','Bob')"

def test_in_clause_ints():
    result = in_clause("id", [1, 2, 3])
    assert result == "id IN (1,2,3)"

def test_in_clause_empty():
    assert in_clause("id", []) == "FALSE"

def test_in_clause_filters_none():
    result = in_clause("id", [1, None, 3])
    assert result == "id IN (1,3)"

def test_like_clause():
    result = like_clause("name", "%test%")
    assert result == "name LIKE '%test%'"

def test_equals_clause():
    assert equals_clause("status", "open") == "status = 'open'"
    assert equals_clause("count", 5) == "count = 5"

def test_and_join():
    assert and_join(["a = 1", "b = 2"]) == "a = 1 AND b = 2"

def test_or_join():
    assert or_join(["a = 1", "b = 2"]) == "a = 1 OR b = 2"

def test_and_join_filters_empty():
    assert and_join(["a = 1", "", "b = 2"]) == "a = 1 AND b = 2"
