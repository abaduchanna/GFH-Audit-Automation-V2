# GFH Audit Timesheet Edition — Two Sheet Logic Flow

## Overview

After both sheets are imported (B2B Soft Count Details + GFH Timesheet), the app uses a sophisticated matching algorithm to:

1. **Match stores** between sheets (tolerant of spelling differences)
2. **Map employees** from timesheet to each store
3. **Filter count details** to latest records only
4. **Extract variances** from matched counts
5. **Identify pending stores** (in count file but no count yet)

---

## Sheet 1: Inventory_Count_Result_Details.xlsx (B2B Soft)

**Columns Used**:
- `Store` → Store name (normalized for matching)
- `District` → District name (source of truth)
- `Product Description` → What was counted
- `Serial #` / `IMEI` → Device identifier
- `Status` → Matched, Deficit, Surplus, etc.
- `Created By` → Username of who created count (optional, for deduplication)
- `Created Date` → When count was created (Excel serial, with time)

**Example Row**:
```
Store: "Arizona Store 123"
District: "Arizona"
Serial #: "123456789012345"
Status: "Deficit"
Created By: "backoffice"
Created Date: 45532.5 (Excel serial, ~7:00 AM on Jan 1, 2025)
```

---

## Sheet 2: timesheets_*.xlsx (GFH Telecom)

**Columns Used**:
- `Employee` / `Employee Name` → Who worked at store
- `Store` → Store they worked at
- `Clock In` → When they clocked in (Excel date, may be missing)
- `Clock Out` → When they clocked out

**Example Row**:
```
Employee: "Ali Baig"
Store: "Arizona #123"
Clock In: 45532.2 (Excel serial, ~4:48 AM)
```

---

## Step 1: Build Store Maps

**Function**: `build_store_maps(inventory_records, time_sheet_records)`

### Step 1a: Create timesheet → store-to-employee map

**From Timesheet Sheet**:
```python
ts_store_to_employee = {
    "arizonstore123": "Ali Baig",      # Normalized: "Arizona #123" → "Ali Baig"
    "coloradoeast456": "Shehriyar",    # Normalized: "Colorado East #456"
    "houston789": "Hamza",
}
```

**Logic**:
- Skip rows with "TOTAL" or "—" in employee name
- Normalize store name (remove spaces, special chars)
- If multiple employees per store, pick one with latest Clock In time
- If Clock In is missing, use row order

### Step 1b: Create count-details store-to-district map

**From Inventory Sheet**:
```python
district_by_store = {
    "arizonstore123": "Arizona",
    "coloradoeast456": "Colorado East",
}

display_by_store = {
    "arizonstore123": "Arizona Store 123",    # For display in UI
    "coloradoeast456": "Colorado East #456",
}
```

**Logic**:
- Extract district from "District" column (source of truth)
- Normalize store names same way as timesheet
- Keep display versions for UI

### Step 1c: Create store-to-employee map (with fuzzy matching)

**Call**: `match_store_employee(normalized_store, ts_store_to_employee)`

**Matching Strategy**:
1. **Exact match first**: If "arizonstore123" exists in timesheet map, use it
2. **Fuzzy token match**: If exact fails, use "Alphanumeric token subset" logic

**Example Fuzzy Match**:
```
Count file:      "Arizona Store 1204"  → tokens: {arizona, store, 1204}
Timesheet file:  "Arizona #1204"       → tokens: {arizona, 1204}

Match? YES — timesheet tokens {arizona, 1204} ⊆ count tokens {arizona, store, 1204}
Result: "Arizona Store 1204" → assign to timesheet employee "Ali Baig"
```

**Conflict Example (NO match)**:
```
Count file:      "Store 1204"    → tokens: {store, 1204}
Timesheet file:  "Store 1205"    → tokens: {store, 1205}

Match? NO — number tokens conflict (1204 vs 1205)
Result: "Store 1204" → no employee assigned
```

---

## Step 2: Filter Latest Count Records Only

**Function**: `filter_latest_inventory_records(inventory_records)`

**Why**: GFH exports can have multiple counts from same person for same store (recount).

### Group by (Store, Created By)

```python
Group 1: (Store="Arizona 123", CreatedBy="backoffice")
  - Record 1: Created Date=45532.2 (8:00 AM)
  - Record 2: Created Date=45532.5 (12:00 PM) ← LATEST, keep only this
  
Group 2: (Store="Colorado 456", CreatedBy="backoffice")
  - Record 1: Created Date=45531.8 (7:00 PM)  ← LATEST (only one), keep
```

**Result**: Keep only 1 record per (Store, CreatedBy) pair, filtered to highest Created Date.

**Metrics**:
```
Raw inventory rows:      1500
Latest inventory rows:   1450 (after dedup)
Stale rows removed:      50
Latest groups:           150 (150 unique store-person combos)
```

---

## Step 3: Deduplicate by (Store, IMEI)

**Function**: `extract_variances()` deduplication

**Why**: Same IMEI might appear multiple times in same store count.

### Group by (Store, IMEI)

```python
(Store="Arizona 123", IMEI="123456789012345"):
  - Row 1: Timestamp 45532.1
  - Row 2: Timestamp 45532.5 ← LATEST, keep only this
```

**Result**: One row per device per store.

---

## Step 4: Extract Variances

**Variance Extraction Logic**:

```python
for each count record:
    status = record["Status"]
    
    if status in ["Matched", "OK", "Balanced"]:
        SKIP — no variance
    
    if status in ["Deficit", "Surplus", "Mismatch"]:
        norm_store = normalize_store(record["Store"])
        employee = rep_by_store[norm_store]  # From Step 1c matching
        district = district_by_store[norm_store]
        imei = record["Serial #"]
        
        Create VarianceRow:
            store: "Arizona Store 123"
            district: "Arizona"
            imei: "123456789012345"
            product: "iPhone 14 Pro"
            status: "Deficit"
            employee: "Ali Baig"  # From timesheet matching
            
        Add to variances list
```

---

## Step 5: Identify Pending Stores

**Pending Store Logic**:

```python
completed_stores = set of all stores in count file
all_stores = all stores in count file + all stores in display_by_store map

pending_stores = all_stores - completed_stores
```

**Example**:
```
Count file has counts for:  {Arizona 123, Arizona 456, Colorado 789}
But master store list has:  {Arizona 123, Arizona 456, Colorado 789, Houston 111}

Pending (no count yet): {Houston 111}
```

**For Each Pending Store**:
- Assign employee from timesheet matching (if exists)
- Show as "Pending - 0% complete" in audit status
- Include in 15-min polling workflow to check for updates

---

## Complete Data Flow After Both Sheets Imported

```
                    ┌─────────────────────────────────────┐
                    │  Inventory_Count_Result_Details.xlsx │
                    │  (B2B Soft Export)                  │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Filter Latest (by Store+CreatedBy) │
                    │  Keep only 1 per group              │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Deduplicate (by Store+IMEI)       │
                    │  Keep only 1 per device per store   │
                    └──────────────┬──────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
    timesheets_*.xlsx    build_store_maps()    master_store_list.xlsx
    (GFH Telecom)        (fuzzy matching)      (optional, manual)
        │                          │                          │
        ▼                          ▼                          ▼
  Build:                Build:                           Fill gaps:
  - ts_store_→emp      - district_by_store        - district lookup
  - (fuzzily)          - display_by_store         - store display
                       - rep_by_store             names
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Extract Variances                  │
                    │  (join count + employee from TS)   │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Tab 1: Audit Status                │
                    │  - Completed stores (100%)          │
                    │  - Pending stores (0%, polling)     │
                    │  - Employee names from timesheet    │
                    └─────────────────────────────────────┘
                    
                    ┌─────────────────────────────────────┐
                    │  Tab 2: Variances                   │
                    │  - IMEI, Product, Status            │
                    │  - Employee assigned (from TS)      │
                    │  - District, Store                  │
                    └─────────────────────────────────────┘
```

---

## Key Business Rules

### 1. Source of Truth Hierarchy

```
District:    Count file ALWAYS (never from timesheet)
Store:       Count file ALWAYS (never from timesheet)
Employee:    Timesheet matched by store ALWAYS (never from count file)
IMEI/Serial: Count file ALWAYS
Status:      Count file ALWAYS
```

### 2. Duplicate Handling

| Situation | Rule |
|-----------|------|
| Multiple counts, same store, same person | Keep LATEST by Created Date |
| Same IMEI appears twice in same store | Keep LATEST by Created Date |
| Employee at store but no count yet | Create PENDING store row |
| Store in count file but no employee | Show "Unassigned" in employee field |

### 3. Store Matching Tolerance

**Exact Match** ✓:
```
Count:     "Arizona Store 123"
Timesheet: "Arizona Store 123"
Result:    MATCH
```

**Fuzzy Match** ✓:
```
Count:     "Arizona Store 1204"
Timesheet: "Arizona #1204"
Tokens:    {arizona, 1204} ⊂ {arizona, store, 1204}
Result:    MATCH
```

**No Match** ✗:
```
Count:     "Store 1204"
Timesheet: "Store 1205"
Reason:    Number conflict (1204 ≠ 1205)
Result:    NO MATCH → pending store
```

---

## Implementation for V2

### What V2 Needs to Do:

1. **Import B2B Soft Count Details** → parse to records
2. **Import GFH Telesheet** → parse to records
3. **Call `build_store_maps()`** → get district/employee/store maps
4. **Call `filter_latest_inventory_records()`** → dedup by (Store, CreatedBy)
5. **Call `extract_variances()`** → build variance list with matched employees
6. **Populate Tab 1** → show completed + pending stores with employee names
7. **Populate Tab 2** → show variances with employee names from timesheet
8. **Start 15-min polling** → check pending stores for updates

### Database Tables Needed:

```sql
-- Inventory Status (Tab 1)
CREATE TABLE inventory_status (
    id INTEGER PRIMARY KEY,
    store TEXT,
    district TEXT,
    employee TEXT,          -- From timesheet matching
    count_status TEXT,      -- Pending, In Progress, Completed
    percentage_complete INT,
    last_updated TIMESTAMP
);

-- Variances (Tab 2)
CREATE TABLE variance_data (
    id INTEGER PRIMARY KEY,
    store TEXT,
    district TEXT,
    employee TEXT,          -- From timesheet matching
    imei TEXT,
    product TEXT,
    status TEXT,            -- Deficit, Surplus, etc.
    created_by TEXT,        -- From count file (count username)
    created_date TIMESTAMP
);

-- Store/Employee Mapping
CREATE TABLE store_employee_map (
    store_normalized TEXT PRIMARY KEY,
    employee_name TEXT,     -- From timesheet
    district TEXT           -- From count file
);
```

---

## Example End-to-End Flow

### User Imports Both Sheets

**Click**: "Import Count Excel" → select `Inventory_Count_Result_Details.xlsx`
**Result**: 500 count records loaded

**Click**: "Import Timesheet Excel" → select `timesheets_2026-01-01.xlsx`
**Result**: 150 timesheet records loaded

### App Processes Both

1. **Filter count**: 500 → 450 records (50 duplicates removed)
2. **Build maps**:
   - Extract 20 unique (store, employee) pairs from timesheet
   - Extract 25 unique stores from count file
3. **Match stores**: 
   - 25 count stores matched to 20 timesheet stores (5 stores no employee yet)
4. **Extract variances**:
   - 320 "Deficit" rows
   - 40 "Surplus" rows
   - 90 rows skipped (already "Matched")

### Tab 1: Audit Status

| Store | District | Employee | Status | % |
|-------|----------|----------|--------|---|
| Arizona 123 | Arizona | Ali Baig | Completed | 100% |
| Colorado 456 | Colorado East | Shehriyar | Completed | 100% |
| Houston 789 | Houston | Hamza | Pending | 0% |

### Tab 2: Variances

| Store | IMEI | Product | Status | Employee |
|-------|------|---------|--------|----------|
| Arizona 123 | 123456789 | iPhone 14 | Deficit | Ali Baig |
| Colorado 456 | 987654321 | Samsung S23 | Surplus | Shehriyar |

---

## Polling Workflow (15-min cycle)

```
Minute 0: START
  - Send "🔔 Inventory Audit Starting"
  
Minute 15: First Poll
  - Check all pending stores
  - Any new counts? 
  - Update Tab 1 percentages
  
Minute 30: Status Update
  - "Processing: 18/25 stores complete (72%)"
  
Minute 45: Second Poll
  - Check again
  
Minute 60: Final Poll
  - All stores 100%?
  - Send "✅ Audit Complete"
  - Stop polling
```

---

## Summary

**Key Takeaway**: The two sheets work together as:
- **Count file** = Source of truth for what was counted (store, district, IMEI, status)
- **Timesheet file** = Source of truth for WHO was at each store

The app matches them **tolerantly** (fuzzy store matching), deduplicates intelligently (keep latest), and merges the data so you get:
- Audit status with **employee names** from timesheet
- Variances with **employee names** from timesheet
- Pending stores waiting for counts

This prevents orphaned stores and ensures every store has an owner for WhatsApp assignment.

---

**Developed by Abad Umair Channa | Copyright © 2026**
