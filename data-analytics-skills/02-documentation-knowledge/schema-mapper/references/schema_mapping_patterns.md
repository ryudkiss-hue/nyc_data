# Schema Mapping Patterns

## Mapping relationship types

### 1. Direct map (1-to-1, same type)
Source column maps directly to target column with the same name and compatible type. No transformation needed.

```sql
source.customer_id  →  target.customer_id  (INTEGER → INTEGER)
```

### 2. Rename (1-to-1, different name)
Same data, different column name between systems. Requires alias in the SELECT or explicit mapping declaration.

```sql
source.cust_id  →  target.customer_id
```

### 3. Type cast (1-to-1, different type)
Same data but requires an explicit CAST to avoid silent truncation or precision loss.

```sql
source.amount_cents (INTEGER)  →  target.amount_usd (DECIMAL)
-- Transformation: amount_cents / 100.0
```

### 4. Derivation (0-to-1, computed in target)
Target column has no direct source equivalent — it must be computed from one or more source columns.

```sql
-- target.full_name derived from:
CONCAT(source.first_name, ' ', source.last_name)
```

### 5. Split (1-to-many)
One source column maps to multiple target columns.

```sql
source.address  →  target.city, target.state, target.zip
```

### 6. Merge / Coalesce (many-to-1)
Multiple source columns collapse into one target column, using fallback logic.

```sql
COALESCE(source.mobile_phone, source.work_phone, source.home_phone)
→ target.contact_phone
```

### 7. Dropped column
Source column exists but is not needed in the target. Should be explicitly documented — not silently omitted.

### 8. Defaulted column
Target column with no source; populated with a static default or NULL. Must be validated for NOT NULL constraints.

---

## Common type compatibility issues

| Source type | Target type | Risk |
|---|---|---|
| VARCHAR | DATE | Parse failure if format varies |
| FLOAT | DECIMAL | Precision loss |
| INTEGER | BOOLEAN | Only valid for 0/1 values |
| TIMESTAMP | DATE | Time component dropped silently |
| TEXT | VARCHAR(n) | Truncation if length > n |

---

## Schema mapping documentation standards

For each mapped column, record:

1. **Source column** — fully qualified name (schema.table.column)
2. **Target column** — fully qualified name
3. **Transformation** — SQL expression or "direct"
4. **Type cast required** — Yes/No and the CAST expression
5. **Nullable** — source and target nullability
6. **Validation rule** — e.g., must be > 0, must match lookup table
7. **Owner sign-off** — who approved the mapping logic
