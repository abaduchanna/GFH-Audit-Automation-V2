"""
Two-Sheet Logic Module for B2B Soft Inventory Audit V2

Implements production-proven patterns from GFH Audit Automation for:
- Store-to-employee mapping (fuzzy matching)
- Latest record filtering (by store + created_by)
- Variance extraction with employee names
- Pending store identification

Based on GFH_Inventory_Audit_Timesheet.py (5841 lines, production-tested)
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


# ===== Normalization Functions =====

def normalize_store(store_name: str) -> str:
    """
    Normalize store name for matching.
    
    "Arizona Store #123" → "arizonstore123"
    "Colorado East 456" → "coloradoeast456"
    """
    if not store_name:
        return ""
    
    # Lowercase, remove spaces, special chars except alphanumeric
    normalized = re.sub(r'[^a-z0-9]', '', store_name.lower().strip())
    return normalized


def normalize_district(district_name: str) -> str:
    """
    Normalize district name for matching.
    
    "Colorado East" → "coloradoeast"
    "Arizona" → "arizona"
    """
    if not district_name:
        return "unknown"
    
    normalized = re.sub(r'[^a-z0-9]', '', district_name.lower().strip())
    return normalized or "unknown"


def normalize_header(header: str) -> str:
    """Normalize column header for matching."""
    return re.sub(r'[^a-z0-9]', '', (header or "").lower())


def safe_text(value) -> str:
    """Safely convert value to string, handling None/empty."""
    if value is None:
        return ""
    return str(value).strip()


def is_summary_row(record: Dict, employee_col: str) -> bool:
    """Check if row is a summary/total row."""
    employee = safe_text(record.get(employee_col, ""))
    
    if not employee:
        return True
    
    # Skip rows with TOTAL or "— " prefix
    if "TOTAL" in employee.upper() or employee.startswith("—") or employee.startswith("--"):
        return True
    
    return False


def is_sim_product(product: str) -> bool:
    """Check if product is a SIM card."""
    if not product:
        return False
    
    product_norm = normalize_header(product)
    return "sim" in product_norm or "simcard" in product_norm


def numeric_excel_date(value) -> float:
    """
    Convert Excel date serial to float for sorting.
    
    Excel stores dates as: 45532.5 = Jan 1, 2025 12:00 PM
    Returns: float for comparison, or -1 if invalid
    """
    try:
        val = float(safe_text(value))
        return val if val > 0 else -1.0
    except ValueError:
        return -1.0


# ===== Store Matching (Fuzzy) =====

def store_name_tokens(normalized_store: str) -> Tuple[str, ...]:
    """
    Extract alphanumeric tokens from normalized store name.
    
    "arizonstore1204" → ("arizona", "store", "1204")
    Deduplicates and maintains order.
    """
    if not normalized_store:
        return ()
    
    # Find all alphanumeric sequences
    tokens = re.findall(r'[a-z0-9]+', normalized_store)
    
    # Deduplicate while maintaining order
    seen = set()
    unique_tokens = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique_tokens.append(token)
    
    return tuple(unique_tokens)


def match_store_employee(
    norm_store: str, 
    ts_store_to_employee: Dict[str, str]
) -> str:
    """
    Fuzzy match a store to timesheet employee.
    
    Strategy:
    1. Exact normalized-store match first
    2. Token subset match (tolerant of spelling differences)
    3. Avoid number conflicts (1204 ≠ 1205)
    
    Args:
        norm_store: Normalized store from count file
        ts_store_to_employee: {normalized_store: employee_name} from timesheet
        
    Returns:
        Employee name, or "" if no match
    """
    if not norm_store or not ts_store_to_employee:
        return ""
    
    # Try exact match first
    if norm_store in ts_store_to_employee:
        return ts_store_to_employee[norm_store]
    
    # Try fuzzy token matching
    target_tokens = set(store_name_tokens(norm_store))
    if not target_tokens:
        return ""
    
    best_name = ""
    best_overlap = 0
    best_len = -1
    
    for ts_norm, employee in ts_store_to_employee.items():
        if not ts_norm or not employee:
            continue
        
        ts_tokens = set(store_name_tokens(ts_norm))
        if not ts_tokens:
            continue
        
        # Check if one is subset of other (no number conflict)
        if target_tokens <= ts_tokens or ts_tokens <= target_tokens:
            overlap = len(target_tokens & ts_tokens)
            
            # Pick best overlap, fallback to shortest name
            if overlap > best_overlap or (overlap == best_overlap and best_len != -1 and len(ts_norm) < best_len):
                best_name = employee
                best_overlap = overlap
                best_len = len(ts_norm)
            elif best_len == -1:
                best_name = employee
                best_overlap = overlap
                best_len = len(ts_norm)
    
    return best_name


# ===== Store Mapping =====

def build_timesheet_store_map(timesheet_records: List[Dict]) -> Dict[str, str]:
    """
    Build {normalized_store: employee_name} map from timesheet.
    
    Logic:
    - Skip summary/total rows
    - If multiple employees per store: pick latest Clock In time
    - Fallback to row order if Clock In missing
    
    Args:
        timesheet_records: List of timesheet row dicts
        
    Returns:
        {normalized_store: employee_name} mapping
    """
    ts_store_to_employee = {}
    
    if not timesheet_records:
        return ts_store_to_employee
    
    # Auto-detect columns
    sample = timesheet_records[0]
    store_col = None
    emp_col = None
    clock_col = None
    
    for key in sample.keys():
        key_norm = normalize_header(key)
        if "store" in key_norm:
            store_col = key
        if any(x in key_norm for x in ["employee", "salesperson", "rep"]):
            emp_col = key
        if "clock" in key_norm and "in" in key_norm:
            clock_col = key
    
    if not store_col or not emp_col:
        logger.warning("Could not detect Store or Employee column in timesheet")
        return ts_store_to_employee
    
    # Track latest Clock In per store
    latest_ts = {}
    
    for idx, rec in enumerate(timesheet_records):
        emp_raw = safe_text(rec.get(emp_col, ""))
        
        # Skip TOTAL/summary rows
        if is_summary_row(rec, emp_col):
            continue
        
        if not emp_raw:
            continue
        
        store_raw = safe_text(rec.get(store_col, ""))
        norm_store = normalize_store(store_raw)
        
        if not norm_store:
            continue
        
        # Use Clock In if available, else use row order
        clock_in = safe_text(rec.get(clock_col, "")) if clock_col else ""
        score = numeric_excel_date(clock_in) if clock_in else float(idx)
        
        # Keep latest by score
        if norm_store not in latest_ts or score > latest_ts[norm_store]:
            ts_store_to_employee[norm_store] = emp_raw
            latest_ts[norm_store] = score
    
    logger.info(f"Built timesheet map: {len(ts_store_to_employee)} stores")
    return ts_store_to_employee


def build_store_maps(
    inventory_records: List[Dict],
    timesheet_records: List[Dict]
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Build complete store lookup maps.
    
    Returns:
        (district_by_store, display_by_store, rep_by_store)
        
    Where:
        - district_by_store: {norm_store: district} from count file (source of truth)
        - display_by_store: {norm_store: display_name} from count file
        - rep_by_store: {norm_store: employee} from timesheet (fuzzy matched)
    """
    # Build timesheet map first
    ts_store_to_employee = build_timesheet_store_map(timesheet_records)
    
    # Extract from count file
    district_by_store = {}
    display_by_store = {}
    rep_by_store = {}
    
    if not inventory_records:
        return district_by_store, display_by_store, rep_by_store
    
    sample = inventory_records[0]
    store_col = None
    district_col = None
    
    for key in sample.keys():
        key_norm = normalize_header(key)
        if "store" in key_norm:
            store_col = key
        if "district" in key_norm:
            district_col = key
    
    if not store_col:
        logger.warning("Could not detect Store column in inventory records")
        return district_by_store, display_by_store, rep_by_store
    
    # Extract store info from count file
    for rec in inventory_records:
        store_raw = safe_text(rec.get(store_col, ""))
        norm_store = normalize_store(store_raw)
        
        if not norm_store:
            continue
        
        # Store display name
        display_by_store[norm_store] = store_raw
        
        # Store district (if present)
        if district_col:
            district = safe_text(rec.get(district_col, ""))
            if district and normalize_district(district) != "unknown":
                district_by_store[norm_store] = district
    
    # Match employees to stores (fuzzy)
    for norm_store in display_by_store.keys():
        employee = match_store_employee(norm_store, ts_store_to_employee)
        if employee:
            rep_by_store[norm_store] = employee
    
    logger.info(f"Built store maps: {len(district_by_store)} districts, {len(rep_by_store)} reps")
    return district_by_store, display_by_store, rep_by_store


# ===== Deduplication =====

def filter_latest_inventory_records(
    inventory_records: List[Dict]
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Keep only latest record per (Store, CreatedBy) group.
    
    Reasoning: GFH exports can have multiple counts from same person for same store.
    We want the LATEST by Created Date.
    
    Returns:
        (filtered_records, metrics_dict)
    """
    metrics = {
        "raw_rows": len(inventory_records),
        "latest_rows": 0,
        "stale_rows": 0,
        "groups": 0,
    }
    
    if not inventory_records:
        return [], metrics
    
    # Auto-detect columns
    sample = inventory_records[0]
    store_col = None
    created_by_col = None
    created_date_col = None
    
    for key in sample.keys():
        key_norm = normalize_header(key)
        if "store" in key_norm:
            store_col = key
        if "created" in key_norm and "by" in key_norm:
            created_by_col = key
        if "created" in key_norm and ("date" in key_norm or "time" in key_norm):
            created_date_col = key
    
    if not store_col or not created_by_col or not created_date_col:
        logger.warning("Could not auto-detect Store/CreatedBy/CreatedDate columns")
        return inventory_records, metrics
    
    # Group by (Store, CreatedBy) and track latest score
    latest_by_group = {}
    scores = []
    
    for idx, rec in enumerate(inventory_records):
        store_norm = normalize_store(safe_text(rec.get(store_col, "")))
        created_by = safe_text(rec.get(created_by_col, "")).lower()
        
        group_key = (store_norm, created_by)
        score = numeric_excel_date(rec.get(created_date_col, ""))
        
        if score < 0:
            score = float(idx) / 1000000.0
        
        scores.append((group_key, score))
        
        if group_key not in latest_by_group or score > latest_by_group[group_key]:
            latest_by_group[group_key] = score
    
    # Keep only records matching latest score in group
    filtered = []
    for rec, (group_key, score) in zip(inventory_records, scores):
        latest_score = latest_by_group.get(group_key, score)
        
        # Use small epsilon for float comparison
        if abs(score - latest_score) <= 0.0000001:
            filtered.append(rec)
    
    metrics["latest_rows"] = len(filtered)
    metrics["stale_rows"] = len(inventory_records) - len(filtered)
    metrics["groups"] = len(latest_by_group)
    
    logger.info(f"Filtered inventory: {len(filtered)} latest records (removed {metrics['stale_rows']} stale)")
    return filtered, metrics


# ===== Variance Extraction =====

def extract_variances(
    inventory_records: List[Dict],
    timesheet_records: List[Dict],
    district_by_store: Optional[Dict[str, str]] = None
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Extract variance rows from count details with employee names.
    
    Logic:
    - Skip "Matched", "OK", "Balanced" status (already good)
    - Skip SIM products
    - Skip empty IMEI
    - Join with employee names from timesheet
    
    Returns:
        (variance_rows, metrics)
    """
    metrics = {
        "raw_rows": len(inventory_records),
        "variances_extracted": 0,
        "skipped_matched": 0,
        "skipped_sim": 0,
        "skipped_no_imei": 0,
    }
    
    if not inventory_records:
        return [], metrics
    
    # Build store maps
    dist_by_store, display_by_store, rep_by_store = build_store_maps(
        inventory_records, 
        timesheet_records
    )
    
    # Use provided or built district map
    if district_by_store is None:
        district_by_store = dist_by_store
    
    # Auto-detect columns
    sample = inventory_records[0]
    store_col = None
    product_col = None
    imei_col = None
    status_col = None
    created_by_col = None
    created_date_col = None
    
    for key in sample.keys():
        key_norm = normalize_header(key)
        if "store" in key_norm and "store" not in store_col if store_col else True:
            store_col = key
        if any(x in key_norm for x in ["product", "description"]):
            product_col = key
        if any(x in key_norm for x in ["serial", "imei", "esn"]):
            imei_col = key
        if "status" in key_norm:
            status_col = key
        if "created" in key_norm and "by" in key_norm:
            created_by_col = key
        if "created" in key_norm and "date" in key_norm:
            created_date_col = key
    
    if not all([store_col, status_col, imei_col]):
        logger.error("Missing required columns: Store, Status, IMEI")
        return [], metrics
    
    # Filter latest records first
    filtered_records, filter_metrics = filter_latest_inventory_records(inventory_records)
    
    # Extract variances
    variances = []
    
    for rec in filtered_records:
        status = safe_text(rec.get(status_col, ""))
        
        # Skip matched status
        if normalize_header(status) in ["matched", "ok", "balanced"]:
            metrics["skipped_matched"] += 1
            continue
        
        imei = safe_text(rec.get(imei_col, ""))
        
        # Skip empty IMEI
        if not imei:
            metrics["skipped_no_imei"] += 1
            continue
        
        # Skip SIM products
        product = safe_text(rec.get(product_col, "")) if product_col else ""
        if is_sim_product(product):
            metrics["skipped_sim"] += 1
            continue
        
        # Extract variance with matched employee
        store_raw = safe_text(rec.get(store_col, ""))
        norm_store = normalize_store(store_raw)
        
        variance = {
            "store": display_by_store.get(norm_store, store_raw),
            "district": district_by_store.get(norm_store, "Unknown"),
            "employee": rep_by_store.get(norm_store, ""),  # From timesheet matching
            "imei": imei,
            "product": product,
            "status": status,
            "created_by": safe_text(rec.get(created_by_col, "")) if created_by_col else "",
            "created_date": safe_text(rec.get(created_date_col, "")) if created_date_col else "",
        }
        
        variances.append(variance)
    
    metrics["variances_extracted"] = len(variances)
    logger.info(f"Extracted {len(variances)} variances")
    return variances, metrics


def identify_pending_stores(
    inventory_records: List[Dict],
    timesheet_records: List[Dict],
    all_possible_stores: Optional[List[str]] = None
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Identify stores without counts yet.
    
    Pending stores = all_stores - stores_in_count_file
    
    Args:
        inventory_records: Count detail records
        timesheet_records: Timesheet records
        all_possible_stores: Optional list of all stores (if not in count file)
        
    Returns:
        (pending_store_rows, metrics)
    """
    metrics = {
        "completed_stores": 0,
        "pending_stores": 0,
        "total_stores": 0,
    }
    
    # Build maps
    district_by_store, display_by_store, rep_by_store = build_store_maps(
        inventory_records,
        timesheet_records
    )
    
    # Find completed stores (those in count file)
    completed_norms = set(display_by_store.keys())
    
    # All stores = completed + from all_possible_stores
    all_norms = set(display_by_store.keys())
    if all_possible_stores:
        for store_raw in all_possible_stores:
            norm = normalize_store(store_raw)
            if norm:
                all_norms.add(norm)
    
    # Pending = all - completed
    pending_norms = all_norms - completed_norms
    
    # Build pending store rows
    pending_stores = []
    for norm_store in sorted(pending_norms):
        pending = {
            "store": display_by_store.get(norm_store, norm_store),
            "district": district_by_store.get(norm_store, "Unknown"),
            "employee": rep_by_store.get(norm_store, ""),  # From timesheet
            "status": "Pending",
            "percentage_complete": 0,
            "last_checked": None,
        }
        pending_stores.append(pending)
    
    metrics["completed_stores"] = len(completed_norms)
    metrics["pending_stores"] = len(pending_stores)
    metrics["total_stores"] = len(all_norms)
    
    logger.info(f"Identified {len(pending_stores)} pending stores")
    return pending_stores, metrics


# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
