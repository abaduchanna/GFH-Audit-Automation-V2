# Developed by Abad Umair Channa  |  Copyright (c) 2026. All rights reserved.
#!/usr/bin/env python3
"""
GFH Telecom LLC Accessories Ordering Automation - GUI FINAL
- Handles final checkout alert ("Are you sure you want to Place Order?")
- Separates USB-A to Lightning and Type-C to Lightning.
- Cables & Chargers: Uses strict mathematical calculation (Branch and Bound DFS) 
  to find the absolute lowest cost combination (Single, Bundle, or Mix) from hardcoded SKUs only.
- Car chargers: <= $3.00 per unit.
- Wall chargers/Adaptors: No limit, picks absolute lowest cost from hardcoded SKUs.
- Phone cases/glass: scraped normally.
- Includes dynamic Store Management (Add, Edit, Delete).
- Added reliable mouse scrolling in the Store Selection list.
"""

import time
from datetime import datetime
import os
import threading
import queue
import webbrowser
from pathlib import Path
import pandas as pd
import numpy as np
import re
import sys
import traceback
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import tkinter as tk
from theme_manager import ThemeManager, apply_theme_to_window, create_theme_toggle_button, get_copyright_year
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText

import subprocess as _acc_sp
if getattr(sys, "frozen", False):
    _acc__run, _acc__popen = _acc_sp.run, _acc_sp.Popen
    def _acc__is_pip(cmd):
        try:
            return (isinstance(cmd, (list, tuple)) and len(cmd) >= 3
                    and str(cmd[0]) == sys.executable and cmd[1] == "-m"
                    and str(cmd[2]) == "pip")
        except Exception:
            return False
    def _acc_run(cmd, *a, **k):
        if _acc__is_pip(cmd):
            raise RuntimeError("pip install disabled in packaged app")
        return _acc__run(cmd, *a, **k)
    def _acc_popen(cmd, *a, **k):
        if _acc__is_pip(cmd):
            raise RuntimeError("pip install disabled in packaged app")
        return _acc__popen(cmd, *a, **k)
    _acc_sp.run = _acc_run
    _acc_sp.Popen = _acc_popen

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None

# PDF reading support (pdfplumber preferred; pypdf as fallback)
try:
    import pdfplumber as _pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False
    # Try to auto-install pdfplumber silently
    try:
        import subprocess as _sp
        _sp.run(
            [sys.executable, "-m", "pip", "install", "pdfplumber", "--quiet",
             "--disable-pip-version-check"],
            capture_output=True, timeout=120,
        )
        import pdfplumber as _pdfplumber
        _HAS_PDFPLUMBER = True
    except Exception:
        pass

try:
    from pypdf import PdfReader as _PdfReader
    _HAS_PYPDF = True
except ImportError:
    _HAS_PYPDF = False
    try:
        import subprocess as _sp
        _sp.run(
            [sys.executable, "-m", "pip", "install", "pypdf", "--quiet",
             "--disable-pip-version-check"],
            capture_output=True, timeout=120,
        )
        from pypdf import PdfReader as _PdfReader
        _HAS_PYPDF = True
    except Exception:
        pass

# -------------------------------------------------------------------
# HARDCODED PRODUCT DATABASE
# -------------------------------------------------------------------
PRODUCTS = {
    # ========== CABLES ==========
    "PD10FTRIV-BK": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "SHPD10FTRIV-BLK": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "PD10FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "SHPD10FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "PD10FTRIV-BRAD": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "SHPD10FTRIV-BRAD": {"type": "cable", "subtype": "c_to_c", "pack_size": 10, "price": 10.0},
    "PD3FTRIV-BK": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "SHPD3FTRIV-BLK": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "PD3FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "SHPD3FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "PD3FTRIV-BRAD": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "SHPD3FTRIV-BRAD": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "PD5FTRIV-BK": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "SHPD5FTRIV-BLK": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "PD5FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "SHPD5FTRIV-WHT": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "PD5FTRIV-BRAD": {"type": "cable", "subtype": "c_to_c", "pack_size": 20, "price": 10.0},
    "AMPUSB-TC-BK": {"type": "cable", "subtype": "a_to_c", "pack_size": 1, "price": 1.25},
    "AMPUSB-TC-WT": {"type": "cable", "subtype": "a_to_c", "pack_size": 1, "price": 1.25},
    "AMP-PD-BK": {"type": "cable", "subtype": "c_to_c", "pack_size": 1, "price": 1.25},
    "AMP-PD-WT": {"type": "cable", "subtype": "c_to_c", "pack_size": 1, "price": 1.25},
    "AUKEY-CBNCC2-29": {"type": "cable", "subtype": "c_to_c", "pack_size": 1, "price": 2.50},
    "10FTRIV-USB-BK": {"type": "cable", "subtype": "a_to_c", "pack_size": 10, "price": 5.0},
    "SH10FTRIV-USB-BLK": {"type": "cable", "subtype": "a_to_c", "pack_size": 10, "price": 5.0},
    "SH10FTRIV-USB-WHT": {"type": "cable", "subtype": "a_to_c", "pack_size": 10, "price": 5.0},
    "10FTRIV-USB-BRAD": {"type": "cable", "subtype": "a_to_c", "pack_size": 10, "price": 5.0},
    "3FTRIV-USB-BK": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 5.0},
    "SH3FTRIV-USB-BLK": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 5.0},
    "3FTRIV-USB-WHT": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 5.0},
    "SH3FTRIV-USB-WHT": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 5.0},
    "SH3FTRIV-USB-BRAD": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 5.0},
    "SH5FTRIV-USB-BLK": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 7.0},
    "5FTRIV-USB-WHT": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 7.0},
    "5FTRIV-USB-BRAD": {"type": "cable", "subtype": "a_to_c", "pack_size": 20, "price": 7.0},
    "BROOKBK13CLTB6-WHITE-35": {"type": "cable", "subtype": "c_to_l", "pack_size": 1, "price": 4.99},
    "EGC1284M-EGTECH10": {"type": "cable", "subtype": "a_to_c", "pack_size": 1, "price": 2.50},
    "EGC37-EGTECH11": {"type": "cable", "subtype": "c_to_c", "pack_size": 1, "price": 1.75},
    "ESEEKG12A-WHITE-38": {"type": "cable", "subtype": "a_to_c", "pack_size": 1, "price": 1.50},

    # ========== CAR CHARGERS ==========
    "AMPCAR20WT-BK": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 2.50},
    "AMPCAR20WT-WT": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 2.50},
    "AMPCMB-CAR-BK": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 3.75},
    "AMPCMB-CAR-WT": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 3.75},
    "ESEEKC15-WHITE-44": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 2.50},
    "ESEEKC15-BK-43": {"type": "charger", "charger_type": "car", "pack_size": 1, "price": 2.50},
    "ESEEKC10BS-BK-47": {"type": "charger", "charger_type": "car", "pack_size": 12, "price": 30.0},

    # ========== WALL CHARGERS ==========
    "AMPDUAL20WT-BK": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.45},
    "AMPDUAL20WT-WT": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.45},
    "BLING20WGG-BK-1": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.50},
    "BLING20WGG-GOLD-2": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.50},
    "BLING20WGG-SILVER-3": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.50},
    "BROOKBK112P20F-BLACK-15": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.99},
    "BROOKBK11PD20-BLACK-19": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.99},
    "BROOKBK11PD20-WHITE-20": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.99},
    "BROOKBK112P20F-WHITE-16": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.99},
    "BROOKBK11PD30-BLACK-17": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.99},
    "BROOKBK11PD30-WHITE-18": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.99},
    "BROOKBK112P30F-WHITE-14": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.99},
    "AMPCMB20WT-BK": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.95},
    "AMPCMB20WT-WT": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.95},
    "EGC08-EGTECH1": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 2.25},
    "EGC41F-EGTECH2": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 2.50},
    "PEANUT20W-WHITE-1": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.95},
    "PHONESUIT20W-WHITE-2": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.99},
    "PHONE30W-WHITE-15": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 6.99},
    "UPLUSHOME-WHITE-1": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.50},
    "UPLUS40WHOMEULTRA-WHITE-12": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.99},
    "ESEEKT32UC-WHITE-33": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.50},
    "ESEEKT45UC-WHITE-39": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.99},
    "ESEEKGOT32UB-WHITE-15": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 3.50},
    "ESEEKT45UB-WHITE-42": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 4.99},
    "VQT16-WHT": {"type": "charger", "charger_type": "wall", "pack_size": 1, "price": 5.45},
    "ESEEKT32US-WHITEBOX-48": {"type": "charger", "charger_type": "wall", "pack_size": 12, "price": 36.0},
}

# -------------------------------------------------------------------
# STORE ADDRESSES & MANAGEMENT
# -------------------------------------------------------------------
DEFAULT_ADDRESSES = {
    "MLK": "7111 Martin Luther King Blvd Ste B, Total Wireless, Houston, TEXAS, USA - 77033",
    "Tidwell": "8615 Tidwell Road Ste E, Total Wireless, Houston, TEXAS, USA - 77028",
    "Mississippi": "15062 E Mississippi Ave, Total Wireless , Aurora, COLORADO, USA - 80012",
    "E Iliff": "17150 E. Iliff Ave., Unit C1A, CO 80013 , Total Wireless , Aurora, COLORADO, USA - 80013",
    "Peoria": "4490 Peoria St Total Wireless, Denver, COLORADO, USA - 80239",
    "Bromley": "530 E Bromley Ln Suite 105 Total Wireless, Brighton, COLORADO, United States - 80601",
    "Wadsworth": "3214 S Wadsworth Blvd Total Wireless Suite A, Denver, CO 80227, Denver, COLORADO, United States - 80227",
    "FM1960": "4765 FM 1960 RD WEST SUITE B HOUSTON TEXAS 77069 (total wireless), Humble, TX, United States - 77069",
    "Rayford": "466 Rayford Rd Total Wireless (Suite 101) Spring, TX 77386, spring, TX, United States - 77386",
    "Melody": "12024 Melody Dr, Denver, CO 80234 Total Wireless , Denver, COLORADO, United States - 80234",
    "W88": "7641 W 88th Ave, Westminster, CO 80005 Total Wireless, westminster, COLORADO, United States - 80005",
    "Belleview": "2749 W Belleview Ave Littleton, CO 80123 Total Wireless, Littleton, COLORADO, United States - 80123",
    "Quebec": "2280 S Quebec St Denver, CO 80231 suite G2 , total wireless, Denver, COLORADO, United States - 80231",
    "Hollywood": "2508 Hollywood Ave total wireless, Shreveport, LA, United States - 71108",
    "Jewella": "4001 Jewella Ave Ste B total wireless, Shreveport, LA , United States - 71109",
    "Airline": "1131 Airline Drive Ste D total wireless, Bossier City, LA, United States - 71112",
    "Colfax": "7520 E. Colfax Ave, Total Wireless , Denver, COLORADO, UNITED STATES - 80220",
    "Englewood": "475 W Hampden Ave Suite B total wireless, ENGLEWOOD, COLORADO, UNITED STATES - 80110",
    "Lakewood": "98 Wadsworth Blvd unit #127 total wireless, LAKEWOOD, Colorado, United States - 80226",
    "Commerce City": "4952 E 62nd Ave Suite A6 Total Wireless, Commerce City, COLORADO, United States - 80022",
    "Boulder": "1676 30th Street Boulder total wireless, Boulder, COLORADO, United States - 80303",
    "Southwest": "8104 Southwest Fwy Suite F, total wireless, Houston, Texas, United States - 77074",
    "Phoenix": "8945 N 43rd Ave total wireless, PHOENIX, ARIZONA, USA - 85051",
    "Federal": "4344 N Federal Blvd, Total Wireless , Denver, Colorado, USA - 80211",
    "Kipling": "1550 Kipling St Total Wireless , Denver, Colorado, USA - 80215",
    "Gilbert": "323 N Gilbert Rd. #107 Total Wireless, Mesa, Arizona, USA - 85203",
    "Rural": "6323 S Rural Rd Total Wireless, Tempe, Arizona, USA - 85283",
    "Glendale": "6442 W Glendale Ave Total Wireless, Glendale, Arizona, USA - 85301",
    "Gulf": "5819 Gulf Freeway, Suite 400 Total Wireless, Houston, Texas, USA - 77023",
    "Thomas": "3517 E Thomas Rd Total Wireless, Phoenix, Arizona, USA - 85018",
    "Highway 6": "6608 Hwy 6 N Suite E Houston Total Wireless, Houston, Texas, USA - 77084",
    "New Colfax": "15355 E Colfax Ave, Unit F Total Wireless, Aurora, Colorado, USA - 80011",
    "South Central": "5233 South Central Ave, Unit A-09 Total Wireless, Phoenix, Arizona, USA - 85040",
    "Nolensville": "4702 Nolensville Pk Suite B Total Wireless, Nashville, Tennessee, USA - 37211",
    "Bethany": "2722 W Bethany Home Rd Total Wireless, Phoenix, Arizona, USA - 85017",
    "Elliot": "1320 W Elliot Rd Unit 103 Total Wireless, Tempe, Arizona, USA - 85284",
    "N 35": "4812 N 35th Ave Total Wireless, Phoenix, Arizona, USA - 85017",
    "McAllister": "2016 N McAllister Ave, Shehriyar Ali, Tempe, Arizona, USA - 85288",
    "N 51": "2828 N 51st Ave Suite 100 Total Wireless, Tempe, Arizona, USA - 85035",
    "N 19": "18631 N 19th Ave #170 Total Wireless, Phoenix, Arizona, USA - 85027",
    "Westheimer": "7529 Westheimer Rd Total Wireless, Houston, Texas, USA - 77063",
    "Windermere": "12149 FM-1960 W Total wireless, Houston, Texas, USA - 77065",
    "Crosstimbers": "20 E Crosstimbers Rd Total wireless, Houston, Texas, USA - 77022",
    "South Post Oak": "16101 S Post Oak Rd Total wireless, Houston, Texas, USA - 77053",
    "104 Tidwell": "104 Tidwell, Suite F Total Wireless, Houston, Texas, USA - 77022",
    "Fry Rd": "5502 N Fry Rd Suite D Total wireless, Katy, Texas, USA - 77449",
    "South Havana": "1155 S Havana St Suite 11 Total wireless, Aurora, Colorado, USA - 80012",
    "Federal Heights": "1886 W 92nd Ave Total wireless, Federal Heights, Colorado, USA - 80260",
    "Mount View": "5335 Mt View Rd 14 Total Wireless, Antioch, Tennessee, USA - 37013",
    "W Thomas": "7333 W Thomas Rd, 86 Total Wireless, Phoenix, Arizona, USA - 85033",
    "Main Store": "9150 S Main St Suite C Total Wireless, Houston, Texas, USA - 77025"
    
}

ADDRESSES = {}

def get_stores_file_path():
    try:
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "stores.json")


def _acc_norm_addr(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _acc_addr_features(s):
    n = _acc_norm_addr(s)
    m = re.match(r"(\d+)", n)
    num = m.group(1) if m else ""
    zips = re.findall(r"\b(\d{5})\b", n)
    zipc = zips[-1] if zips else ""
    toks = set(t for t in n.split() if len(t) >= 3 and not t.isdigit())
    return num, zipc, toks


def _acc_address_score(store_addr, label):
    snum, szip, stoks = _acc_addr_features(store_addr)
    lnum, lzip, ltoks = _acc_addr_features(label)
    score = 0
    if snum and snum == lnum:
        score += 5
    if szip and szip == lzip:
        score += 3
    score += len(stoks & ltoks)
    return score

def load_stores():
    global ADDRESSES
    path = get_stores_file_path()
    loaded_successfully = False
    
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validates that it's a dictionary AND it has at least 1 store inside
                if isinstance(data, dict) and len(data) > 0:
                    ADDRESSES = data
                    loaded_successfully = True
        except Exception:
            pass
            
    # Fallback to default if the file is missing, empty, or corrupt
    if not loaded_successfully:
        ADDRESSES = DEFAULT_ADDRESSES.copy()
        save_stores()

def save_stores():
    path = get_stores_file_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ADDRESSES, f, indent=4)
    except Exception:
        pass


LOG_CALLBACK = None
PROGRESS_CALLBACK = None

def set_log_callback(callback):
    global LOG_CALLBACK
    LOG_CALLBACK = callback

def set_progress_callback(callback):
    global PROGRESS_CALLBACK
    PROGRESS_CALLBACK = callback

def emit_progress(**payload):
    if PROGRESS_CALLBACK:
        try:
            PROGRESS_CALLBACK(payload)
        except Exception:
            pass

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    if LOG_CALLBACK:
        try:
            LOG_CALLBACK(line)
        except Exception:
            pass

def safe_int(value):
    if pd.isna(value) or value is None:
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0

class CPWHOrderAutomator:
    def __init__(self, username=None, password=None, stop_event=None):
        self.username = username or "[REDACTED]"
        self.password = password or "[REDACTED]"
        self.stop_event = stop_event or threading.Event()
        log("Setting up Microsoft Edge browser...")
        options = Options()
        options.add_argument("--start-maximized")
        options.page_load_strategy = 'eager'
        try:
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e1:
            log(f"⚠️ Auto driver failed: {e1}")
            log("🔄 Trying native system driver...")
            try:
                self.driver = webdriver.Edge(options=options)
            except Exception as e2:
                log(f"❌ CRITICAL: Browser failed to launch.")
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "Driver Error",
                    "Failed to start Microsoft Edge.\n\nPlease open your command prompt and run:\npip install --upgrade selenium webdriver-manager"
                )
                sys.exit()
        self.wait = WebDriverWait(self.driver, 10)
        log("✅ Edge browser started successfully!")

        self.blacklist_colors = ['red']
        self.male_colors = ['black', 'blue', 'grey', 'gray', 'brown', 'silver', 'charcoal', 'navy']
        self.female_colors = ['pink', 'purple', 'rose', 'gold', 'clear', 'magenta', 'teal', 'mint', 'yellow', 'burgundy']
        self.female_keywords = [
            'diamond', 'butterfly', 'epoxy', 'glitter', 'shimmer', 'cute',
            'pearl', 'flower', 'floral', 'bling', 'rhinestone', 'women', 'girl',
            'jewel', 'crystal', 'leopard', 'daisy', 'lepoard'
        ]
        self.case_max_price = 3.00
        self.glass_max_price = 1.50
        self.soft_limit = 500.00
        self.hard_limit = 550.00
        self.current_limit = self.soft_limit
        self.camera_skip_keywords = [
            'camera', 'camera lens', 'camera glass', 'camera lense',
            'lense glass', 'lens glass', 'camera protector', 'lens protector'
        ]
        self.skip_excel_keywords = [
            'speaker', 'airpod', 'smart watch', 'watch',
            'other accessories', 'car phone holder'
        ]
        self.cable_charger_url = "https://www.cpwhwireless.com/latest-models?model=CABLE+CHARGER+POWERBANK&a=4"

    # -----------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------
    def handle_alerts(self, wait_time=0.5):
        try:
            WebDriverWait(self.driver, wait_time).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            alert.accept()
            return True
        except:
            return False

    def login(self):
        log("Navigating to login page...")
        self.driver.get("https://www.cpwhwireless.com/login")
        try:
            email_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            email_input.clear()
            email_input.send_keys(self.username)
            password_input = self.driver.find_element(By.NAME, "password")
            password_input.clear()
            password_input.send_keys(self.password)
            password_input.submit()
            self.wait.until(EC.presence_of_element_located((By.ID, "search")))
            log("✅ Login successful!")
            time.sleep(4)
            return True
        except Exception as e:
            log(f"❌ Login failed: {e}")
            return False

    def normalize_model_name(self, name):
        n = name.lower()
        n = n.replace('sumsung', 'samsung')
        if 'g play' in n or ('moto g 5g' in n) or ('moto g (2026)' in n):
            return "Motorola Moto G 5G 2025 / 2026 / G Play 2026"
        if 'edge 2025' in n:
            return "Motorola Edge 2025"
        if 'a37' in n: return "Samsung Galaxy A37 5G"
        if 'stylus' in n: return "Motorola Moto G Stylus 5G 2025 2026"
        if 'power' in n: return "Motorola Moto G Power 5G 2025 2026"
        if 'razr' in n: return "Motorola Razr 2025 2024"
        if 'a17' in n: return "Samsung A17 5G"
        if 'a16' in n: return "Samsung A16 5G"
        if 'a36' in n or 'a56' in n: return "Samsung Galaxy A36 / A56"
        if 'a26' in n: return "Samsung Galaxy A26 5G"
        if 'a57' in n: return "Samsung Galaxy A57"
        if 's25 fe' in n: return "Samsung s25 FE"
        if 's26 ultra' in n: return "Samsung s26 Ultra"
        if 's26 plus' in n: return "Samsung s26 Plus"
        if 's26' in n and 'ultra' not in n and 'plus' not in n: return "Samsung s26"
        if '16e' in n or '17e' in n: return "Apple iPhone 16E / iPhone 17E"
        if '17 pro max' in n: return "Apple iPhone 17 Pro Max"
        if '17 pro' in n and 'max' not in n: return "Apple iPhone 17 Pro"
        if '17 air' in n: return "Apple iPhone 17 Air"
        if 'iphone 17' in n and 'pro' not in n and 'air' not in n and 'e' not in n: return "Apple iPhone 17"
        if '14' in n and '13' in n: return "Apple iPhone 14 / Apple iPhone 13"
        if '15' in n and 'plus' not in n and 'pro' not in n: return "Apple iPhone 15"
        if 'tab a9' in n or 'tab a11' in n: return "Samsung TAB A9 Plus / A11 Plus 5G 11 inch"
        return name.replace('Sumsung', 'Samsung').replace('sumsung', 'Samsung')

    def search_phone_model(self, raw_model_name):
        model_name = self.normalize_model_name(raw_model_name)
        for attempt in range(2):
            try:
                self.handle_alerts(0.1)
                if not self.driver.find_elements(By.ID, "search"):
                    self.driver.get("https://www.cpwhwireless.com/")
                    time.sleep(1)
                search_box = self.wait.until(EC.element_to_be_clickable((By.ID, "search")))
                search_box.clear()
                search_box.send_keys(model_name)
                search_box.submit()
                try:
                    self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".col-md-3.pro-1")))
                    log(f"✓ Searched: {model_name}. Loading all items...")
                    last_height = self.driver.execute_script("return document.body.scrollHeight")
                    for i in range(8):
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        new_height = self.driver.execute_script("return document.body.scrollHeight")
                        if new_height == last_height:
                            break
                        last_height = new_height
                    self.driver.execute_script("window.scrollTo(0, 0);")
                except:
                    return False
                return True
            except Exception as e:
                log(f"  Search attempt {attempt + 1} failed")
                self.driver.get("https://www.cpwhwireless.com/")
                time.sleep(1)
        return False

    def is_correct_model_exact(self, full_text, target_model):
        text_lower = full_text.lower()
        target_lower = target_model.lower()
        all_mods = ['pro', 'max', 'plus', 'ultra', 'fe', 'air', 'mini', 'stylus', 'power', 'play', 'edge', 'razr']
        required_mods = [m for m in all_mods if m in target_lower]
        for req in required_mods:
            if req not in text_lower:
                return False
        nums = re.findall(r'\b(?:[as]?\d{2})\b', target_lower)
        nums = [n for n in nums if n not in ['20', '24', '25', '26', '5g', '4g']]
        if not nums:
            return True
        forbidden_mods = [m for m in all_mods if m not in target_lower]
        needs_e = 'e' in target_lower.split() or '16e' in target_lower or '17e' in target_lower
        for num in nums:
            matches = list(re.finditer(r'(?:ip)?' + re.escape(num), text_lower))
            if not matches:
                continue
            for match in matches:
                end_pos = match.end()
                context_after = text_lower[end_pos:end_pos+15]
                is_dirty = False
                for f_mod in forbidden_mods:
                    if re.search(r'^[\s\-]*' + f_mod + r'\b', context_after):
                        is_dirty = True
                        break
                if not needs_e and re.search(r'^[\s\-]*e\b', context_after):
                    is_dirty = True
                if not is_dirty:
                    return True
        return False

    def has_camera_keyword(self, full_text):
        for keyword in self.camera_skip_keywords:
            if keyword in full_text:
                return True
        return False

    def is_screen_glass(self, full_text):
        if self.has_camera_keyword(full_text):
            return False
        if 'privacy' in full_text or 'tempered glass' in full_text or 'screen protector' in full_text:
            return True
        return False

    def is_phone_case(self, full_text):
        if self.has_camera_keyword(full_text):
            return False
        if self.is_screen_glass(full_text):
            return False
        case_indicators = ['case', 'hybrid', 'cover', 'bumper', 'wallet', 'folio',
                           'magnetic', 'ring', 'stand', 'kickstand', 'magsafe', 'tpu', 'pc']
        for indicator in case_indicators:
            if indicator in full_text:
                return True
        if 'iphone' in full_text or 'for iphone' in full_text or 'for ip' in full_text:
            return True
        return False

    def is_male_case_strict(self, full_text):
        text_lower = full_text.lower()
        for b_word in self.blacklist_colors:
            if re.search(r'\b' + b_word + r'\b', text_lower):
                return False
        for f_word in self.female_keywords:
            if f_word in text_lower:
                return False
        for color in self.male_colors:
            if re.search(r'\b' + color + r'\b', text_lower):
                return True
        return False

    def is_female_case(self, full_text):
        text_lower = full_text.lower()
        for b_word in self.blacklist_colors:
            if re.search(r'\b' + b_word + r'\b', text_lower):
                return False
        for f_word in self.female_keywords:
            if f_word in text_lower:
                return True
        for c in self.female_colors:
            if re.search(r'\b' + c + r'\b', text_lower):
                return True
        for color in self.male_colors:
            if re.search(r'\b' + color + r'\b', text_lower):
                return False
        return True

    def scrape_products_fast(self):
        js_script = """
        let data = [];
        let items = document.querySelectorAll('.col-md-3.pro-1');
        for(let i = 0; i < items.length; i++) {
            let div = items[i];
            let name = div.querySelector('h6 a') ? div.querySelector('h6 a').innerText : '';
            let desc = div.querySelector('.mid-2 p') ? div.querySelector('.mid-2 p').innerText : '';
            let priceTxt = div.querySelector('.item_price') ? div.querySelector('.item_price').innerText : '';
            let qtyInput = div.querySelector('.qty') ? div.querySelector('.qty').getAttribute('name') : '';
            let stockTxt = div.querySelector('.label-success') ? div.querySelector('.label-success').innerText : '';
            let img = div.querySelector('img') ? div.querySelector('img').src : '';
            data.push({name: name, desc: desc, price: priceTxt, qty_name: qtyInput, stock: stockTxt, img: img});
        }
        return data;
        """
        raw_items = self.driver.execute_script(js_script)
        products = []
        for item in raw_items:
            full_text = (item['name'] + ' ' + item['desc']).lower()
            if self.has_camera_keyword(full_text):
                continue
            price_str = item['price'].replace('$', '').strip()
            if not price_str or 'login' in price_str.lower():
                continue
            try:
                price = float(price_str)
            except:
                continue
            try:
                stock = int(item['stock'].split(':')[1].strip().split()[0])
            except:
                stock = 999
            products.append({
                'name': item['name'],
                'description': item['desc'],
                'full_text': full_text,
                'price': price,
                'qty_field': item['qty_name'],
                'stock': stock,
                'img_url': item['img']
            })
        return products

    def set_quantity(self, qty_field_name, quantity):
        if not qty_field_name:
            return False
        try:
            js_script = f"""
            var elem = document.getElementsByName("{qty_field_name}")[0];
            if(elem) {{
                elem.value = "{quantity}";
                elem.dispatchEvent(new Event('input', {{ bubbles: true }}));
                elem.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            """
            self.driver.execute_script(js_script)
            return True
        except:
            return False

    def add_to_cart(self):
        try:
            add_btn = self.wait.until(EC.element_to_be_clickable((By.ID, "btnAddtoCart")))
            self.driver.execute_script("arguments[0].click();", add_btn)
            self.handle_alerts(2.0)
            log("  ✓ Added to cart")
            return True
        except Exception:
            log("  ❌ Failed to add to cart")
            return False

    def empty_cart(self):
        log("🗑️ Preparing fresh cart...")
        try:
            self.driver.get("https://www.cpwhwireless.com/shopping-cart")
            time.sleep(3)
            try:
                empty_btn = self.driver.find_element(By.ID, "btnEmptyCart")
                log("🗑️ Items found. Clicking Empty Cart...")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", empty_btn)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", empty_btn)
                self.handle_alerts(3.0)
                time.sleep(4)
                log("  ✓ Cart is now empty.")
            except:
                log("  ✓ Cart is already empty.")
        except Exception as e:
            log(f"  ❌ Failed to check/empty cart: {e}")
        finally:
            log("🏠 Returning to homepage to begin search...")
            self.driver.get("https://www.cpwhwireless.com/")
            time.sleep(2)

    def get_cart_total(self):
        try:
            self.driver.get("https://www.cpwhwireless.com/shopping-cart")
            time.sleep(2)
            total_elem = self.driver.find_element(By.XPATH, "//th[contains(@class, 'text-right') and contains(text(), '$')]")
            total_text = total_elem.text.replace('$', '').replace(',', '').strip()
            return float(total_text)
        except:
            return 0.0

    def trim_cart_to_limit(self, target_limit):
        log(f"🛒 Trimming cart to ${target_limit:.2f} limit...")
        max_attempts = 20
        for _ in range(max_attempts):
            current_total = self.get_cart_total()
            if current_total <= target_limit:
                log(f"  ✅ Cart total ${current_total:.2f} is within limit.")
                return True
            log(f"  ⚠️ Over limit (${current_total:.2f}). Removing 1 unit...")
            qty_inputs = self.driver.find_elements(By.XPATH, "//input[starts-with(@name, 'quantity_')]")
            if not qty_inputs:
                log("  ❌ No quantity inputs found, cannot trim.")
                return False
            target_input = None
            for inp in qty_inputs:
                try:
                    val = int(inp.get_attribute('value'))
                    if val > 0:
                        target_input = inp
                        break
                except:
                    pass
            if not target_input:
                log("  ❌ No product with quantity > 0 found.")
                return False
            curr_val = int(target_input.get_attribute('value'))
            new_val = max(0, curr_val - 1)
            target_input.clear()
            target_input.send_keys(str(new_val))
            update_btn = self.driver.find_element(By.ID, "btnUpdateCart")
            self.driver.execute_script("arguments[0].click();", update_btn)
            time.sleep(3)
        log(f"  ❌ Could not trim cart within {max_attempts} attempts.")
        return False

    def proceed_to_checkout_and_place(self, store_address):
        log("💳 Proceeding to Checkout...")
        try:
            self.driver.get("https://www.cpwhwireless.com/checkout")
            self.wait.until(EC.presence_of_element_located((By.ID, "DivShippingAddresses")))
            time.sleep(2)
            log(f"📍 Selecting store address: {store_address[:50]}...")
            addr_elements = self.driver.find_elements(By.XPATH, "//input[@name='shipping_addredd_id']")
            best_elem, best_score, best_label = None, -1, ""
            for elem in addr_elements:
                try:
                    label = elem.find_element(By.XPATH, "..").text
                except Exception:
                    label = ""
                sc = _acc_address_score(store_address, label)
                if sc > best_score:
                    best_elem, best_score, best_label = elem, sc, label
            if best_elem is not None and best_score >= 5:
                if not best_elem.is_selected():
                    self.driver.execute_script("arguments[0].click();", best_elem)
                log(f"  ✓ Matched store address (score {best_score}): {best_label[:60].strip()}")
            else:
                log(f"  ❌ No reliable address match (best score {best_score}). Skipping this store to avoid shipping to the wrong address.")
                return False
            log("🚚 Selecting Regular Ground Shipping...")
            ship_radio = self.driver.find_element(By.XPATH, "//input[@name='delivery_type' and @value='Regular Ground Shipping']")
            if not ship_radio.is_selected():
                self.driver.execute_script("arguments[0].click();", ship_radio)
            
            log("✅ Placing Order...")
            place_btn = self.driver.find_element(By.ID, "btnCheckout")
            self.driver.execute_script("arguments[0].click();", place_btn)
            
            if self.handle_alerts(5.0):
                log("  ✓ Accepted checkout confirmation alert.")
            else:
                log("  ⚠️ No confirmation alert appeared.")
                
            time.sleep(4)
            log("🎉 ORDER PLACED SUCCESSFULLY!")
            return True
        except Exception as e:
            log(f"❌ Failed during checkout phase: {e}")
            return False

    def add_cases_distributed(self, target_qty, case_type, target_model):
        products = self.scrape_products_fast()
        if not products:
            log(f"  ⚠️ No products scraped for {target_model}")
            return 0
        filtered = []
        for p in products:
            if self.is_phone_case(p['full_text']) and p['price'] <= self.case_max_price:
                if not self.is_correct_model_exact(p['full_text'], target_model):
                    continue
                if case_type == 'male' and self.is_male_case_strict(p['full_text']):
                    filtered.append(p)
                elif case_type == 'female' and self.is_female_case(p['full_text']):
                    filtered.append(p)
        if not filtered:
            log(f"  ⚠️ No {case_type} cases found for {target_model} under ${self.case_max_price}")
            return 0
        filtered.sort(key=lambda x: x['price'])
        remaining = target_qty
        total_cost = 0
        for product in filtered:
            if remaining <= 0:
                break
            take = min(remaining, 2, product['stock'])
            if take > 0:
                self.set_quantity(product['qty_field'], take)
                total_cost += product['price'] * take
                remaining -= take
                log(f"  ✓ {case_type.capitalize()} Case: {product['name'][:35]}... x{take} @ ${product['price']}")
        if remaining > 0:
            for product in filtered:
                if remaining <= 0:
                    break
                take = min(remaining, product['stock'])
                if take > 0:
                    self.set_quantity(product['qty_field'], take)
                    total_cost += product['price'] * take
                    remaining -= take
                    log(f"  ✓ {case_type.capitalize()} Case (extra): {product['name'][:35]}... x{take} @ ${product['price']}")
        if remaining > 0:
            log(f"  ⚠️ Only found {target_qty - remaining}/{target_qty} {case_type} cases")
        return total_cost

    def add_glass_exact(self, target_qty, glass_type, target_model):
        products = self.scrape_products_fast()
        if not products:
            return 0
        filtered = []
        for p in products:
            if self.is_screen_glass(p['full_text']) and p['price'] <= self.glass_max_price:
                if not self.is_correct_model_exact(p['full_text'], target_model):
                    continue
                is_priv = 'privacy' in p['full_text']
                if glass_type == 'privacy' and is_priv:
                    filtered.append(p)
                elif glass_type == 'clear' and not is_priv:
                    filtered.append(p)
        if not filtered:
            return 0
        filtered.sort(key=lambda x: x['price'])
        best = filtered[0]
        qty = min(target_qty, best['stock'])
        if qty > 0:
            self.set_quantity(best['qty_field'], qty)
            log(f"  ✓ {glass_type.capitalize()} Glass: {best['name'][:30]}... x{qty} @ ${best['price']:.2f}")
            return best['price'] * qty
        return 0

    def go_to_cable_charger_page(self):
        log("\n📦 Going to CABLE CHARGER POWERBANK page...")
        self.driver.get(self.cable_charger_url)
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".col-md-3.pro-1")))
            log("  Scrolling down to load ALL items...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(8):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            self.driver.execute_script("window.scrollTo(0, 0);")
            log("  ✓ On CABLE CHARGER POWERBANK page (Fully Loaded)")
            return True
        except:
            return False

    def add_hardcoded_items(self, target_qty, category, subtype):
        if target_qty <= 0:
            return 0
            
        if not self.go_to_cable_charger_page():
            return 0

        all_products = self.scrape_products_fast()
        sku_to_qty = {p['name'].strip(): p['qty_field'] for p in all_products}
        sku_to_stock = {p['name'].strip(): p['stock'] for p in all_products}

        available_items = []
        for sku, info in PRODUCTS.items():
            if info.get('type') != category:
                continue
            if category == 'cable' and info.get('subtype') != subtype:
                continue
            if category == 'charger' and info.get('charger_type') != subtype:
                continue
            if sku not in sku_to_qty:
                continue
            per_unit = info['price'] / info.get('pack_size', 1)
            if category == 'charger' and subtype == 'car':
                if per_unit > 3.00:
                    continue

            available_items.append({
                'sku': sku,
                'qty_field': sku_to_qty[sku],
                'price': info['price'],
                'pack_size': info.get('pack_size', 1),
                'stock': sku_to_stock[sku],
                'per_unit': per_unit
            })

        if not available_items:
            log(f"  ⚠️ No hardcoded SKUs found on page for {category} ({subtype})")
            return 0

        items_sorted = sorted(available_items, key=lambda x: x['per_unit'])
        best_cost = float('inf')
        best_counts = {}

        def dfs(current_target, item_idx, current_cost, current_counts):
            nonlocal best_cost, best_counts
            if current_target <= 0:
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_counts = current_counts.copy()
                return
            if item_idx >= len(items_sorted):
                return
            if current_cost + (current_target * items_sorted[item_idx]['per_unit']) >= best_cost:
                return

            item = items_sorted[item_idx]
            max_takes = min(item['stock'], (current_target + item['pack_size'] - 1) // item['pack_size'])

            for take in range(max_takes, -1, -1):
                new_counts = current_counts.copy()
                if take > 0:
                    new_counts[item['sku']] = take
                dfs(current_target - take * item['pack_size'], item_idx + 1, current_cost + take * item['price'], new_counts)

        dfs(target_qty, 0, 0, {})

        if best_cost < float('inf'):
            log(f"  ✅ Optimal combo found for {category} ({subtype}): ${best_cost:.2f}")
            total_units = 0
            for sku, take in best_counts.items():
                item = next(x for x in available_items if x['sku'] == sku)
                self.set_quantity(item['qty_field'], take)
                units = take * item['pack_size']
                total_units += units
                log(f"    ✓ {sku} x{take} (={units} units) @ ${item['price']} each")
            log(f"  Total units ordered: {total_units} (Target: {target_qty})")
            self.add_to_cart()
            return best_cost
        else:
            log(f"  ⚠️ Could not meet exact target. Buying what is available...")
            remaining = target_qty
            cost = 0
            for item in items_sorted:
                if remaining <= 0: break
                take = min(item['stock'], (remaining + item['pack_size'] - 1) // item['pack_size'])
                if take > 0:
                    self.set_quantity(item['qty_field'], take)
                    units = take * item['pack_size']
                    remaining -= units
                    cost += take * item['price']
                    log(f"    ✓ [Fallback] {item['sku']} x{take} (={units} units) @ ${item['price']} each")
            
            if cost > 0:
                self.add_to_cart()
            return cost

    def is_phone_model(self, model_name):
        model_lower = model_name.lower()
        for keyword in self.skip_excel_keywords:
            if keyword in model_lower:
                return False
        phone_indicators = ['iphone', 'samsung', 'motorola', 'google pixel', 'moto', 'galaxy',
                            'apple', 'edge', 'razr', 'a16', 'a17', 's26', 's25', '5g', 'tab', 'revvl']
        for indicator in phone_indicators:
            if indicator in model_lower:
                return True
        return False

    def read_pdf_orders(self, pdf_path):
        """
        Extract order data from a PDF file.

        PDF layout (from the actual Accessories order request spreadsheet):
          Row format for phones:
              <Model name>  <Male qty>  <Female qty>  <Privacy glass qty>  <Clear glass qty>
          Row format for accessories:
              <Label>  <Qty>

        Rows with no quantities (zero-order placeholder rows) are silently skipped.
        """
        # ── 1. Extract raw text ───────────────────────────────────────────────
        raw_text = ""

        if _HAS_PDFPLUMBER:
            try:
                with _pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            raw_text += t + "\n"
                log("PDF text extracted via pdfplumber.")
            except Exception as exc:
                log(f"pdfplumber failed ({exc}), trying pypdf…")

        if not raw_text.strip() and _HAS_PYPDF:
            try:
                reader = _PdfReader(pdf_path)
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        raw_text += t + "\n"
                log("PDF text extracted via pypdf.")
            except Exception as exc:
                log(f"pypdf also failed: {exc}")

        if not raw_text.strip():
            log(f"❌ Could not extract text from PDF: {pdf_path}")
            return None

        # ── 2. Helper: split trailing quantity columns from a line ────────────
        def split_trailing_numbers(line):
            """
            Split the rightmost block of pure-integer tokens from a line.

            Rules:
            - Year numbers (1900-2099) belong to the model name — stop collecting.
            - Slash-model variant numbers (e.g. '13' in 'iPhone 13' after '/') also
              belong to the model name — skip the first integer when the token before
              the qty block is a plain word that follows a '/' in the prefix.
            - Exception: a parenthesised year like '(2025)' after '/' is NOT a qty
              boundary; collect the actual integers that follow it normally.
            - 'iPhone 15' / 'Pixel 9' — single trailing integer that immediately
              follows a brand-suffix keyword is a model generation number, not qty.
            """
            tokens = line.split()
            n = len(tokens)

            # Collect trailing pure-integer tokens, stopping at year numbers
            raw_end = []
            for j in range(n - 1, -1, -1):
                tok = tokens[j]
                if re.fullmatch(r'\d+', tok):
                    val = int(tok)
                    if 1900 <= val <= 2099:   # year → model name, stop
                        break
                    raw_end.insert(0, (j, val))
                else:
                    break  # non-integer → stop

            if not raw_end:
                return line.strip(), []

            split_idx = raw_end[0][0]

            # ── Slash-model guard ─────────────────────────────────────────────
            # "Apple iPhone 14 / Apple iPhone 13  10  5  20  20"
            # After year-stop scan: raw_end = [(idx_13, 13), (idx_10,10), ...]
            # The '13' is a model variant that follows the slash group — skip it.
            prefix_text = ' '.join(tokens[:split_idx])
            if '/' in prefix_text and split_idx > 0:
                prev_tok = tokens[split_idx - 1]
                # Only fire when prev token is a plain word (not a digit or
                # a parenthesised year like "(2025)")
                prev_is_paren_year = bool(re.fullmatch(r'\(\d{4}\)', prev_tok))
                prev_is_digit      = bool(re.fullmatch(r'\d+', prev_tok))
                if not prev_is_digit and not prev_is_paren_year:
                    # First integer is the model variant — skip it
                    raw_end = raw_end[1:]
                    if not raw_end:
                        return line.strip(), []
                    split_idx = raw_end[0][0]

            # ── iPhone / Pixel generation number guard ────────────────────────
            # "Apple iPhone 15" — '15' is the model generation, not a qty column.
            # Trigger: single trailing integer ≤ 20, prev token is a brand keyword.
            if raw_end and split_idx > 0:
                prev_tok_lower = tokens[split_idx - 1].lower()
                first_val = raw_end[0][1]
                MODEL_SUFFIX_WORDS = ['iphone', 'pixel', 'revvl', 'galaxy', 'razr']
                if (any(prev_tok_lower.endswith(kw) for kw in MODEL_SUFFIX_WORDS)
                        and len(raw_end) == 1
                        and first_val <= 20):
                    return line.strip(), []

            model = ' '.join(tokens[:split_idx]).strip()
            nums  = [v for _, v in raw_end]
            return model, nums

        # ── 3. Parse lines ────────────────────────────────────────────────────
        lines = [l.strip() for l in raw_text.splitlines()]

        orders         = []
        car_charger_qty  = 0
        wall_charger_qty = 0
        cable_qtys = {'c_to_c': 0, 'a_to_c': 0, 'c_to_l': 0, 'a_to_l': 0, 'unknown': 0}
        phone_map = {}   # model_name → {male, female, privacy, clear}

        SKIP_LINE_PHRASES = [
            'accessories order request',
            'phone cases model',
            'male cases quantity',
            'other accessories',
            'car phone holder',
        ]

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            line_lower = line.lower()

            # Skip header / section rows
            if any(ph in line_lower for ph in SKIP_LINE_PHRASES):
                continue

            # ── Classify by label, then extract qty columns ───────────────────
            label, nums = split_trailing_numbers(line)
            label_lower = label.lower()

            # Car charger
            if 'car charger' in label_lower:
                qty = nums[0] if nums else 0
                if qty > 0:
                    car_charger_qty += qty
                continue

            # Wall charger / adaptor
            if ('charger' in label_lower or 'adaptor' in label_lower
                    or 'adapter' in label_lower or 'wall block' in label_lower
                    or 'wall adaptor' in label_lower or 'wall charger' in label_lower):
                qty = nums[0] if nums else 0
                if qty > 0:
                    wall_charger_qty += qty
                continue

            # Cables / USB lines
            if ('cable' in label_lower or 'usb' in label_lower
                    or 'lightning' in label_lower or 'type-a' in label_lower
                    or 'type a' in label_lower or 'type-c' in label_lower
                    or 'type c' in label_lower):
                qty = nums[0] if nums else 0
                if qty <= 0:
                    continue
                if 'lightning' in label_lower or 'iphone' in label_lower:
                    if ('usb-c' in label_lower or 'type-c' in label_lower
                            or 'type c' in label_lower or 'pd' in label_lower
                            or 'c to' in label_lower):
                        cable_qtys['c_to_l'] += qty
                    else:
                        cable_qtys['a_to_l'] += qty
                elif (label_lower.count('usb-c') == 2 or 'c to c' in label_lower
                      or 'type c to type c' in label_lower or 'c-c' in label_lower):
                    cable_qtys['c_to_c'] += qty
                elif ('usb-c' in label_lower or 'type c' in label_lower
                      or 'type-c' in label_lower):
                    cable_qtys['a_to_c'] += qty
                else:
                    cable_qtys['unknown'] += qty
                continue

            # Phone / tablet model
            if self.is_phone_model(label):
                if not nums:
                    continue  # placeholder row with no ordered qty — skip

                # Columns: Male, Female, Privacy, Clear
                male_q    = nums[0] if len(nums) > 0 else 0
                female_q  = nums[1] if len(nums) > 1 else 0
                privacy_q = nums[2] if len(nums) > 2 else 0
                clear_q   = nums[3] if len(nums) > 3 else 0

                if not any([male_q, female_q, privacy_q, clear_q]):
                    continue

                if label not in phone_map:
                    phone_map[label] = {'male': 0, 'female': 0, 'privacy': 0, 'clear': 0}
                phone_map[label]['male']    += male_q
                phone_map[label]['female']  += female_q
                phone_map[label]['privacy'] += privacy_q
                phone_map[label]['clear']   += clear_q
                continue

        # ── 4. Build orders list (same shape as read_excel_orders) ─────────────
        for model, counts in phone_map.items():
            if any(v > 0 for v in counts.values()):
                orders.append({'type': 'phone', 'model': model, **counts})

        for c_type, qty in cable_qtys.items():
            if qty > 0:
                orders.append({
                    'type': 'cable',
                    'cable_type': c_type,
                    'model': f'Aggregated {c_type.replace("_", "-").upper()} Cables',
                    'qty': qty,
                })

        if car_charger_qty > 0:
            orders.append({'type': 'car_charger',  'model': 'Dual Port Car Charger (Combined)',   'qty': car_charger_qty})
        if wall_charger_qty > 0:
            orders.append({'type': 'wall_charger', 'model': 'Wall Adaptor/Charger (Combined)',     'qty': wall_charger_qty})

        if not orders:
            log(f"⚠️ PDF parsed but no orderable lines found in: {pdf_path}")
            return None

        log(f"✅ PDF parsed: {len(orders)} order group(s) found.")
        return orders

    def read_excel_orders(self, excel_path):
        # ── PDF files are handled by the dedicated PDF parser ─────────────────
        if excel_path.lower().endswith('.pdf'):
            return self.read_pdf_orders(excel_path)

        try:
            if excel_path.lower().endswith('.csv'):
                df = pd.read_csv(excel_path, header=1).fillna(0)
            else:
                df = pd.read_excel(excel_path, sheet_name='Sheet1', header=1).fillna(0)
                
            orders = []
            car_charger_qty = 0
            wall_charger_qty = 0
            cable_qtys = {'c_to_c': 0, 'a_to_c': 0, 'c_to_l': 0, 'a_to_l': 0, 'unknown': 0}
            
            for index, row in df.iterrows():
                if len(row) < 2:
                    continue
                item_name = str(row.iloc[0]).strip()
                if not item_name or item_name == '0' or item_name == 'nan':
                    continue
                item_lower = item_name.lower()
                
                if 'car charger' in item_lower:
                    car_charger_qty += safe_int(row.iloc[1])
                elif 'charger' in item_lower or 'adapter' in item_lower or 'adaptor' in item_lower or 'wall block' in item_lower:
                    wall_charger_qty += safe_int(row.iloc[1])
                elif 'cable' in item_lower or 'type-a' in item_lower or 'type a' in item_lower or 'type-c' in item_lower or 'type c' in item_lower or 'usb' in item_lower or 'lightning' in item_lower:
                    qty = safe_int(row.iloc[1])
                    if qty > 0:
                        if 'lightning' in item_lower or 'iphone' in item_lower:
                            if 'usb-c' in item_lower or 'type-c' in item_lower or 'type c' in item_lower or 'pd' in item_lower or 'c to' in item_lower:
                                cable_qtys['c_to_l'] += qty
                            else:
                                cable_qtys['a_to_l'] += qty
                        elif item_lower.count('usb-c') == 2 or 'c to c' in item_lower or 'type c to type c' in item_lower or 'c-c' in item_lower:
                            cable_qtys['c_to_c'] += qty
                        elif 'usb-c' in item_lower or 'type c' in item_lower or 'type-c' in item_lower:
                            cable_qtys['a_to_c'] += qty
                        else:
                            cable_qtys['unknown'] += qty
                elif self.is_phone_model(item_name):
                    male_qty = safe_int(row.iloc[1]) if len(row) > 1 else 0
                    female_qty = safe_int(row.iloc[2]) if len(row) > 2 else 0
                    privacy_qty = safe_int(row.iloc[3]) if len(row) > 3 else 0
                    clear_qty = safe_int(row.iloc[4]) if len(row) > 4 else 0
                    if male_qty > 0 or female_qty > 0 or privacy_qty > 0 or clear_qty > 0:
                        orders.append({
                            'type': 'phone', 'model': item_name,
                            'male': male_qty, 'female': female_qty,
                            'privacy': privacy_qty, 'clear': clear_qty
                        })
                        
            for c_type, qty in cable_qtys.items():
                if qty > 0:
                    orders.append({'type': 'cable', 'cable_type': c_type, 'model': f'Aggregated {c_type.replace("_", "-").upper()} Cables', 'qty': qty})
                    
            if car_charger_qty > 0:
                orders.append({'type': 'car_charger', 'model': 'Dual Port Car Charger (Combined)', 'qty': car_charger_qty})
            if wall_charger_qty > 0:
                orders.append({'type': 'wall_charger', 'model': 'Wall Adaptor/Charger (Combined)', 'qty': wall_charger_qty})
                
            return orders
        except Exception as e:
            log(f"Error reading Excel file ({excel_path}): {e}")
            return None

    def process_store_order(self, orders):
        total_cost = 0
        self.current_limit = self.soft_limit
        last_processed_idx = -1
        
        for idx, order in enumerate(orders):
            if self.stop_event.is_set():
                log("🛑 Stop requested. Stopping before next item.")
                break
            log(f"\n--- {order['model']} ---")
            item_cost = 0
            
            if order['type'] == 'phone':
                if self.search_phone_model(order['model']):
                    if order.get('male', 0) > 0:
                        item_cost += self.add_cases_distributed(order['male'], 'male', order['model'])
                    if order.get('female', 0) > 0:
                        item_cost += self.add_cases_distributed(order['female'], 'female', order['model'])
                    if order.get('privacy', 0) > 0:
                        item_cost += self.add_glass_exact(order['privacy'], 'privacy', order['model'])
                    if order.get('clear', 0) > 0:
                        item_cost += self.add_glass_exact(order['clear'], 'clear', order['model'])
                        
                    if item_cost > 0:
                        self.add_to_cart()
                    else:
                        log(f"  ⚠️ No valid products found for phone order")
                else:
                    log(f"  ⚠️ Could not search or no products for {order['model']}. Skipping.")
            else:
                if order['type'] == 'cable':
                    item_cost = self.add_hardcoded_items(order['qty'], 'cable', order['cable_type'])
                elif order['type'] == 'car_charger':
                    item_cost = self.add_hardcoded_items(order['qty'], 'charger', 'car')
                elif order['type'] == 'wall_charger':
                    item_cost = self.add_hardcoded_items(order['qty'], 'charger', 'wall')
                    
            if item_cost > 0:
                total_cost += item_cost
                log(f"  💰 Subtotal: ${item_cost:.2f}")
                
            if total_cost >= self.current_limit:
                log(f"\n⚠️ Reached ${self.current_limit:.2f} limit. Will attempt to add remaining items with extra budget if any left.")
                last_processed_idx = idx
                break
        else:
            return total_cost
            
        remaining_orders = orders[last_processed_idx+1:]
        if remaining_orders and total_cost < self.hard_limit:
            log(f"\n💰 Extending budget to ${self.hard_limit:.2f} for remaining items...")
            self.current_limit = self.hard_limit
            for order in remaining_orders:
                if self.stop_event.is_set():
                    log("🛑 Stop requested. Stopping remaining items.")
                    break
                log(f"\n--- {order['model']} ---")
                item_cost = 0
                if order['type'] == 'phone':
                    if self.search_phone_model(order['model']):
                        if order.get('male', 0) > 0:
                            item_cost += self.add_cases_distributed(order['male'], 'male', order['model'])
                        if order.get('female', 0) > 0:
                            item_cost += self.add_cases_distributed(order['female'], 'female', order['model'])
                        if order.get('privacy', 0) > 0:
                            item_cost += self.add_glass_exact(order['privacy'], 'privacy', order['model'])
                        if order.get('clear', 0) > 0:
                            item_cost += self.add_glass_exact(order['clear'], 'clear', order['model'])
                        if item_cost > 0:
                            self.add_to_cart()
                else:
                    if order['type'] == 'cable':
                        item_cost = self.add_hardcoded_items(order['qty'], 'cable', order['cable_type'])
                    elif order['type'] == 'car_charger':
                        item_cost = self.add_hardcoded_items(order['qty'], 'charger', 'car')
                    elif order['type'] == 'wall_charger':
                        item_cost = self.add_hardcoded_items(order['qty'], 'charger', 'wall')
                        
                if item_cost > 0:
                    total_cost += item_cost
                    log(f"  💰 Subtotal: ${item_cost:.2f}")
                if total_cost >= self.hard_limit:
                    log(f"\n⚠️ Reached hard limit ${self.hard_limit:.2f}. Stopping.")
                    break
        return total_cost

    def run(self, stores=None):
        log("\n" + "="*60)
        log("GFH TELECOM LLC ACCESSORIES ORDERING AUTOMATION")
        log("="*60)
        
        missing = [s.get('alias', 'Unknown') for s in stores if not s.get('excel_path')]
        if missing:
            log(f"❌ Missing order file (Excel/CSV/PDF) for: {', '.join(missing)}")
            return False

        total_stores = len(stores)
        processed_count = 0
        completed_count = 0
        emit_progress(total=total_stores, processed=0, completed=0, pending=total_stores)

        if self.stop_event.is_set():
            log("🛑 Automation cancelled before login.")
            return False

        if not self.login():
            return False

        for store in stores:
            if self.stop_event.is_set():
                log("🛑 Stop requested. Automation stopped before next store.")
                break

            log("\n" + "="*50)
            log(f"🚀 STARTING ORDER FOR STORE: {store['alias']}")
            log("="*50)
            orders = self.read_excel_orders(store['excel_path'])
            if not orders:
                log(f"⚠️ No valid orders found in file for store {store['alias']}. Skipping.")
                processed_count += 1
                emit_progress(total=total_stores, processed=processed_count, completed=completed_count, pending=total_stores-processed_count)
                continue

            if self.stop_event.is_set():
                log("🛑 Stop requested. Store skipped before cart processing.")
                break

            self.empty_cart()
            total_cost = self.process_store_order(orders)
            self.trim_cart_to_limit(self.hard_limit)
            success = self.proceed_to_checkout_and_place(store['address'])
            processed_count += 1
            if success:
                completed_count += 1
                log(f"✅ Finished processing store {store['alias']}\n")
            else:
                log(f"❌ Aborted processing for store {store['alias']}\n")
            emit_progress(total=total_stores, processed=processed_count, completed=completed_count, pending=total_stores-processed_count)

        if self.stop_event.is_set():
            log("\n🛑 AUTOMATION STOPPED BY USER.")
            return False
        log("\n🎉 ALL STORE ORDERS COMPLETED!")
        return True

    def close(self, ask=True):
        if ask:
            input("\n📌 Press Enter to close browser...")
        try:
            self.driver.quit()
        except Exception:
            pass


APP_TITLE = "GFH Telecom LLC Accessories Ordering Automation"
APP_BG = "#F4F6FA"
NAVY = "#090d26"        # matches theme_manager.py navy — header blends with logo
EMBEDDED_LOGO_B64 = "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O3rtmg3FUu2Sj13u+8Gbbz79yMPPnn7m2Z+47NM/+OHV73/fBxYsXjh3zqyZf1tw+ac/k05nq9Xek6cfd9NNN2zYsDWO65MnT7z+hz/9znXXXnD+R3/ykx+sWLGC2U2cMPErX7n6plt+/NCDT0w7/NBjjj3lzbmv/eB73zvttBn77LPfzJmv7DFi5JFHnrxs5bzvXvu9Y4457AMfOOmN2a+mM5nVq9Y3N+evuurbL7380gP33zNy1PAlSxYfeOCBTzzx9Isv/O3CCy9oa2vLZjMbNmx88MHHa1H129/+6quvvtHW1vzoY0/8+pZbX3nluQ0bNpdK5XETRt11131fvvJazw95W3Zuar/6xQ1HHvm+RYsWH3f8Md+46juT99133333Hjd29MaNmyuV6heuuHLZ0qWrVy9evnz5oYceefxx0++66zenn3HeX5566OEHH0mFLaecei55Cojieu+0ww56+ukH7r//kQs+/EnrzPeu/c4JJxxz+LQTGcy5Hzz72mu/Om7C5Ft/84uTTznxzTfmDeoYcuut9/zXj34cpryn//LggQfuN3nKESuWLd97n73/+uxjGzatLRVLk/bZ5557HvzSlVcJBszgxP5j2jTeIdAXBw4dOJ16ujs+JKcPzTSnap1BcePhzcOX17KPVBMIUizSE+buKHRXJTW9dVA+6c3ZClU3j/XDYW1NU9pbl9fMothsMraccCwoqABFo2QJ9vCCvUM1HuMOqahyve6SovIkCCtWCpZ6vLZ1jlbWojUuMaBOzqYPwpqf9JR8rzvXurJo54mfiKfjpL49ydqlanTqgVOOPe7Iww8/5o03Xrn88itqEZ17/r8NHzbu+ece/tznvv7iK3+zpnLN1Vdt2rRln0nj99v34F/e9Ivzzjvr3z97yTPPvtDe1vGNq7+lPe3Y5bLB9df/x1NPP3vhhZ9nNlde8e+XXnrhnx+495pvf+nue+7+9Ke/ACjf/+73vv/9/3j0sYcKhc58U/DD668+/rhjo3ohSWqkoVDo3n//va/9zpc/dN55xhSieiVJqs7Zq6665re/+xWpPLvKT37yozFjRx191MlLl8899JCj7r33d08++fzhRx1/zTe+cvChB08/+Wx28TXf/NZLL7563PEfECAiGjd+ggh/8lNfevW1V089+aR77r55/psrf3vn70mHjf6RYUOGn3nmKR+5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QWeQvX3zxtbBg4/IDy5b1i6ewPaiIYPyhcrD1XLZCz0g4+VKPsw0tUWFaFyJx2l/ZBCO9lJ5MEoJaREQB+IErXgFQ2uT+krhFa62jlVVpSEgQCYgsuV2W3tfS3hYgC21rTEZdmHk52bG9HgSd6UylDh4tyo0UKRLvYWzzznzpJOPXrly1fvff9jXv34tkaeUn07nBLijffgHzzr9k5+68u57fu978sILL1522WWvvPpUW2tHPt8srIDBitGeVyoXv/DFr//m1zdO3f+Q3kJh6gH7/Of1P1m48PWrr77uxht/eNTRh4LQPpMmf+XKqzdsWNna0rF+w2ZU4Te+8d1jjz2qtbUDRTfnWzyVRvK/dfX10086rq21XZGPoK699ppLL724paXlG9/87jXf/o8jph3ywl8fW7R40X77TVkwf+GDDz3AzqD2giCFAETaOjnyyMOffebZ1taWv/zl+Ztu/k0Y+jffdEN3T+d++069+eY77rzz7scff+z11+d86cqvh6mWQm/hmGOOPefcM19/ffYRR0674b9uATRIXi7T5PuhVv6ll158ww23fP+H3yPy/vSHOy679GP33X9XJtOUzWQRtXVWexRFlTFjJp5yysmXXnLZfX++N/TTb7w586Mf/XAcxW2trZnUUEZubm7P5Zp8P8uOPn7pJQcecNDQoUO+d91PTjt1+mszZ5986ukC+OUrrvz3f7/soYced1Z+8YsbCr3dkyfve+cd999x1x9SqWa3fd/s967s2WmNUgg0IwKUNK0ud2cy2Y50G1XroXEZW9+zNdOuMSmWbCLFlA8InnUag6rVy2L7WhzPrXpvVPzX6vRmpF+P9MyafrXm/a3GL9fqrzhZIGorehZUM3spUYZsJilPpNoH2lOT05KOyppNLF5PpnmmU49Walv9FAqC8LuvIintdXVtue++B4U5qsU/uuGmP9//aBDmTWJXrVg7a/Yb2g+WL1v54MNPaZ21lufPW9HTXV28eE1Pb8+bb8xbtWa99NdLiPTihYseffRxZ6izs/Oab33vrrvvyzcNm/na7KeefF6RWr589bevvv6Bhx8O0oPWrdn85psL1m/YWqlFM1+d/frsBUuXrdm4fsvM1+Z0dld6CoWZf5v9xux5K1asWb9u8/x5ixYtWjLnzQVvzFm6bt3m++57tKerJ47dXXfc+61rvl+rMaqwVCrO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"
EMBEDDED_ICON_B64 = "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pqbm823bJvNuN1cR1R98/9r0mKPPGgPKj5xyyjM2jW2dUlXVL3/pu9PV6qpHBwePvg0YuOWPP1DU8zOf+XsF0HrrW/9wq6pq0vX6oQ9+pktYvr5eP/4+YMW9H//Y5aqq+q53/el2gDZd+skvqKpqu5Xr7GziZ2cSnW+mfmqykz31qS++DWjc9Yyn//bcL39xV6aq0m6nfuPGMWm1ElVVve4/bs2f/KRn6Rc+/xVNE5WZ6Y625jPttJ122k5nZjqadL3+zqvelv3Oq94+Xzwr0+mptuzYMaetVipjYzP5sy962fhha594x113PZTtEwCVxvESxIc9vHLlyVM3/+rufGpqRi+++I3J0NDq7IQTzp6/6ca7O1mq+oqXX5Idc/RZD55xxkV3POWpL7z9hl/e5bZunvTPefZrsmOOPffRk0993uZy9fB7omikedll/9RWVel2c7n9tvuzY445Z2ulctjY0NCJt33j61flqqrveMd7PYCpt739fWNZlstVP7xhFlh2Y1w58pFq/bhtjcETflWpHXn7smVHT19zzbVeVfUH3//J/BlPet6txx3zNHfeeS/Kf/Sj62dVVX/2sxv9iuVHJCeddObWjRu3qXNeL730c3riiU+9b+3ak7c89zkXt2684XZVVf3iF789R1S+74wzzvfr1m0VVZVOO9FLLnnfhLHVB0txfeaSS/5QvPfy6c9ckQPY8KpXvVZmZxNRVZmdbSdPf/qLxphG7jB25O4/+7NPiPde3vSm31cA+id/8glxzsuln/zS3AknnHvjWWe98O5TT7vo9lNOf85NcTzy0MrVR3Zuuun2eVXVf/3XH3dPO+0Z9xx22EmT55//guZVP/wPUVW56qqf6+mnXfjIKade9Kvjjnvypr///Nek1Ur92972gfuOPvbJvzjvvJf/ulo+bPK1r/mDxHuvX/ziNyaOOfaM655y1nPGzjrrwrEnn3nBzQODyzcvWbZmw5133d/e7+8Geqd+1apVM6tXrxyanJzRW265LZue3tycnh7b9qY3v+Pop559/uw99z6YrHvo0QDQ6aGhEVWFRqWAH354gzy0/j6Oq8OJz317yejyR57+jKeefO99D+Dhhx/G85/3/OD0004uP/TQuoeSrlvyla9cOf385z9z9EUvugg/+vEPOy98wbOXJF2vX/6Hr20xgUWpVG5maTpHgR1uz0/M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"

NAVY_2 = "#050817"
RED = "#E91B2F"
TEXT = "#111827"
MUTED = "#6B7280"
BORDER = "#D7DAE2"
WHITE = "#FFFFFF"

def resource_path(relative_path):
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path:
        return os.path.join(base_path, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

GFH_LOGO_PNG_B64 = "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"
GFH_ICON_ICO_B64 = "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"
GFH_SQUARE_ICON_B64 = "iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAABacUlEQVR4nO39eZDl2XXfB37Ovfe3vD2Xyszaq7qrdwANNJoACG4NiBQ3cZFG6rFki7Y1E+EIhyIsjaQIa6wIO+QIe+QISWN5wuE/JsIjyooQNRhLJEWKICEJAEmBJMjegEaj9+7qWnPPfNtvu/ee+eP3sroaBLqrugvolmZOxKusl/nebzvnnnuW7zlH+HePBB43sCXwZf+tf1xd/YGBc/U51Xivqt4LcrcIZ0E2VHUVGIB2REhBbPstDarUIAUwEZFd0E1V3gB9VUReEjEveZ9e3N39yuSPX9JjDtYVPhcB/a7e/R0meb8v4BZpwXSAz4Wb/7C+/n13q+qjwKcgPiIi94IeF7HJm7fX8kRV3/L+254GEJG3vAdFNTQg11X1JTBPAX8gIk9sbf3Rq289xuMLofp3Qxg+6AJg4DFz80pfWfnk0Fr/aWPkJ1X1M6AfEnGJiCwYHI8YHeGI43+Mo9/pvr9FQt7yfdMKhuHoXKq+AfmGiHwpRv18CO739va+On7zcI85+HJsr+WDSR9QAXjcwudabgKnT39/x/vmszHyOOifFDGnRAyqEdUIaKBlmoAsNMUdv7cjoTha2QJiRQw3XcsVkC8Yw+ecS754+fLvF4vvGnhcvlV7fRDoAyYAj9ubVefGxkc/pOr+IvC4iFxoV15EVWPLCDG09/B+3Ye2r/ZaRMS0wqCo6ivA50T8P97cfOYbi88vtrIPjiB8QATgrYxfW3v0x4H/XIQ/ZYxNVAOqcaFKxfKBue4/RrrQRkbEGBFLjKFR5deB/2V7+4nfWnzuAyMI7/eDPFLXEWB9/eN/BuSvicgPgaCtZveLlW6+41E+mHSkpZyIpTUk9XdB//7W1pP/fPGZt9z/+0HvlwC8ZQUcO/Z9P2WM/lci5ofaBxUXBtwNFf/vMh1tESJiTCvY8XdjlP9+Z+ePfqP9yFs14PeS3oeH+7g9Yvz6+iMPi9j/Fvh5ANWweAhH/vm/b6QBEBF7tPJ/RTX811tbT32tffvms/le0fdSAG6s+rW1h/oinb8F/F9ETNYyXrnJgv/3nDSCIGKNaqyA/7tq8d9tbz83/V5rg++VABgW+9za2sd/QkT+R2PsAzF62lXx7+uKfydq790YR4zheVX9q9vbT/7m4o83ntl3k74HAvCYgy/706e/v9M0zf8N5K8AqAb/flj0ord+wvi9uTIFDSLWLd7+gyRJ/q9tDKF9dt/Nk3+Xb7G9gbW1j31UxP2vxpiPx+jfX3V/O4r1eyqa7bZgjDMxxidV/f9pe/vpZ77bQvDdusWj4ExcW3v0PxHhfxaR3mLVu+/SOf89IfUi1qnqTJW/vL39xC/SbgeLoNOdpe/GKjy62Li29ujfNcb8Q9CeaggfBObrbbzeHxLXPivtGWP+4drao3+X1hZQvgv8usMaoHVjNjYe7kHyj0Xsn46xCR8kf165tb1d9H2PPCloNCaxquGXofmLm5tfm91pV/EOMqW9sPX1D29A9ivG2E/F2DQgyZ07x3snVb1l09qIfACkVhtjkiTG8AdQ/fzW1rObd1II7tD9Ha38j55Xdb8hYh5Q9R/I/f4GJmCRz1v8uOk/b9KbuID3m9SLOKcanxfxP7W5+czrd0oI7sAdHq38j9wN6b8SMXd9UJkPb3UDRd/K96P/q7Q/wweF/8BNQvAa1D+2tfX1V++EELzHW2wv4PjxR87FaL4oInd9kC19ASQoom9d7jc/hJuNPzVC/EDFJm94CK8ZEz97/fpTF9+rELwXATBA3Nh4eF3V/baIvf97tfLfROTom2r6Jp4KN0BgtCHXN6Fe0kQktna+8u23gKPvq7PoUYxSAdWbBORNvSEqqOi3/Pa7RUeaILwg4n9kc/NrW7yHqOG7FQAB5MSJR/MQ9Esi9hPfDebHxeWp6Js+kCoxBpwIqXVEH2gkos6gCqqCqMFicAIED6GG2CAxIpViA1jACBgUI9oGLWi/f4ThUpsQjMEbCIlBEosxrZerMRAEgm23CqsWVNpwjhqEo1d7DlBkwaM/Lhztb1rv5FZYckMI/tBa+cy1a0+UvEvv9d0wTOAxC1/23us/sdZ9Isbmlph/O2FYL0IQARGO1t0REMg5i9VIbKpWnSeKTwwSDVqDi5D4AMWcXqwZ2sAwga6B46vHWEr6pAa6TkhNJGmTtASFJkKtShTDdBI4qBuuhhlXmxnjosJrxIpDnCV0U+bGMFMPkuDEYUyCjQ4THSYajIJoRKRZuJXtsRVBVFGJiMQbAh4R9CbjVPTb7UHiVL03JvmE9/6fAD+/iBgeQeNumd6FBjgK7z7yd61N/vrtuHq3IwCNDQQTMcHgoiVRgwSIIWIyR0VN6UtM7kiswdQ1tgqkZcNSFDas41y3y6nEcn7Y4fRSn9VORi940hjIDKQmYjVgpF08UcELRHFEBA/MLewY5UpZc23u2RnXXNuesT2v2AyBsUmZdhyzQaspjLfYmGBxiNoWwiaKikelQQVsSBehUkVFF4KwWMIiN21f8PaOaOsihtD8ve3tp/7Guwkb36YA3GD+Lxjj/tHtqv3bSsSYCjU1LjqcTzAhwZKAGKbVFM3ADRKKZk62t8+pCk5kfc4uDbhveciFQZ+7ejmjUNKPDVmoME1NDCVowElECBgNxBjbRyFCEIuKQ0XwsSA6oen2qbMuhaZEM8DT5crejJf3Dnn5cJ9X5xNe9CWzJMVmOdEmFAiNMWBtq/glAgFRcDFB1IIourAhWsNDF67pm1aMvOOCbreDGP1/vL391P92u0JwOwJwZPR9WDX5Kmi6+N0tH+PWBUBwWpBoRZCEQEZQh+JIaNW2VGMox+Q28olsiU8N1zl/bIVTo5RhLOn4KVmY40IJoUZ9QxMasqSDS7I297KwJ1pksUWNQ2kTlGoMxJJAQ4PQYBCxCA4xKdLpUHUydrXiWlnz7PXAC1tjXhhvcgVPNVqiGnQp1BDVkKghDdJuU9JaBa3xSAuBuWmty831C/KOtt0CPS21SPPJzc2vPcttGIW3yjyBx825c1vJfD7+qjH2I4vY/m3l8W9HA+S+JtNIaR1Ta2kShwikZUFvcsipuuSjS0MeOXWCj47WOOUyUi2w9SGUB9g4w5mAmkCwlugSJMlwc4OtDVhDVAja7r9iE1SlNSJjq6C9FqjxJBwZjYoTIRKY+oIqVequwbucXO9iqzA8M9ni3x5c44/Ge1x1Cc1ghNLH+JS0dlgMtW2IEkEt7Rbf2i+CYlQQIra1JokL++DtSYOItTGGr3e7w09evLje3Cqo5Bb5cUP1/wNrk//iVo2+P3ayWxWAm9w1nxhCIiCKFGOGxZhPjZb40RMbPNrrcpoIoaJRj9OKJBRk6klMxPtAFSC4jOj6BHFYJ1ijhBvqvl2REYOGgFWDwSEh0DUVtimRKpAqaBMJjUetEBNDTC21BR8iSSnYzoDdbsq1ruOJwwO+8MprvHBYUeQrSL5G7XOaEIl2jBKwaY+68SiWJMnQqFhVDBEbbxKAW3po6o1JXAjN/7S9/dRfudWt4BYOfRTm/fifAPOv30ug53Y0QG0d06pklKf0g6fZvsSH+gM+e+YUjyz3ebDjWJ6PyWdjvHoaE3CmtaSiKGos0XWoXY+QDGjoMA/KpbjPDjPqEJjVnsoHqtAulNwmJCokauhYy1ISWE4dq2mXZSym9FB7nEbwAbwniWCJaFoSbGTeBOgMqLsjtkzOV67t8S9efpU3tMusv07dSbHxEI0etRnRpNReURzWWEz0GAJWFdFIMNyiAMBRoAjij25uPvlvbiVI9E6HFvhv5MSJX8tDiF8TsXerxnedlrxVARARptrgcstSUdHfucaPbmzwp++9n3MmMConuGYGvsTZSIZDGogKVZJQdXvM8w676rheKlenFVfGU7YnM16qp2yZQB0jRVDKEIlAliRI7bEx0EUYJDnBlgwzw+lOn5N5ztluj1OjPseyhEFdMWwaBmVD2jQcdAqC8Yy8wc0C2lhid4m9wQpfj4ZfvXiR397bZdbrkaSGOkQmlSfpLGHSHpUPoGCIGA1YDa1rKuY2BIAoYkQ1vGqtefjatZ8p4W+/bXzgHQ59FOf/2N8xJv0v363qv3GyWxUAIJOaZL7LelHysxfu5ufPn2ftcI9+MSHVSBSlcIbSCnltSUNC3e2ymya8WjW8MC352t4er4wnXC5nlMYgaY7KgEAHb4TGWYJxiBgkBFxTM7CWvgp1NeOACUJNVhfkzOkTOJZknFrpcffKkI+srnGX7TAKyixM8eWM1SiMfCCtAkGEadrhcGmZK90ef3B9ky+8+CKvS0LsLVFjKUio1BGNw1iL0dhqAHxrpNJ6JLdO7VYQY/0/bG09/TffSQu83ZENoMePP/JAjOZp2qDoe8rrv50AiAgaI5j2FEuH1/mYzPnJD32I7z+xymjvOqP5Iblvbc/GZMwkp7AZfmWJHYFvbu7wwt6UZ3YPeKkqmCYdmixH8gy1QlGX5DElMym1QG0sfoFMszHQEyEpSkxR0JXIhzoJx40hSRK8erabOVeKMdvVBGsdx9M+D66c4eH1Db4vgxMuUs73kOqAjouI8aixzIPgsx7RdHh+XvP/uLzNMwcThktr1LbDpApI1iEirSFIjSG00UlNb1MAbngFwZj4sevXn3p+wbNv6xW8zZGPVv8jvy7iflrVv2f0bhsVa4MdorL4P1QmUJqGrrMMZxUrk8CPdlL+w4fOsrGUM9l9jaGU9NTTkZTZXCnzJZrRcXai4yuTPb6ydYVXdva47qHsDal7PbzrUFU10kRyMWRWMKGmUU9wjqAWjEV9Q9cp3XJCb7zHh4+t8v333cP3pZbRvERdSrQJk6BcKgu+unWVr2xtc7mMdPMNBrXh0aHhh8+f5K5+ynEKktk2vtqj100oygqrCeu9VfZCwlcGa/zz55/nG7vbjIdLTJIeNR2MprgITmuEGowSbl8AaL0CZ1X9v9zaeupPvZ0W+A5HvqH6f0zEfeHduHzf9mQLfxc1mChYFYKN7NmCphMYNgV3Xz3kz/bP8gv3XOCEm3BY7kHa4DLFlzW+EWSwwbh/jKfHJV98/SK/t7vPVRFilqK9Ho1LKCM4l0AdcI2Se3BBMYlSmgZvMxoPaZJjqjnDesp6uctPndngp+4+y7Kf4/yYEBskOrrqyJo2P3B90OHX93f53BvXeaPqkqRr7PtDjpvAjw2X+fGlIR8fpAzjlNl8B7ERax2xDBjNCJ01LmaGf3rxOT6/t83OaB2fHMM0XTLvSLQBmaEm4nk3AgBHrqGq/5NbW0//q+8kBN/pyAbQtbVHft8Y+8k7JQBRBBUha4QkGIKBwgWkEzHVmOXtLX7m2En+woMf47wLFDuv0CGykuXMxhNIu4TlZV5VyxcvXeMLFy/yRozsDdeYdHs4FTK1mCYS64ATsKlFnMVLwMeACRPwFTEbsR8hz/sslyUnd/f4UydO8B88fD/rkz38pddJRpbCBMRDL1pSDLu+4HDUJ5y7m1976Sr/9LlX2O8fw9outpiRz3c5Kw2fOX2cHz5/mlVfwsEeHSPE4MlcjtYp436XN471+KUXnudL1/cohieppI+qw2iDSIlIeDdbwIJuxAa+ur391PfzHbaBb3PkI7fvkZ8F96t3QvUfUW0gGMuwNKQBCqdUqSfzU47t7PCz6xs8/uEHWRHP9OANhhms0oH9hqgp9fIqz3rPP33xG/zuwRZlbxW6Q/bIKU1OIkoSArZpSGJDKor4Gl/NiVqTOseZLLBiE8JwjSerOdshsDYp+Jl0xF96+KMshTGydYXTWGzHchBKfKP0VcicZZJ4tqQhSZcp0mP8s81tfvHKqwQ/YtRdItgKbab05oc82Mv42Qcf4kOdDLu1ycBEOsbgvGW3qGhObnC52+MfPvkMvz8uKJZPMzYOlUBCg1VPJPn2bLolarcC8D+3ufnUv/h2WuDbWPSfU0Bi5G8Zo+8chLoNkgUGKxrwKJhIEhs6u3v8+LENfuGBBzndzBlPrrCaevJomU8nuM4xisE6//rqJp975WWes4H94XFsb4AJgqkMfWMwJqIacKYm0RKZHXI8Szk1yjk1WOXM8iofyR3HSNjpLvG/br7OF66+yjGj/PDxE2z4gvFsm+5yQnFYYwqoej2aYUpeKzKfElA6iaN/OOZ42uUT/Q6f7wmXKmHfCp4Um69SpAP+YHbIla99k5+7/x4eO3Uau7WJKwuir1hyhtn1a9y1epIf3zjN7vwy36wLtNcjINgoWN60k949qcbI3wJ+bcHbt9C3CMDR6n/0syCfamv27lzZlottDr4xbaYvxdOfjHls/SR/7sIFTlUFbnqNY1mNUyHMI9POkM3BiF9/7SL/+xsXudjtc9jtEdMUFyNJ1ZDh6WkFVYVWh/SpONlNeOjuU3xodZW7+z1GITJQw9LBHt15pN9YeocH6GSP1c4S9/RSsr1tunmFt1A7xdohlzLLq0w5AVxIMkxrYGNjIJlOOL++xOluxosu4hPBzg22djQuo1wZ8LXJJpvf+AaHd5/hp9fXEV/hbMXQOrLDGnewz0dWjvNHwzEvTA4x/Yx6gSOwoc0wvnsSqxqiMfZTGxuPfmZz84kvfqsW+LY+fYzxrxnjoN0z7ggoSlFSLLEKzBNPkil2/4D7Q+Q/uu8B7o0NtjgktQErQj0PaGeJ8XCZf/byS/zzNza53F+h6K0Q1JBiqecHiI0Mcks83CSfT7mQZ/zwyTN86tQGx1E6zRyzt00MdRtjrypiSKnKGbP5HFFY6XZYSxJGvsKGwHTa0Ikd9pOU37j4Ep8fX+Xj3T7/6fkH2dAOVZiRJY7Q1AzEclINZbGDTzOW0gFGMhocpSoy2mA3ifz6a69QTfb5qfvvYslH/MGEpTzDxoo0VJzbWCI53MRq02Y9a09qE+5ASVAEMTGGvwZ88Vv/eLMAGPhcOHbs4ftEzE+oBr2zCB9BfCQPCh2DL/Y4EeY8/sBHuLcpyYtDsJ65CqZUGG1wuTPil559ll+/vslk9S6QPmamrOcZ1XhMnighqYi7W5wn8Kl77+LH7rqPc6EhvXadY6qk0RO1oTFKMIIRiN2c2uXU3uJCStd1UBOZ+zmYSNRATByboeL3tt5gupTwxN4enx7scPrUaeazOUVqqDzgKz6+ssEDk0MuH+7gkogkjtJDXUa6mSVLR+zLmC/tbmP3u/yJ1YxjKWQxYLwnaMmgk9B1gjQVLnEYbNuN6D1XVIhTDSpifuLYsYfv29n53IvclC28aXU/1ualjP1LxthkUct+x0iAGCPWGpL5hJXpAX/y7HEeO7nCqNgj9XO8KvO0T9Ff45XOiF+8eJnf2NyjPHaWA2+wOFZtit3e5gyR9TClf7jNZ1eG/NWPfpS/+OC9nCp2iZsX6aeeoHMabQgYNDpC45h5YZL1qPqrOLdEpj1CbRh3DLudwDxTZins5KB9x93DJQaTinv6fU4sLzGdHEJoiC6iHaiqKR8aDPnLH36EH+t2GOxdxkw36bianlNcXZP6BJsPuYrlmYMJVTSoWEoDpYVaGrLUMkgdrqpJYkScUC8SQu+dNBhjE2PsX2rfP3aD70crXODL4dy5x/L5fPIX2tYsd754U50hxEC6t8/3L/f5M/fdQ7p7DakPSZKUQnJ8NuQw6fIv3rjKL1/apB5uENyAiFCHgAkVawOHnW+y6vf52fse5OdOn+TM+BD/+utY9WROEBuYpW0uPpoMbAexGbMksJt2+ea8YafOSBgxrwzXo+f4KEdNAd4w1YCVmj9z3/18+MplPnL6LMdixIQpGubkroOxjrKe0Jsbvi/JufvCfTzQ3eZfvnaFK01DsnqCovbMYsMw6WDrPpQJeZmQ1w6iJxiloQWnpCGSBkWJeGPxVt+7AgBATNtnSf7CuXOP/e2LF79cLQ6rCwFoGzfM5+PPGOPOqfr4XgXgzb59urD+Fe+E8XTOJ/rL/Nw9d7MyGUOxB1lDxKIBPB3+8I1tvvDaJQ6Ha3gc82lDZ2WJeTPHE6l3r/ORRPkPH/w0nx6t0NndxDWHDI2QRUVnJU1UNM2pRyMOOh1erz1Xyikv713hlXnJlbjBtdCl313nsNjmysGYs4OMZPeAFTug9MKeOeD+vM+n1+/CzQObsz2yJYsPgayeImQM0pyiKch299lYWuPY8TMMbJ9/fukKz822mfS7pM5hJpFh5fhI9wzrlaFbTgjWMbe0Kd8QkKYhkYRalcZFcII0d0IAMKoxGuPOzefjzwCfPzIG37LHi/DnF3y7bePPKhhtKy1UhCo2LQjDJjResSKkSQI6od8bcvr4OYbTXbpakISaogyYE8d5uQn8yqWXuJQ4TNonFhVZllH7EmtqZH+L7+vl/MKFe/hEntE/vEotE5pepCyEpoIkWaHuDdnu9HhyvM/T16/yymTGlfEhk6RkkqQUWYn2O0j0XDqY8cS2cmFwgjMyID2sGTlD7EFdHhDmQl3VdAeOGRVNZmm8J40Rnc/paULWsRTjbbJ5w2c3TuPyjF9942W+uXsZdcKJBh4drfDJpS7KHt4EYhWxSYqxCZvzCVuUFL0OtYG0sSTqCNLQAknbxWRQJB6BRdtgWjBmweW3BQFFaRHyf74VgAXPFy9dW3uoD9nLImajBafdmuAd7VAuQhIVo0oQiKljrkoThcQmSDQYPFmcsVZM+WQn4zOjIY/0+hxLO2inw6su4f/59BP828Md/OpZDoPBIhgLwVQkszEfSyz/6bkLfDq1dKdbqJtT5jCrA6ZO6fVOMHFDnpk3/JvdTb66t8OVuiTNe2QuI5hI44TCGioRrIF0OmFjNuHPf+h+/uTKEie3N+kcHHDYszSJYVCDQ6gkcpBGJongsoyBTxiOA9msYd5tcHmH+dhT2R7F0hIvNnNeGG9zOD/gTN7l0ZXjHDeWotoiLWuW7ZBZdGwdW+UXL73Eb4z3GS8dJ/gOo6JL3hiKvGxh76YFl9oYSaJgg0GxNNZQuhZilsT4dhhCBRHVuAnVPW07GsS92a2r8wPGyMbC97/l1a/S4uJV2pVvo4BE1Jd0gUQVUx4gVUMZG8qk5prU/PrBmN/ZgzO9jI+cP89D5z/K1164zDfmNUn3OGXV3orPhU6iZAdjLqjy5x54iPNOqGYHZA5SLNkkYrWHHa6yqY4vvfoSX9rd4XlVdrs9quUlSttuMU4s0QqVMTTGgoDvDdgT4fOvv0Hd1PzgiTWWh1260yn9KiK+heZp4rAuI+nnvL65Rbm/z4fWzrOynDIt38AVM7q2QxIrzGSf+wYZp06vE+0a3SYymJR0Zg15UKztMgnCtD/gGoY3dqZknSHOOyKWIol4o6gIwQpRjhDDtq01UFk0shXMomDlHQCkAjEaYzdi7PwA8FvwuHFt122A+NMiiS46dd2W+o+mBWNEAWuUJETy2JA3JZ1ixjEr3LWyxFr3GAbDgat4ZXad16Y7POsrXrjyGt29MbOpRdMBNl2ibCIuEbyrmexf46Gm5j+4/yE+4QxZM8Ezp7QRWwm+TMiOneH5Ysqvvvw1nmlqXktSpt0l6iyjUsVHSLOUzEfSBoyxrTCgdGxKmue8tnWJf/H8q1yZFHzszAkeWuvjiwZTtfUlhXVcN/DM61f5xtWrzJuS80XGDzz4IOe7x8j2N8mdoxcirh6THESymaJpgq09nRoyDyYKvttlV2C/O+B3L13lep0gnRHWO4wRGhcIFmxUIoo3ZiEAbXTQiGC0De8fNWS4FVaJGCFWP90KwJYcbQGsrX38aWPMw4uOnLcsAFFaLP0iyksWI/2mJp3uctYEfvD0SX7o7rOsJTA68CxVOftp4NrQ8my5y2+98DLfPNjl0HRJ+qcZ+4w5CR2XkcQKmDAcb/LnNtb4P1+4h+HuFkELZiZgnCOplNg/wfOV4f/97Ff5qp8wWT3Boe1QR0vuulixeI00MdD3Sh6EsMABIo4YAibUdF2EYow0Jcsdx4VRxvEsoe/6xAa253MuVXNen04oOyk2zalnNad7Hf6jeze4n0BvPONYVTJQj9iGWjw1EAJkmpLbnFmwbIqlPHMXX9ze55efe5HZ6Bgzl1FbUAmoeEQDNlqCFSpjCcYgakgCpKG1uyASzBH733HXjiLGhNB8bWfnmY/d+EZb1m1eXBR43PL+D282XFBaQGMnNIzmMx7u5fzE3Wf41PoSS9NtzHiHUe1Imi51bJh2E+arK1yzji+8/CpffOMym8kSk9EG10WwRuhXc/rTHR471uUv3XsXD0wPGMzGkBj2BcYuRbpDnpjAP3r+eV7WkvnGBtdrj7UDBtohmQVcVDQRKhuwBBwCUbDRYnCYCCIRYyBKQx1Kal8i9ZyOCB2TQxCqECgTg4wGlEYJ0ZO6FN3f40Na8vMPPsAD3Q5rkwOWqhlSHRLVUyPgOqhaGkkoV5bZlIQn9iZ8/vXLHHbX2U071C7BxIpOrOj5GZlGKpNSiFAkjtokYBJsMCRBcREETzRhoQHe0Wlc8DY0Ity3ufnM6228N7pPGGOS2838KYoVQ6qGxlf0rJBMDjnrLP+Hhz/Eg+pZvX6NQTPG+TliDU0/EIyAL5GDkvV8if/jAx/B1oZfufI6prfMlirScbhmysm64E+dvJ8zTYnO9lACsbFEk+GHI75Z1vzjF17iuSRjNhwxcRkqXZxPsUWkpwaRSKEBTZRDKYFApg5XRRIPiVqi19YpTg0hswTpYeOIWa0UdcSmCcZYVNoSMuMDiSppCLhOn9cnnl96/jU+uXGMHzy+xqlul7TMsRpoMPgkoyHhUITndM6zly/zyvUph9ky06TDzFpiInSaQGc24WQ150c/+SmevnqVpy9exC2tMHFCqUriOhyVt7bKty1s+U7bQIwRETDGStM0IcvTxMfqE8DrR27gp1q//XbrygRCi/QZJTky2+VYbPgTFy5wT1TWZxOWmwbjPSiUMTKLdVsH54Shs+xPN0Ejnzx/khcO9/nD6RYrK+vMmzGD8oAfXt/g4ayH23kNa5TaGcpgKfIBl4Pjl77xFK/GlNAbEaJgK4sjIfeGVCDQEExDnbRBl64WuLokqT15FRhKxiDpIFaofaCoPRVKbQ0z1yfYLpqnNMbhI0SNJELrnWAwoWpd39WTXJ7P2H39Cs9ducyHV5c51euSaMRmCaWH3dmES7MxT1U7TILgOiNi2uUweEo8qVFGWjOaH/Cx7pBHbUZpYEdrSl/TSTvsNhB9xIhBZeEeLopnbxU/Dkoxn3wK+NxCAOLHta1QuK2Yg0hr/DVR6ahiyglnBzmPHF/l2GzKsK4wMRLFUfWXqG1Clw7qC4rpPjYtWTLCYbXPyY0hH7n7JE88+xy5XSWOD7jHRX7k7rMshxq8x2SWwxjYUYMfrfL5b77Ik/M57thJtDF0xJKKRRf+csBThSm5UwZGGe9ts96U3NvpcmK0xKnBkI3ugJFN2xsxhqn3bB4esjmb8lzlea3YZSIKgyGa5VQh4q3DRsFHQxCHIEwqT6+7RN7tc3Gyx/WtQwYyJlVoQqRxjsoYZkaZjVaIJqWsHV6FJLEcc0I42KJbjLlX4Ic2jrM2OeD7l5c47OQ8M74Os4rBYJ3KWJr4ZhnZrVkAcvSvqAZCrD8O4Nq2rdzb5gZuL/qnCtEY6hixdcmIwPljQ0ZakhcTEt8Qomc+7LPZd1zdK0inNadGfZb6Bp3s0cUjVim3N7lneYWVpMPBfM5qiHx6Y4XT/YTZtWusJSllOafMU/T0GX7j6hU+f+0S2er9jDGoaV012xbc0NCgztPLEtx4h+F+ySeWVvj0mSXu6+Wsdrr0NeLKAoop6gOSOELiqAYZ5VKXK8bx9cMxT25e5YWDq4z7I0w+pETwxoIkbbGJKt0sJYbIXgi4bECS9ZiGiHhPVEVTh2YJHkMsGtQ5GudoiHSt0p9NuZB3+dSJ41wIJXcNM9LykFOp48fP3836tODpmeelsqaJFpvmBNpq4rjoZWRvJXwjYmIIJEly710PPdZ3xnTPq4bjeuRU3qYEiDNEsYRQYB0cG3UY2IDzFUSlFmHc7fL0/ja/8eJrXJ01fOL4Bn/uQ/ewEWYksxmdOjAygdWOYSPt8tKk4HQn4/s21vHFPp6KGMFpSpKNeMMr/+rSRfZ7S+Suy8yXkFqsb0u4GglEpzgJlAcH3O2Vnzx9Lz96/C6GeoBWu5jpGKlndJ2QOcGHmsYrVSWosRiEh2vLo8M1PvvAQ/zW9et86fo21+aB0F2nUrtIlhpMjBArAgG1wsxYZFGFZFwLdBZnKExEK8/JMKDBcJhGSCLNfMzQV/zgqfP88MoKK8WYMNkm+AI5bLj71FnyjVOkVWD8ylVmk5qY3Bx/uTXGtTaDSAgel8jx0Vp63qnGe9u2I7fn/i3ECRsiHY2ktq2z69guy5qShICXyEEuHGbKG4cHXJpNORTh4mSbzXCSTqZ0i0jfp2SaokZI8kh3csjHNk5yJgnU0z1ElCgpmvSZJSO+8M2XuUwHP1phWlTYLKX0DR3bpWhq6gxS29A73OahquEvPPBhHl1aIV6/hIsHZKamY1MwFj8pUGtxzmATwRIopSJFGYkl7l9lvejxcyeOczzr81uvX+H1g02q4TGmmlBisc5h6oCzFgwoERGLNQZF2xJxH7FGcMairsZ4JS8iqRcS4yhcze9tXuL6pZf55NIyDw/6mCDM1wzPzw/4o2tXeT4mXKqFqUtwRhYg2xYFrm8jAm92UWkroJ1zMSKu3+/f61T1vvYDehuFWzf4j4kB01RE5wnR4L1BS5BgIIt4F2jEc7a/wv3pLpt1yUe6Q0YEjAkt+j0mlNEwIVBJxTEqHhr26IUCqzVEJZiM0mS8UQZeGleMO11KMQzTlLKuSazF1QaJQsc69OAaF+qSX7hwgU9nQn31JbCRXqbEeUWMAi7HdzO8OMRBpKLyczQoaWo40Io8NZimoLu3y/ePjtO9t8v//uLzXCoPqPojxhhwSoZgFj1NcgU0oN4DcmNkVRJag+0wq8kSyKIlBKidcDVP2NaCF+pDNq9NSeUC54crvBAP+e3rV3jmsOB6PsQP1gkhQbRV+S7eZAR+B/7dEICFpnAu0bpRLNznQO6+Pa6/lQJKYxRjLbV1XJ1MGA+XGGZdrBT0fYMfN3x0sEr/3pw9lPtGHVb9jM4stOhggEGfg6pmOh5zKlviRG8JF3ZIjUNMZNo0NF3Li1c32fc1weQgpq23DxHrEspmxiBNkMMpa43wU/c8wP3LQ4prVxkYAXFM5zNMPmQqQt3p4ns9DqoKRRmkQ/LosfM5RV2QpQ0opCYjVjXsbnP3yiqfuesC//LVi1Tzkn5nQNEoYgUfPdz0sFt+6M3tPogilM5SaouMVoTGOQoBawQr8M2tXX77cI/s7rv55qs7PL87pewMcfmQJrah3zYnAKKtNxJE3jmDo0edVhTvA0VR3+1EOLO4wtvOOooIgUiUBJMIc2N4cWeP7TPnWM5SpCzo4NBxQZak9EYjDjKlPznAjfcYpg5nO8xImfc6XNna5bCc8eH1s5zKe+jOZVwCAUOZpuxb4ZsHW+wFT7TuRvyzYx1NU4ETHCX54RY/ddfdfHr5GLJ9GRdqXJpQh8hMMuJgjR0beWE64Y1izBvjA6rKs5Z1OJN1uSsfcqa3QidOcPMpyyTkJkA5RcbCx1bX2JytsnP5Ornr0jjb+tqm3Wf/GBPe8l5xwWLUkgTTMlAtQZQ6BEiGhL7lUnA8sT/nucJwkK4RB0PKEAlRSVAMHqOt4k9CWzrv7a3VgytI0wR2drbPONDjt8v4G7eiijELKfaRNBtwcTLmDza3GK0MaOoZ/VDT8ZGkntILFU1dMyhKei4FFfabSNHv8Xwx58lrl1CEuwardOsGaTzWJFQq1IMurxZTXmsqik4HTVIIrbNnQmz33b4hjg95KO/yI8NlBtev05eawbDD4cEhjcvR4+f4RlHx1dcu8vR4j2smUvVyrE0x+xOW5nucTfqc7w752Nllzo+W4WDMqCnoiyKzPUJmeOT4Ki/u7fNCOSPrJRREZFGd/PYPDbIgpF5JAhg1NEZwLqMItPWAbsi1ecXBy29wTZV5ZxljM2pqrLEQI2qUqLJonGXa5XsrTsDiGjCO7d39405VVhZXfdsaQFWxtrWYZ1VDpztkr6j40qVL3H3sIe4b9JBJw0AFosfGpk0Stexi10fmozV28z6/c/UNntnbYaM3ZL3fhWJOKhbConwsSXlxe5NN06putQk0obUPQo10LI3zSFPwieN3cS56cl8Qk5r9siT0OtT9Jf7g8IDPX7zClfmUaW9AkSeUWQI4OqNVpnng1XnD5XHBG6+MeeyuE3y42ycpCvqxYSDK9GCTjZMdPnxqnddfuQK9PoghhHfmgKBYbYGvVtr3DiFiiImlDiWHAr6XsBuU0nWpUZqqwqYWnNLUTRuVVMUo2EUfsluCj4kQfJA06VBO5ytOhMHtMv7NYwmEgFFDz6U0HqQ/4uX5Pv+fZ57hz919mo/2u+j4gF6aMA8lqso8QuwOmPaWuZb2+PKrl/nCa69R5BnZoEuSREzV4JzFN5Gk02GqysXZjEmS4NMc30QyXRRTWgtOmNQT7uol3Lc6JD04wImnksis8dildZ6ran7z8hYvqMUurdPYtiLXeiFiqcWgTij7QtKPTCdXKF+7yOiBB8g7Gb1ZwSg1ZE1DWk+4a2nAMVezOd1ikI+oY+CdugurKLVr8CiqFhYZPh/bbB9JoEJpEKw1SCxJVUitAoG6qohWqE37/I3aNiegt5YRFBEa7+n2e2xPxgOnqp2jPorvSgpUsdFjSGgw1JIy6fZ5avc1zl5Szl04z1JiaaiQtO3fN02FnTTn2bLk3zz3Gi/tFxx2lvBJQYyejgtQNzQELBbUUTTtdjF3KZEEFyxJbPFzaoQQPUYDp3o9lkSxoaS2NfMYcJ0hB3T48tWrvABMB8O2WWS0mMbQFUsUwYvQCMydQYylO1rl4uEmX716nVNnNihjRZwfEo1gqwmrvYyProz4+tYepQ+L+OM7PC5RvC3b9nDaJm90YcR5gWBaQE0QsGJIQkpTNaSdHpUIUwONzahNRI3FxoiotAmuW6AYAp1OT+qqAnEd107Rfg8kSjQeEy2iKd5AYT0u6TIJDpv0sU1N5QuMGpCcXYR/+vVn+EqlbCUrhGyIG/VgfpWug54B7wtA6RqDYCnqyGHV0OQdlAQbDTYeAZcF4wNdVc73RwxVidTMXcBjcMmAa4eer00qdvI+2ASjSiLtHmpiC75Ue4SbiniU0uWI7fHCzpj906dZzftoOSdNDEld04kHfP/GMS4Ml6kwiHGtEfitUnC0P9Oa2onWiLYeQRQ46hQV2yRlCxEVBdd6SFs7B+xMa14fT+n0hkyzLjsholZuZGGNyo3mU29HxlrqqqFuapaXV1L3Xit/oomAR9QhaAvuJMXZAZnrkYaErDYgFjEZkgy4Mhvz9WnFxeEx6qXjyDwhrT1x5hkOcvpWUWmoJJKFNsTbeKX2gojDRIuLgo2KmrYTZxqELMKppEfeeAKR0oAzGTZkXN0as+W6xO4AG1p0jTcQVTEm3ujYZVRIQ7s/ezWYfIl5UfPGzoQzyx2MSXExMHIOrStGpuJEnuK9B9O84zo0Ct2mDd+0FVKtwJio2LjAVCIEI4QYqE2NO7nMvs/4w8s7/NudXeZi6fT7zLVlvtOIUVl0FHgHG0SEpvF0Ol2suzGo6N1SK8FBAkYWo4AwgCU0kEtG2lhy315U3QRc1qOgYuxypoMRk2jpx4Q0QpeMLCjWVzhnKMIiiqYs+gI7ULuI+berN9A2WsyD4AIsRYMpyzbr7QzSgI0p85kyThxqUlwdF6q2/XnUrNGqYBRSBYmWmVqs5KhkXNubUI8GuOhICWhRkitofQBiMDSIhG9viavcZKAZJLq2E7lTpEV1YH3A1QG3CMa2DWI84qfo/gFpd4MfPn+esaZMxhOqjlCL4GLEqWKi0NxCP6EYI2maYEzCbDbB8Z7GtmkLqtAuNjqCRIQGocZIbPvqOqHWgHVg6gZtSmJimFuLqtCThG4Ea7W9qSTBxi5JNaGJiosG03b0pbGtr+sNZOgCBRswsW2rliHkAKFBCSBK09RIChhDFTzOR/IQW8tajpowtVwTFVyQBdrG0tiEQKQRxasnEYM2SpFYiiygMbBcB5YamLmG2kQMpsXIHRlWN3oiLIK1ajDR0CQQTAOqpFFw3qCSMpM2tJsDOZakP2I+r7CTHQZJwqPH+1yux0yqGc4OCCTU4rALQb4VngmWpq6xSnDa5ms6704A2pWShDYlGomIBAwekUiNpzZKTSS1SpIAGgnSMicJYJqGTgPB1sxNQ+FS1OSId1gFq7I4dsuEYCLRaKs6Y8TG1ozy0jKqMoo4C1UEDYgTGqkwztMzhmBajJ2oImJaQGU0Lb5O5Qh4TcAQRDE2EkxDJ8txWpNbQ20iZZIQFLpB8Y0yM47SCjYaxLQNq2URe7/he6MYNdhoKWNkrm2rWlcZJOY0rkPhFDEeV9fYpmYuiktTulGYFHssj44xcg2u8UAfLxYRgyO0Qv+OVoAs3EeDMUntRKQA6dwOFPxmUtoV6SI39bttpbEOnhBbAKYEJXjFJxGHwWo7Cj5oJBxVwyI0dU0ZmtYiRvAtBghjBKeRxEfUtccP7fPFWUujgUIim6GmyTPS0pIETwBqqen1LcNZw1ao0DRbXGgL0JRFIDSKUNn2pQiVCZgwx1GyNlrG1xOsBLIm0JsaQmdAmcJlo1RpRjALxO6RQN28J2uLlgZDEhxlEijSBqsRzQxVY5mroUyFxAQSnZOIA5lBVFQFkyRg3AID8CarZPGbW0fzyAIiLoVTZSLCyu0y/oYAGFi02XtTAExrYJUh0LAQrWhQbWXU2YQcgw26CCW3hpxFqeqaWfA0VlC1LQADT2YThsaRNp6QeaJYvGmDIAGlcZapCq+VU6b9VfqakDV+cayS48tdTkwqdqs5vtuBRct4WWyaQVvDy1vT2jUoVjymOGDVKSdHGUwPCNWMLDpGWZdx6PN8MeFiU1I5QUlaYw5hEaNDVNq8vQiIIRJRrSiSSJU0OA10K0OmKYUq87Ih05ozBj7U7zIsC0QDRtpUUzCGILbthSggGm8I2a0LgSJqUOzEieieiDmn+m41QItdt2/5XYu6nWugNoJaB42gUcEastiidxIBL60xdpSHLr1nqp7KGpwkVCHSSKDjDKvO0Q01jYa2nbwFie1tR2cpo+ON2Yz97jHWgsWVkKWGuZ+zOujy6KjP3iSw1XgEoVHa1u3GLYxZRfGgQmIiuZ+xWk/5+MYqKzS4UGGtYqPDaZdxlfD7uzO+GqeUxqNhkZyKillkAVXbtvft3IF2poGVSJV4autJYqRbWZxaaqP4xJMUB9zrLIPeGR6ylugbAlBFpQqLDOrRsxYQaZtK3gaeTxERibLnQK7fLtPfciRpa9tcbE3QI5e3EUOhkYKIF0O2yFxrjPSso4fBhQipEqziREEtlW+YiKFyCaJlu7erp+uEtdTRP5xThIbGGLwuwqhBseoQm7M1L9mLhlo6ZFqTmcCsmtPPC35wbZVr8wOeOhijnYQ6z5hbZaaBQBsX6EVZFGl6svk+H84SPr4yojfbI9EGyRPKYDGuxzWvPK+Gl5eXsOmAxFsckCLYoC0SyIA3CQVQGcEaS68KeGlobCSNYFKHBqUyEddpbRsM5J0hYVwChqCtlqp9W20VxbaRQ221wM2a4JZIQEWuO1UuvWs8wJEQLE5tFXyk9QOMMgmBSdNQG+hgsAbmVcFw2GUly9Byjib9tnwbsNZRVJGt2nOhk1NP9zFGKJuSXAPn+wMG24ccVDXSTfAxtn19Y9uFu5v0mFQFL+yPua8/ROclLlaMspz55JCTnSE/feYsnTe2eOFgk/06ocotWS9vBz0UJb15w6iO9BrPfaOMHzl7nPXZFDeeoKkyjoYmzdBeh69fucalBJrlZWQWMT4Sm5oQPITWfY3OENMcl+Vtb8K6YRiytlm5UTIcphYwCfgKWzd0a8PxLGVYKMEHGm3jFuJSyhCoYiTahSt5ZLbKbShwRUUMIv6SA331XXH9JhIWeDxtAx0A6iwHVclUI9GlFE0gTw2Eik7wnOh0cLNtjATULoo01DILwqsHYz6xfAo3BRIhMUIoC07nOesiXKsryDNELHhwzlGEiNQgWY/f37zCff17uavTo9PUbdp5PkObA+5a6tM5c5xzfXh6f5tLVcFhMyFEyKuGDbVc6I44t3KMe5Yy1so5vWJGYgyNdcxcxiwb8npd8M3ZBJa7JEXDys6Yk5rQdZaOCt00I0tTCh+4Pp+xPzmkTjM07eKNo7HtghDaohWMQW1KTY0YwzDLyNv8MipCFEOjQlF7mhiJzqA3nP54I9d/awzThUEaX3Ui8uK7xQMsWP1mECW2HThUgdRxMC3ZLmfEfo8qKrko+Io81pwa9sm2rhO1wbmMFkuVU5mUV8dT5mLJVVDTmlNaVRzPljnTHfC8byC2k2hFodYIVqBWNOvx6nTCFw+36V84xfJuQX2wy2q3R0pkvnOZU8vH6K/2OD1K2EW5PD6kqipWVjsczzusu4QlsfTmU5JqTpZCEy2HNZTLI67ajN+9fIkt60nqhvXZjEdU+cioy4mVFXpEEhSipzKWqVnipZ0dXtvZZaea8PpgmdKlyAIyJokhukiZRDRUjNJA1rOoVkBcbLNt79BJUVN6hbw1BM3CvRS5nXYiKlBjRF50Iual9zrqzWjrBtoIxrIIeFtqjVzf36Ma9ug4S9BAoh71Dau9HqNuztXo0VSIoQ3zquuwVwWuH4xZMxbvG4wqaTT0VbhrbY3Rzg7XNCKmjYEXGhCX4hpLJQkcW+VL4+t0rtT82RMncU3JrCowqaPf8Wi9SW8u3J/1IetRDFZwywkxNOALtNnH+ECviTirzENgGiO+M6JIhzy7vcc3izHSGbBUB+6SlB89NeJUCq7Zx1VzkuhxzjJXpUhTTp1d5b7lhN+9+AbXdNbGSgIY6eJMTklD1Aa0JksiSx2LaYq2Vl9s60EozMuSJoZW+91gti4Cjbe2hkUwkcYj5iUX4/x1key6iJx+t57A0anbivWFL2gs3lm2pxNKlH6WEeox1kGMgX5qWMpzUE9Aib6N0iUmZRZLru4d8PBKSlXOSYLSMxm+LDm7vMrg8ACnEa9t7MCmjnmoWcq7jEND000oXZ9/e+0yJ8uSH91YJ0SP9zW9jhKKCSNy3AzC7pRVm+I1LAJXNSENSCLtlLEkZS6ROBji0yWeu7bF05tbxOUhTVFwXzLkJ0+eZzVcxRb7bcFJDKQasFEQA36uFDJntZvziXtOsHl9ThYijQcTGxIypjQkmceGwEaAMyQMypLSHJlmhoBh7j2VxtYmiEcxgFudKQC00iJovB5jfN1sbz83VeWlRXPQdzV7LopS20Bj23yA9Q5kyCxb4qKHTa+Icdg0Z+ZSat9w0jge6Q5YmU6RpiSiOEnJbM5BAl8f77HtMub5ANMdEuqabjXjtK350MjQn+3Qo8H7miwqnRhoqPEO6mBRt8p+fpzfuD7mN7dKdkbnqXqnmPsORnqoGmJTkMmcnpkyYMJIpgy1otfUpGVJQWA3sUyX13i1v8qv7E/55a0DdvIVEp9yOlh+8Pgq67pHUm+TUbcYxuCwPiOtHcNKWI+GlaoiP5xwPAZ+ZH3EqBxDAGdGlKVBE0djZnSYcqE3YCnmEBzYiuArlC77vsMl7bCXD6gs5KGh23iiQOXMLUYBNAoGUfPS9vZz04XaN0+KyGdvtzTsxiEXeDSzUEMSHT5YSIZcn2xxrSh5KEkJVUmDoNHTDZ57ez1O+EgdPU3aRSulipGQ5rw83+X5ecV9y8vUe3sMRSDMYbrFD5w9zsvTfb62d43e6ByzYk43d1Tek9uMRC2mjjR2mb1Bxm9u7vHyeM6j505wT3+dQT2HpkSYk8QGR2j3UGOIxhKMpUEoOwPGnS4vFw3/9uIVvlkr0+EKiWTkkwMudHNOJzV2fI2uiUBbwBnTLo1xdA1oM6OuZ6CB3ArQcL6fcSJzbDVQu4zGRqLz+FDQNZ6TvQ5Jsyi8iQ0mGqJkbE4j170w72dEI3R8II1QGMEjJLemvHUBQnkS3mwS9QfvqjDkBslCEPTGywdPN0+Z7FZcG48pT25gijFZaFCUuZ+yPhpytt9jaz4juB5NaqlqyCRlR4Untne4a3kN05i2lXwKTXXIatXjp8/dw/5TX+eg3KPT6VEFJRWDjS2IFAQJnsqlHAx6PBkmPPvaszw6WOHB/hKj/gqD0TGS2CDBo9FjbBuwqUOgCLBbGV65OObFwwM2xVF2h0iaE8saCRXHl5bJ/JhuLOhIzswnzLIO+2nCuG5bvq/0O/Q1wVYlaTR0GyHOPeeXV/jGTkFBg8lyRBs6ledkL2M9zWA+R2gWyJCM2hquz8bMYgMub+MCIgTTBoXNre8B0sZr7B/cEABj/B+qmqP5f7dlB8iNSHRsI2mLF0bAOkKScHF/n+sba5xxCb0qUtgG1ZKVdMiHl5Z55eJVpm6KX1rG2wwtKyQb8PRkyiP7c453lyj3DsnSyFAi1cEu96cr/OSpc/yzSy9TuQ3qtAcxthi50LpXxnWY+RkT45B8gDEZv70/5bndkuX+gKVuxlIno5MmWJvgK8+8LDmcz5hUFftFwiQ4imyVstuhdA6MJaUkEc9SNyGtD8hCgTSO4DrMTcbL85LndjYJ0nD/+ioPLvVZDkpeBVxZk6nlxKiPNXPm0tBNUkxTc0wc5/OUY0RsmIDWOEnxSYfdxrPlK6rEEl0bBAtGCNo24bpFAVAQG2NoxOgfHgmAbG4+c3Ft7ePfXDSIuC0BOJpxF8xNuDTTHmJelPS7Q1473OSFyYRjacqqSSipsMaTzCd8eLTEN7N9duqSCRGf5EgJTXfEllG+8sY17r/vPMc6XaTeZZgI6hu03OP7jh3nerHGF4op5SBHAuAbrFhMbANqnf4SPsyZVYe4pEu9tMRmHblSVcStA1KBLHFAQKRF4HgiAUtteqSDFbTjOKgLGlUSMTggSRKMQIgBMYbQ1KiL1AqbhxOuV3MCntF0yvlRj26o6fk29JvVKWntMVappSGJJb2q4FTuuCfv0CvnuFAQDSgZlcl5fTxjVyNNmtOoEI3iFVxop5xZORo9+/bsEjGCxm9ubj5zERDTjoFFQb8oYvR2DcH2nAbULCBNsQ0zhkBV1WjaYQfhucMJh2lGbSwkFqOtAJxNhYdXVxhFj9TFIvcnYHpU2YinZxOemE+plleIMcGVkTAZs5Qbes2Yz5w5zkODHmZ2iI1zXBIIWcMsqZlJzd58RllHemZAL/aYVLBvEprhEnF1nWK0wmE+YNZd5rAzZNIdMO8tUfWXCaMl9tSzNZ8SE4PNUmIIiLEYk1DUSiU5lckIqUGsx4aavigbJJyQjHWbMAxKEj1iGsQp2igxtGNjkZpMazrVhLPOchLBTidYGiptKCVj7HJeLebsJ5aQZsTYajgFgpEbtYG3wP8oYjSiX2x5/pg1sL4w/My/VI1H3twtk+qR+ll8TRRii2dJ05wqCiEd8tzemCsqTFxCJRZCpONLBtWcD62OOG2hW07JmgpLBA+NJuz2evzWtct8o6qgv0rULppkTKoZtpmzUc75mVNn+UxnwNrWLsvFhDTM8czRHtB3xNRRK3gvWJeCNVQxUmOINsG7jNKkeJPSmITGSBu21RqTKmkqiNZIU5Jqi2MIHqYlhGyJCSm1BFRLelrz8bUNPrt+hs+unODR7hLD6Zw8BLCRQiIzlzAJQuUbklDT93OO03BvN2fkK5jNEDFUYqnSPteC8HpTcZg4okuwQUhCy/I2HCzvDAVqmWNaHsd/2b5fV7cYMAgUX4kx27zdNnFGQdUgCxBTG5sWrFqczShLj00yrtQznt474N71ZeqdKcdSQxpqYj3mWD/nI8dGvLa5y57kSDqkmM9wnYy4ssQ3ty/xW6++wem770V6lsaPqYxHQ00+L/mIGzAYrfN7+zO+vreDZClueYWDoFQkNCYhyyyKxWiFU9/msZHFzzdv9i1zjaSdKmqIuBAwGJyHHkL0DfuHY5rOKsF28FKh2pDUJcsm4ViSkFjBVQXBF0QH3jpmAmYw5OXDXbyx9IKnP5nysZUhp9OInU1JjFB4JY6WOHA5z+3ts5MlzJKEuvZkCIQWFBMXYWKrBn37YaFK2zR6E5qvtL/6XFw0mHrcbm8/NxXh88YY5Tb6BLdJoKN08AKqoBETFSeWRg0x7zHLcr567TqvRMWMjuELTy6C1lPSMOUj68d4IMsZjg/J6jmpVVQDQRxlZ8DXZjW/tbnLq/mASf8YmvaRAJkR7NYV7i4n/PyFc/yJtWPcU5cc291lZT6hX89JtUZNYB5KfGxBGIbwlsaKurj6N/EbLcJFtMXd5SHQDQ3duqLjK7JY0swO0LLAoC0iV1ukcuJLkmqCTPcw5YwEiDgqyZllI55X4dUQMUnGwAfuSR0Pjjr0qjHGz7BpQoWlNBmbQXlpNuWwk1JmGaqGPFpy3y6+aFpv4J33fw1GjIrw+bZH4OOWG+J/9BHllxbQtVveBgTBhjYq1Q6FavMCDkFDxEiCug4h7/NGWfHEtWvErId4WeTNPX5+yEZi+NTxU5yxCaaakmZtvCAWDXl3icP+El/Y2eN3DiZsNg4XO+SxHQVjOoHo95Bym0dPrfKT997LR7Ocs7OatXHBYDIna5oWPcuRp9JOCQ8s8vUY4uJnYFGpI0lbli4Wo9IWYzYFzs+5a7jMfWtr9G1NUs2hhBjazqhYqLUiuIBmQoUyrZQm9mmSVZ7cn3BFDHMfGRnD/cMBy/UcOz/AaE2wEGzOuBYuHhyyK8o8zyidYMXSCZbMC26BZjoCh7wDHbHnl27+5SIO8LkISLc7/NJ8PrlojDmneqNZ+dsLwBHeXZV4kxmQiKFqGtS0xRZlUJJen2e2dvnk0jGOd0eU4+skfYfDk8wO+ejGGS5NS65vXcUPu4hLMA00QdF8wDVj+DfXrjBcO8GxQYeuOrypiFmLGZiXBRJrLvTXWTp7ngvjkmd3D3l5VjD2kSrLCYkQrGkROwIqFrALQGVrwAqLyd6hhXbZoOS+IasrVq3woRMnOZ8YTmuJO7hKpg1qcxrfehBqhZC05vTU0Da06i0x8QnPXt7mdQN1PyXMDjk3WuV8npMcbtNJ2iGWkzrg8w5TNbxysM+sn1OKxYe2TSyLkjCzUOC6+PdtZCCKGBNjuNjtDr8EyNHWfxQIUnjMXbz45XJ9/ZF/IuL+pmpzSx1Do0TUNYuDmDYuIKDisYvEUPRKYh2VHfFCBV+6Nub4qTXWYwXxgI405NUB0wPHD64tsV9N+NLBPqyewmBoyholIektc1nglw+22DMjfuTYMZbnOb44xGSRgTTY+Rw3vcKSyzjbGXLfiSGvNF1enBdcmu+z5TOmLqUO0jaMsylIssiF6gJY2Y6V78aSbvSsE7iQGC6MutyVp6zEAt0dt8MdBBqToUYgacfBR2vQfMQMw0QtRd5ls468srvLFd+wN+jTLys+nHT4kcxw3O8TdUZtLWMxlPmIYDo8f/2QK/kSVdohrxMywBjPPGmvNUoLhW/NwbcL4moUcUak+ScXL365vHmu8E0ZwC9HgBjD/wvMX7/V7KCK3hSDvhmsqIh5E6dmMIgkVK7hmb0DHljq8anRMsnOIQMF5wJlMWZtkPHp4xtcfe0NXpqOcd0hYyvYbodJOaefj7haV/zOteuEsuTTx4+zYQx2ukcqroVH2QZjI9F7TmQ9Rt0O5/sJ42bApapiu2mY1w3TsqD0SlCDGoOYNqtsLTiNrCU91tMha7lh1QYGviAt90hiQ5JY6hgovVJFaKwj5hlFiGxPSsYEirTLVghc25uyUzdMUNKlHmE653zqeHgw4JhWxPkBNgaaxtCkHWZpjyvTkperkunyBtEkJNoOA1cDzU3P396a9W9jDE3L2zd53XLsLdS2EF9be+RfGON+RtW/pzTxW0iVDEtWlshsi48upfz82eN8TAPdvT2Mtew7x7jTp0kHfH1W86uvvc5VoFk5zpW6AddhhGGpLulNdhn4KedW+/zI8hIPOkeMNWU5BmnIUodvWmvfaIKRHIwlpoZaImUTKAOte6iKD22pu3NtA2mHMCpz0miIpsZLSaMFtVZtNZJY/KKHsMn6bPWXuFp5Lm5u8/p0wsxk+E6fiSiVAKmhEaXjI/fNAx9ZXebc0LI032U4G9PzAbUps8Eq34yO39vd5zUch/1j+PdUvKVexLkY/a9tbz/1s7c0M8gY8/dBf4Y7NC8IABG0jiQ2Y7a8zB8VWyzv7HH36QsYGhJfYZ2S1xO69YxP9JbxJ1b4/MXXuDiGTm+FkDiaUqili+sbSs25XB2yeeUSnxqNuGt9jbVeh85siqsLuk1AQ5tnj7ZErSNWilMhV9MOZl4AQhtdxC/qiKhiInTCDBsDNQ2YtsbAGKEMEa+WJB3iJOPQK1/fLHh+XrFfp5TDc8zTjJmBRgN5InRo0HLCKHh+YGXE2RS0mhKrOcYlQILSpdQer47HvBiU6fIQbZsOvRcyoAuefhu2fPsvoGtrj/zeYmjkHZkcpigdb3GqTLKG4A84VxT82dWT/InBEv3ZPoYCNQUm1jRJh4PBMX5//4Bfe2OT64MNJukKTcyIPmCtx2SB2pYkB1scr2ruX1rhoUGf+5OUk8HTqWZIXdBojbeRaAVDilHXRtEWkPK2PXbbb5MYFuVoijEVVkJbnBKFEMCro0671GmPiaRcG89543DG8z5hWzLqvEu1WPmNBjo20vcFnekuSxJ4ZH2ZHxLo+Bm11jgUFwBNqdMhT45Lfmc+47XVJcZ5Tqc2N2B27+KpBxFrFsMjP03L77cEC76NBnhc4HPRGP47kF99t6f+49cCIWm7cdZBcemQ7Qr+9eY26/1lHu6v0J9cJw8RcZG63icv4KNLI+pwgt+5PuG1UimH6xwkMDcG6wxRFRmeZrcs+Op4yqXpHi93My50Eu4eDFimRzd6pJoTmhoXfTuZW2ihMa3ZRvBxYQgKi3bcNBppVDDRIDFBbEbpcvZsxhtN5PnpIa9XJZM0QTp9Kk0pjKM2gjGGgUK3KlmaH3ImBh4YdHgwSRiUu4TZmFHWxZiUcVDK3pDXvPBkOWMzz2myAV6hbaXxLvP0AIi0vEQXowHe+tfv8K0jLXBHR8cGWVQRqbQBEyJZNef+puEvnD3Dxx3I9CqNGxOdEqKlokeRHOPZceTLO3t8PcLuoM/MWTQqPeMQSUEVJx4XC1w9Y1DPOZNbLnS63JV3OG4cAxV6OiWNc0JUYmgIwbculDlqsrQIsSKIGxAko4qRiRf2Ea4H5bWq5o2gXEUY5xl0umQefBUJ1mJta7Rl8ymD6SEXXODRQY97soSsHINO6IjDhpSisRT9JS7mOV/c2eYVMdRLaxw0rTuaExaQ79ulWxsd+x0MvFYLiOjfAr7wLs7+bclbpTKQVUIWLN7CpNPhG9WcX7v4Ot1zZzm/tMasUqypSWnbu3dnUx7OugzOn4LLb/DNap/DmCM2w5SBSWKZdTJcNCRGyCXFmJxXiwm70xnP65Rll3As73Auy1g2GdYIqRWSrO2vE6JHFTyL2QdAUcFB7dlqaq41NZtE9oxhYh1N0iHanISEWMAsbZCBYGNDrCaYuqTnS84NDB9dHnFSA2a6B6EkOKhsQlWBDJa5JCm/t7vPS8B+t4sRgw2BVON7XnYLHn7b1Q9vG++/8+PjK6c0VhmUQu7beTeV8yTSMDjY4RFn+ckLd3EyT9D9q/Sakh4O00Allml/wPVun9++fJmnt/eZ2S6adLnWH7DbzUl9oNdA1wdy77E+INFTxwpPg3WW1Tpj4B3WRlKzaM1mwBpDiJGA4hfTOKpQMMczNco4MczTFL+Y8WO9kDeWnrcYge28IKSerCrp1HNWfcV9oz4PLg0YlXO684JOXZIbS21TJmVE+yts2x5f3TngBVV2ujllkuJwJHUkN+5GMevt0XseHw8stoHjxx95IEbzNKjlPY4x9CYSbCD1hrxpExi1iUzNnLSj9MZ7fCw4fu7kvTxgFDfbxDmFWKNNjY/CxCQ0Sxu86IWvXNvmpWnB9mBA0elhlUXjCJCwGHvqLEGgxhMUHK2mINYYrZHoEfWYhREYkTZ/oULHOcQItShewBshLPIezgfSGMlNQiKWOlZoPafXzDmbwYNLXc5m7cyDpKnIta2biI1SBkvVH3G50+GL17Z4lYSwepx5gBi0xQwsCj0CcrvTw49CmsGY+LHr1596nu+g/nlnZh5pgY/9HWPS/zLG5j3FBVQiUQIgpN6ShtbgOnQ1k8wzsMratT0+1XT506dOc7ZXMyv2sFLSsxFXNUgjFLbPXv8Yr2c5Xx/PeX7/gP3aUyeOuXUUaUZjUyoEY12bc6jagVal8zQSsUSMeBwR0QAaUGPapI5YRA2mSkhiijGCRCWoJ6JYa1DbTvWoace9nZoGTonh7lGXu3uWVT8jnx2Qh5rEGurgqUWQpEdtl7mo8HvTfZ5PHfudIaVkOG9JQqRjLcYEyqZCzO2Oj1dvTOJirP+Hra2n/+bbrX5459Us8N/IiRO/locQvyZi714ght5lfEBvnNREufH/YJVaA84IeYikhefhUPLjx3ucXu3CdJd0fsCKhU40lGWgkpzYXaZKurxsG75eHXJxb8LlQtm3Q4q0zxyHphmpEYw2RN9gMYi4tip5sVjijRT2UddtwURAIiKGaNoGUmFR9SK+IvWeLHg6EukHz8d7KRe6KcPYMKoLOtUUqWY4J4TUcSi0sw76azxbb/CN3Tlb9Qw/6jE1QhkVa13bBVQEc9QAC3M7kO8oYkQ1vGqtefjatZ8p4W8rbxNJeKfVrPCcuXbtifnGxsf/M+Bft6nidzdUUvTNJmpHN6W0Fb45CeqVRhx1L+fZWcH+66/yKc7yqRNnMNFQTg9JUTrWkZpIUe8Tm0PuSTJO2g67Kz2uNMLzhzWvTufsu4RJU1DZCC5gnSENOSa0WLrG6I3qZjEt1MssWrEaaEexiAcMaVRcUDIf6PmGUd2wYQynOl3W+wlraUmfGc10imlKEmtI+n1mIbBV1ejqKjNneX53zjP1hD1NCGmPECwxeKx9E1MXVRe4hNtiPgs0lxOR/+zatSfmcLflO6j+Gzy5tQO3yYO1tUf+gbXJf/Fut4K3gC3e9qIU0ZLcFwwmUx4Z9PiJ0+c4Uc/pTvdJpKaWmsI21E4ZzXO6RU6Z5UyyDvtpzlXg+YM9NkPDVl1yGEoqjUTXJ9rsBpQKI63hFwNG5cY1WgUbAk4hE6GD0PWeFRHOdDtsOGHDCYPocb6iKQ9Ik0V21ECjwlyFujNg1hlxpQlc3BtztQhsuSE+7xKdUJnWNT4aE2/iostSXGjHWwX7LFR/CM3/tL391F+5OeHz9s/61kjgcXPu3FYyn4+/aoz9yLuJDdyyAIgwCzWSWFajId/f5F4Mj50+zd1dS89PMM0BMY6xLjBqeuRz1zaDcI4mS6iSlDJJOcSwFyL7RcW0brhYN+xHJaDU0VPHgArYJGkbUdECQ2yMbEjKSBK6ScJS6lhKLD0N5LGkoxWJlogvMaFhFNquJ9MQqdKMiUsZp10OswGvzSKvjWv2GkuV5DSpwVuhEaWOAVLbFoeqtuV13K4A3PD5v97tDj958eJ6s0j3vqP7cDsKxgBxY+PhD6smXwVNuU2v4FYFACCIpQye3Dp6gJkcsKqBewcpD41yLnRgWB+SVzOIQgiC4EmMoiHggydiia6DT7p4kxNMRhGVJiohxhsCEERRc1NuXQBV8sSSAi4E0qgkMWBjjQ8lQQs8NcF6rBhW5hnGpxxYpeoPmPaGXGqUFycVF2eBqR0Q8mXqqCgFUULb4NKADy2y2Fn7bjTAkdVfizSf3Nz82rNHvLolntwiPxZ0Yyv4BWPcP7rdbOEtC4CAhth2+AZmdUUnzXBNTTrZ597M8VAv4Z7McDZPSPGEeoZpClwoySWQCISoNOqo1FGREUjpqZIvUDStm6WtCiYiC5Cl0mKlZq4k4ElqcE3E+ohTELuIYQhUBOoYcLIKSZ9xAteD59VZwetlxYHLqfIlKtOlloygioslQgRrwAje+9YwthYTWvvDLky3+I4CcCPb9x9vbz/1v92q6r/pUd8u3RCCv2tt8tdjbI4KSt75ZLehAZAG8HhJ8DZBgyUBOjGSTg4ZlnNOdSxnhj0u5I6zGXQtJH5OnB9gfEViLG0b1pRGUlQSkjDH+apdNoupnEGPSrBbvP3RqvOmIkokCYY0WJw6aAx1I2ia421GI47CWDa7QzZjZGs25WoxYzPUFHmG73QpJSGQEsWBCom+2c3rZvRti9laeEkL5f32WD9tjEmSEJq/t7391N+4XebDuxIApK0l+LJfW/v4r1jrfu5WjcLbEQBvG7xtsMFho8OGBBeFVAza1MSmQMTjTORMLLnHwXq/x3onYdkoA0Lbpr5pZ//G0GIUY1qitobYNk1UVTS249eCafVmWODcOiFgfWzTMdHQREsjKSEbUtqcmSSMm8h+hKfrkq2olBoonRA7KXViqHUBGKWFoUlcgGMWCvrmHpI3kMm39ISOjD7/q9vbT/78gvm30ifuLfRuo3oCyIkTj+Yh6JdE7CduZTu4HQFobCCYiIvS9t6JBhfbLFsQ2uaNRvEmks0PGVRTesayYg3H05TTeYfTnS7DJjKI0EXIEIKfEGLRjmCO2jaNhkUHs6NGzS3A2qoD2hqBwlrm1jC1jl01bDWRrTJwWAcmClvOUiUpLkkIKFX0LQw9sTeMyzeh52/fU/xmDn77z7VqXzX8obXymWvXnig5AjbfJr3rsC5vGoXrqu63Rez97yQEtyMAogYTbTsYgdAiX82idawsmjBGQUM77tWatsmTrRuSqqIXIytOWDbKsdSykiX0U0tfIrm2nQkT2u7loq0ARG2bRHtpm0zPYsY8wsxXHISKsXoONXDQBKZqmEeLmgxNMsoswYuB2CKinU3a64tHwS+9EY8VCTeex5EGONrno7zJyZuF5k26wfwXRPyPbG5+bYvbMPr+2HN+N196k9ow4/Hjj5yL0XxRRO56u24jtyMAqXe44PA2UrpA7QLeekJsG02m0ZIFQxINNVAbaUfYRI+gOInQFFitSKlxsULUM0oSurbNQ2RicKYVJtU2KOQ14rXNwk80pxCHx1Orp44eLyAuoWVzskiRWOZGQQyurb1HAlg1GFk00b458CUe0D8mAAuZfhsBUN9OeNPXjImfvX79qYvvFOp9J3qPAgBv5gs+cjek/0rE3HUnsIRmUZShi4lY8aasWPtg2pI0s9hj2yegN56cCIveY4sqUdrmFWZRtNI2oP0OtGBIEENYCBY3wCJHbuLiKmK79HTxGTn6vh6dQ7710N8RwXsr1r5qfA3qH9va+vqr75X5izu6E9ReSDuF3P2GiHngjgJK3zMtmjYiN9yrt9C3KYRru562KqttnXCb2+uNmPe7ud5vpRvMf17E/9Tm5jOv3wnmwx0TAHhTE3x4A7JfMcZ+6nZcxO8VHbla70Rv9j3+rl/SO11JY0ySxBj+AKqf39p6dvNOMR/uJOqXzwV43G5tPbsp0vyoavhlY5KkTR7dmXXw/2OkoMGYJFENvyzS/OidZj7cUQ1wg25YpGtrj/5dY8xf11YG7giu8L3S7Riit9Bw4btE7bMSscQY/9729hN/Y/GHd23tfyf6bt3ikQEb19Ye/U9E+J9FpPde+xHeqQu7VXp/1NYNS3+myl/e3n7iF1mgs74bl3QHt4C30ML8fsxtbz/xi6rhB1V50pjEtb9/d+3o7tSF3erre3xlEYjGJE6VJ1XDD7bMf2zxzL47l/TdEoAFfdm3QvD0M2nqfkg1/AMRY0SsAW2d4f8/6WLVGxFjVMM/SFP3Q9vbTz/zbmL7t0vfq13uJrvg4z8hIv+jMfaBGD3fa9vgdiTuu/9w2ns3xhFjeF5V/+r29pO/ufjjHd/vvx19lzXADVo0s3/cbm8/+ZuqxSdiDH8HpBJxC9jS+7ctfO+pVfftvUsVY/g7qsUnWuY/ftQE+HvyPN4HO/dNN2Z9/ZGHRex/C/w8QFuHiH43NcL7qwE0ANJugQD8imr4r7e2nvpa+/bOuni3Qu+XoyOLSpUAcOzY9/2UMfpfiZgfAkU1Lhrgy3uqQ/iAkLYrXkTEtB0TNP5ujPLf7+z80W+0H3nc3iqE607T+/1wj1ZCBFhf//ifAflrIvJD7YMKtMaiGL5329WdosW2Jq5t7a6o6u+C/v2trSf/+eIzb7n/94PebwFY0FtXwNraoz8O/Oci/CljbKIaFlqBo1L1D8h1/zHShZo3C2+HGEOjyq8D/8v29hO/tfjcWzTg+0kfsAf5VkHY2Pjoh1TdXwQeF5ELInJUu3+0uo62iPfrPhYhg/ZaRMSItOheVX0F+JyI/8ebm898Y/H5Dwzjj+gDJgBH9LiFzy2CSXD69Pd3vG8+GyOPg/5JEXOqfdCRtpnZjXyD8GbRyp2+t8X+rEcCKm241nDTtVwB+YIxfM655IuXL/9+sfiuWVRcf2AYf0QfUAG4QQYeMzcHQ1ZWPjm01n/aGPlJVf0M6IdEXNJqh1ZmFq3vb5qkdKO47p1gd/rWn2/5vmmnqxmOzqXqG5BviMiXYtTPh+B+b2/vq+M3D/eYWzRk+sC6uB90ATiiheqEb11F6+vfd7eqPgp8CuIjInIv6HERm3xrUl71W/j77U4DLQDkpvetARcakOuq+hKYp4A/EJEntrb+6NW3HuPxhQv7/lj1t0v/rgjAzbQQhi35dmHS1dUfGDhXn1ON96rqvSB3i3AWZENVV4EBaEeE9M14gwZVapACmIjILuimKm+AvioiL4mYl7xPL+7ufmXyxy/pMdc23f53g+k30/8XRlrJLGrwbqoAAAAASUVORK5CYII="


class GFHAccessoriesAutomationGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.configure(bg=APP_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.automator = None
        self.logo_source = None
        self.logo_photo = None
        self.icon_photo = None
        self.store_vars = {}
        self.file_map = {}
        self.store_rows = {}

        set_log_callback(self.enqueue_log)
        set_progress_callback(self.enqueue_progress)

        # ── Copyright bar — packed FIRST so it is ALWAYS visible. If packed
        # after the expanding body (fill=BOTH, expand=True), the body consumes
        # the whole pack cavity and squeezes this bar to zero height. ────────
        _cbar = tk.Frame(self.root, bg="#12142B", height=24)
        _cbar.pack(fill="x", side="bottom")
        _cbar.pack_propagate(False)
        tk.Label(_cbar, text=f"Developed by Abad Umair Channa  |  Copyright © {get_copyright_year()}  |  All rights reserved.",
                 font=("Segoe UI", 8), fg="#8aaccc", bg="#12142B").pack(side="left", padx=14, pady=3)

        self.build_style()
        self.load_logo_source()
        self.theme_manager = ThemeManager("GFH Accessories Ordering")
        self.build_ui()

        load_stores()  # Load stores safely before refreshing the list
        self.refresh_store_list()
        self.refresh_file_table()
        self.update_summary(total=0, processed=0, completed=0, pending=0)

        # Dynamic screen resolution support: size to 90% of the screen and
        # center it (DPI-aware), then stay a normal resizable top-level so
        # Windows Snap (50% left/right, corners, Win+arrow) keeps working.
        self._apply_dynamic_geometry()

        self.root.after(120, self.process_queues)

        apply_theme_to_window(self.root, self.theme_manager)

    def _apply_dynamic_geometry(self) -> None:
        """Size the window to 90% of the screen and center it.

        Works on any laptop/monitor/PC (1080p, 1440p, 2K, 4K) and respects
        Windows DPI scaling (run after _enable_dpi_awareness()). The window
        stays resizable so Windows Snap gestures keep working — it centers
        on launch, then snaps normally to 50% left/right, corners or via
        Win+arrow shortcuts.
        """
        try:
            root = self.root
            root.update_idletasks()
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            w = max(700, min(int(sw * 0.90), sw - 20))
            h = max(480, min(int(sh * 0.90), sh - 40))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            root.geometry("%dx%d+%d+%d" % (w, h, x, y))
            # minsize <= half the screen so 50% / corner snap is never blocked
            root.minsize(min(1180, max(640, sw // 2)),
                         min(720, max(480, sh // 2)))
            root.resizable(True, True)
        except Exception:
            pass

    def _on_mousewheel(self, event):
        """Scrolls the canvas reliably on MouseWheel events"""
        if hasattr(self, "store_canvas"):
            self.store_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def build_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("GFH.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), borderwidth=1)
        style.configure("Red.TButton", font=("Segoe UI", 11, "bold"), padding=(14, 10), foreground=WHITE, background=RED, borderwidth=0)
        style.map("Red.TButton", background=[("active", "#C91524"), ("disabled", "#9CA3AF")])
        style.configure("Dark.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 8), foreground=WHITE, background=NAVY, borderwidth=0)
        style.map("Dark.TButton", background=[("active", "#111A43"), ("disabled", "#9CA3AF")])
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), borderwidth=0)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#EEF1F6", foreground=TEXT)
        style.map("Treeview", background=[("selected", "#DDE8FF")], foreground=[("selected", TEXT)])

    def load_logo_source(self):
        import os
        # PyInstaller onefile extracts bundled data to sys._MEIPASS; the logo
        # ships via --add-data, so check there first, then exe/script dir.
        _candidates = []
        if getattr(sys, "frozen", False):
            _meipass = getattr(sys, "_MEIPASS", None)
            if _meipass:
                _candidates.append(os.path.join(_meipass, "header_logo.png"))
            _candidates.append(os.path.join(os.path.dirname(sys.executable), "header_logo.png"))
        _candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "header_logo.png"))
        self.logo_source = next((p for p in _candidates if os.path.exists(p)), None)
        # Windows needs an AppUserModelID or the taskbar can show a
        # blank/generic icon even when the titlebar icon is set.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "GFHTelecom.AccessoriesOrdering")
        except Exception:
            pass
        try:
            # Use EMBEDDED_ICON_B64 first (self-contained, works in frozen .exe)
            _embedded_ico = _extract_embedded_icon(EMBEDDED_ICON_B64, "app_icon.ico")
            if _embedded_ico:
                self.root.iconbitmap(_embedded_ico)
            else:
                import tempfile as _tf, base64 as _b64
                _ip = _tf.NamedTemporaryFile(delete=False, suffix=".ico")
                _ip.write(_b64.b64decode(GFH_ICON_ICO_B64)); _ip.close()
                self.root.iconbitmap(_ip.name)
        except Exception:
            # Fallback: brand PNG via iconphoto only if the .ico failed —
            # a transparent PNG used with iconphoto(True) can blank the
            # taskbar icon on Windows.
            try:
                self.icon_photo = tk.PhotoImage(data=GFH_SQUARE_ICON_B64)
                self.root.iconphoto(True, self.icon_photo)
            except Exception:
                self.icon_photo = None
    def resized_logo(self, max_width=260, max_height=70):
        if not self.logo_source:
            return None
        try:
            if Image and ImageTk:
                img = Image.open(self.logo_source).convert("RGBA")
                ratio = img.width / max(1, img.height)
                width = min(max_width, int(max_height * ratio))
                height = int(width / ratio)
                if height > max_height:
                    height = max_height
                    width = int(height * ratio)
                img = img.resize((max(1, width), max(1, height)), Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            return tk.PhotoImage(file=self.logo_source)
        except Exception:
            return None

    def build_ui(self):
        self.header = tk.Frame(self.root, bg=NAVY, height=92)
        self.header._tag = "header"
        self.header.pack(side=tk.TOP, fill=tk.X)
        self.header.pack_propagate(False)

        self.logo_label = tk.Label(self.header, bg=NAVY)
        self.logo_label.pack(side=tk.LEFT, padx=(22, 14))
        self.logo_photo = self.resized_logo(260, 70)
        if self.logo_photo:
            self.logo_label.configure(image=self.logo_photo)
        else:
            self.logo_label.configure(text="GFH TELECOM", fg=WHITE, bg=NAVY, font=("Segoe UI", 20, "bold"))

        separator = tk.Frame(self.header, bg="#697089", width=1, height=54)
        separator.pack(side=tk.LEFT, padx=(0, 18))
        tk.Label(self.header, text=APP_TITLE, bg=NAVY, fg=WHITE, font=("Segoe UI", 21, "bold")).pack(side=tk.LEFT)
        self.header.bind("<Configure>", self.on_header_resize)

        body = tk.Frame(self.root, bg=APP_BG)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(body, bg=NAVY_2, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        self.build_sidebar()

        self.main = tk.Frame(body, bg=APP_BG)
        self.main.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=16, pady=16)
        self.build_dashboard()

        theme_btn = create_theme_toggle_button(self.header, self.theme_manager, on_toggle=self._apply_theme)
        theme_btn.pack(side=tk.RIGHT, padx=16)

    def _apply_theme(self, colors=None):
        apply_theme_to_window(self.root, self.theme_manager)

    def on_header_resize(self, event):
        height = max(46, min(72, event.height - 20))
        max_width = 280 if event.width >= 1200 else 220
        new_logo = self.resized_logo(max_width, height)
        if new_logo:
            self.logo_photo = new_logo
            self.logo_label.configure(image=self.logo_photo, text="")

    def build_sidebar(self):
        items = [
            ("Dashboard", True),
            ("Store Selection", False),
            ("Excel Files", False),
            ("Credentials", False),
            ("Run Automation", False),
            ("Logs", False),
        ]
        for label, active in items:
            bg = "#1B244D" if active else NAVY_2
            fg = WHITE
            row = tk.Frame(self.sidebar, bg=bg, height=52)
            row.pack(fill=tk.X, padx=8, pady=(14 if label == "Dashboard" else 3, 0))
            row.pack_propagate(False)
            if active:
                tk.Frame(row, bg=RED, width=4).pack(side=tk.LEFT, fill=tk.Y)
            else:
                tk.Frame(row, bg=bg, width=4).pack(side=tk.LEFT, fill=tk.Y)
            tk.Label(row, text=label, bg=bg, fg=fg, font=("Segoe UI", 11, "bold" if active else "normal"), anchor="w").pack(side=tk.LEFT, padx=14, fill=tk.X, expand=True)

        tk.Frame(self.sidebar, bg="#283052", height=1).pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(0, 84))
        tk.Label(self.sidebar, text="Settings", bg=NAVY_2, fg=WHITE, font=("Segoe UI", 10), anchor="w").pack(side=tk.BOTTOM, fill=tk.X, padx=28, pady=(0, 20))
        tk.Label(self.sidebar, text="About", bg=NAVY_2, fg=WHITE, font=("Segoe UI", 10), anchor="w").pack(side=tk.BOTTOM, fill=tk.X, padx=28, pady=(0, 10))

    def card(self, parent, title):
        frame = tk.Frame(parent, bg=WHITE, highlightbackground="#E6E8EE", highlightthickness=1)
        header = tk.Frame(frame, bg=WHITE)
        header.pack(fill=tk.X, padx=16, pady=(14, 8))
        tk.Label(header, text=title, bg=WHITE, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Frame(header, bg=RED, height=2, width=54).pack(anchor="w", pady=(7, 0))
        content = tk.Frame(frame, bg=WHITE)
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 14))
        return frame, content

    def build_dashboard(self):
        self.main.grid_columnconfigure(0, weight=4)
        self.main.grid_columnconfigure(1, weight=5)
        self.main.grid_columnconfigure(2, weight=4)
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        store_card, store_content = self.card(self.main, "1. Store Selection")
        store_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.build_store_selection(store_content)

        file_card, file_content = self.card(self.main, "2. Excel File Assignment")
        file_card.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=(0, 10))
        self.build_file_assignment(file_content)

        right_top = tk.Frame(self.main, bg=APP_BG)
        right_top.grid(row=0, column=2, sticky="nsew", pady=(0, 10))
        right_top.grid_rowconfigure(0, weight=1)
        right_top.grid_rowconfigure(1, weight=1)
        right_top.grid_columnconfigure(0, weight=1)
        cred_card, cred_content = self.card(right_top, "3. Credentials")
        cred_card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.build_credentials(cred_content)
        controls_card, controls_content = self.card(right_top, "4. Automation Controls")
        controls_card.grid(row=1, column=0, sticky="nsew")
        self.build_controls(controls_content)

        log_card, log_content = self.card(self.main, "5. Live Activity Log")
        log_card.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=(0, 10))
        self.build_log(log_content)

        summary_card, summary_content = self.card(self.main, "6. Order Summary")
        summary_card.grid(row=1, column=2, sticky="nsew")
        self.build_summary(summary_content)

    def build_store_selection(self, parent):
        self.quick_var = tk.StringVar()
        self.quick_var.trace_add("write", lambda *args: self.refresh_store_list())
        entry = tk.Entry(parent, textvariable=self.quick_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1)
        entry.insert(0, "")
        entry.pack(fill=tk.X, ipady=8)
        entry.configure(fg=TEXT)
        tk.Label(parent, text="Quick Input or search store name", bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 4))

        list_outer = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        list_outer.pack(fill=tk.BOTH, expand=True)
        self.store_canvas = tk.Canvas(list_outer, bg=WHITE, highlightthickness=0)
        self.store_scroll = tk.Scrollbar(list_outer, orient="vertical", command=self.store_canvas.yview)
        self.store_frame = tk.Frame(self.store_canvas, bg=WHITE)
        self.store_frame.bind("<Configure>", lambda e: self.store_canvas.configure(scrollregion=self.store_canvas.bbox("all")))
        self.store_canvas.create_window((0, 0), window=self.store_frame, anchor="nw")
        self.store_canvas.configure(yscrollcommand=self.store_scroll.set)
        
        self.store_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.store_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # MOUSE SCROLL BINDINGS
        self.store_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.store_frame.bind("<MouseWheel>", self._on_mousewheel)

        btns = tk.Frame(parent, bg=WHITE)
        btns.pack(fill=tk.X, pady=(10, 0))
        self.selected_count_label = tk.Label(btns, text="0 stores selected", bg=WHITE, fg="#1E4B9B", font=("Segoe UI", 9, "bold"))
        self.selected_count_label.pack(side=tk.LEFT)
        
        tk.Button(btns, text="Manage Stores", command=self.manage_stores_ui, bg=WHITE, fg="#1E4B9B", relief=tk.SOLID, bd=1, padx=10).pack(side=tk.LEFT, padx=(15, 0))
        tk.Button(btns, text="Select All", command=self.select_all_visible, bg=WHITE, fg="#1E4B9B", relief=tk.SOLID, bd=1, padx=10).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(btns, text="Clear All", command=self.clear_all_stores, bg=WHITE, fg=RED, relief=tk.SOLID, bd=1, padx=10).pack(side=tk.RIGHT)

    def manage_stores_ui(self):
        win = tk.Toplevel(self.root)
        win.title("Manage Stores (Add / Edit / Delete)")
        win.geometry("700x450")
        win.attributes("-topmost", True)
        
        columns = ("alias", "address")
        tree = ttk.Treeview(win, columns=columns, show="headings")
        tree.heading("alias", text="Store Alias")
        tree.heading("address", text="Store Address")
        tree.column("alias", width=150)
        tree.column("address", width=500)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def refresh_tree():
            tree.delete(*tree.get_children())
            for alias, addr in sorted(ADDRESSES.items()):
                tree.insert("", tk.END, values=(alias, addr))
                
        refresh_tree()
        
        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def add_store():
            alias = simpledialog.askstring("Add Store", "Enter new Store Alias:", parent=win)
            if not alias: return
            if alias in ADDRESSES:
                messagebox.showerror("Error", "This store alias already exists!", parent=win)
                return
            address = simpledialog.askstring("Add Store", f"Enter Full Address for '{alias}':\n(Format: Street, City, State, USA - Zip)", parent=win)
            if not address: return
            
            ADDRESSES[alias] = address
            save_stores()
            refresh_tree()
            self.refresh_store_list()

        def edit_store():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Edit", "Please select a store to edit.", parent=win)
                return
            old_alias, old_address = tree.item(sel[0], "values")
            
            new_alias = simpledialog.askstring("Edit Store", "Edit Store Alias:", initialvalue=old_alias, parent=win)
            if not new_alias: return
            
            new_address = simpledialog.askstring("Edit Store", "Edit Full Address:", initialvalue=old_address, parent=win)
            if not new_address: return
            
            if new_alias != old_alias:
                del ADDRESSES[old_alias]
                
            ADDRESSES[new_alias] = new_address
            save_stores()
            refresh_tree()
            self.refresh_store_list()
            
        def delete_store():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Delete", "Please select a store to delete.", parent=win)
                return
            alias = tree.item(sel[0], "values")[0]
            if messagebox.askyesno("Confirm", f"Are you sure you want to delete '{alias}'?", parent=win):
                del ADDRESSES[alias]
                save_stores()
                refresh_tree()
                self.refresh_store_list()
                
        tk.Button(btn_frame, text="➕ Add Store", command=add_store, width=15, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="✏️ Edit Store", command=edit_store, width=15, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Store", command=delete_store, width=15, fg="red", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=5)

    def refresh_store_list(self):
        for child in self.store_frame.winfo_children():
            child.destroy()
        query = self.quick_var.get().strip().lower() if hasattr(self, "quick_var") else ""
        visible = []
        if query and "," in query:
            wanted = [p.strip().lower() for p in query.split(",") if p.strip()]
            for alias in ADDRESSES:
                if alias.lower() in wanted:
                    visible.append(alias)
        else:
            for alias in ADDRESSES:
                if not query or query in alias.lower() or query in ADDRESSES[alias].lower():
                    visible.append(alias)
        for alias in visible:
            if alias not in self.store_vars:
                self.store_vars[alias] = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(self.store_frame, text=alias, variable=self.store_vars[alias], bg=WHITE, fg=TEXT, activebackground=WHITE, selectcolor=WHITE, font=("Segoe UI", 10), anchor="w", command=self.on_store_change)
            cb.pack(fill=tk.X, padx=8, pady=2)
            
            # Bind the mouse wheel directly to the checkbutton as well
            cb.bind("<MouseWheel>", self._on_mousewheel)

        self.visible_stores = visible
        self.on_store_change()

    def selected_aliases(self):
        return [alias for alias, var in self.store_vars.items() if var.get()]

    def on_store_change(self):
        count = len(self.selected_aliases())
        self.selected_count_label.configure(text=f"{count} stores selected")
        self.update_summary(total=count, processed=None, completed=None, pending=None)
        self.refresh_file_table()

    def select_all_visible(self):
        for alias in getattr(self, "visible_stores", []):
            self.store_vars.setdefault(alias, tk.BooleanVar(value=False)).set(True)
        self.on_store_change()

    def clear_all_stores(self):
        for var in self.store_vars.values():
            var.set(False)
        self.on_store_change()

    def build_file_assignment(self, parent):
        columns = ("store", "file")
        self.file_tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        self.file_tree.heading("store", text="Store")
        self.file_tree.heading("file", text="Order File")
        self.file_tree.column("store", width=130, anchor="w")
        self.file_tree.column("file", width=320, anchor="w")
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        self.file_tree.bind("<Double-1>", lambda e: self.browse_selected_file())

        tools = tk.Frame(parent, bg=WHITE)
        tools.pack(fill=tk.X, pady=(10, 0))
        self.files_assigned_label = tk.Label(tools, text="0 of 0 files assigned", bg=WHITE, fg="#1E4B9B", font=("Segoe UI", 9, "bold"))
        self.files_assigned_label.pack(side=tk.LEFT)
        tk.Button(tools, text="Browse Selected", command=self.browse_selected_file, bg=WHITE, fg=NAVY, relief=tk.SOLID, bd=1, padx=10).pack(side=tk.RIGHT, padx=(6, 0))
        tk.Button(tools, text="Use One File For All", command=self.browse_one_for_all, bg=WHITE, fg=NAVY, relief=tk.SOLID, bd=1, padx=10).pack(side=tk.RIGHT)

    def refresh_file_table(self):
        if not hasattr(self, "file_tree"):
            return
        self.file_tree.delete(*self.file_tree.get_children())
        selected = self.selected_aliases()
        assigned = 0
        for alias in selected:
            path = self.file_map.get(alias, "")
            if path:
                assigned += 1
            display = os.path.basename(path) if path else "Not assigned"
            iid = self.file_tree.insert("", tk.END, values=(alias, display))
            self.store_rows[iid] = alias
        self.files_assigned_label.configure(text=f"{assigned} of {len(selected)} files assigned")

    def browse_selected_file(self):
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("Select Store", "Select a store row first.")
            return
        alias = self.file_tree.item(selection[0], "values")[0]
        path = filedialog.askopenfilename(
            title=f"Select order file for {alias}",
            filetypes=[
                ("All supported", "*.xlsx *.xls *.csv *.pdf"),
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self.file_map[alias] = path
            self.refresh_file_table()

    def browse_one_for_all(self):
        selected = self.selected_aliases()
        if not selected:
            messagebox.showwarning("No Stores", "Select at least one store first.")
            return
        path = filedialog.askopenfilename(
            title="Select order file for all selected stores",
            filetypes=[
                ("All supported", "*.xlsx *.xls *.csv *.pdf"),
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("PDF files", "*.pdf"),
                ("All files", "*.*"),
            ]
        )
        if path:
            for alias in selected:
                self.file_map[alias] = path
            self.refresh_file_table()

    def build_credentials(self, parent):
        tk.Label(parent, text="Username", bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.username_var = tk.StringVar(value="[REDACTED]")
        tk.Entry(parent, textvariable=self.username_var, font=("Segoe UI", 10), relief=tk.SOLID, bd=1).pack(fill=tk.X, ipady=8, pady=(4, 12))
        tk.Label(parent, text="Password", bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.password_var = tk.StringVar(value="[REDACTED]")
        self.password_entry = tk.Entry(parent, textvariable=self.password_var, show="*", font=("Segoe UI", 10), relief=tk.SOLID, bd=1)
        self.password_entry.pack(fill=tk.X, ipady=8, pady=(4, 8))
        self.show_password_var = tk.BooleanVar(value=False)
        tk.Checkbutton(parent, text="Show Password", variable=self.show_password_var, command=self.toggle_password, bg=WHITE, fg=TEXT, activebackground=WHITE, selectcolor=WHITE, font=("Segoe UI", 9)).pack(anchor="w")

    def toggle_password(self):
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def build_controls(self, parent):
        self.start_btn = ttk.Button(parent, text="▶ Start Automation", command=self.start_automation, style="Red.TButton")
        self.start_btn.pack(fill=tk.X, pady=(2, 8))
        self.stop_btn = ttk.Button(parent, text="■ Stop", command=self.stop_automation, style="Dark.TButton")
        self.stop_btn.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(parent, text="Test Login", command=self.test_login, style="GFH.TButton").pack(fill=tk.X, pady=(0, 8))
        ttk.Button(parent, text="Open Script Folder", command=self.open_script_folder, style="GFH.TButton").pack(fill=tk.X)

    def build_log(self, parent):
        self.log_text = ScrolledText(parent, height=13, bg="#020817", fg="#E5E7EB", insertbackground=WHITE, relief=tk.FLAT, font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        bar = tk.Frame(parent, bg=WHITE)
        bar.pack(fill=tk.X, pady=(10, 0))
        tk.Button(bar, text="Clear Log", command=self.clear_log, bg=WHITE, fg=RED, relief=tk.SOLID, bd=1, padx=10).pack(side=tk.LEFT)
        tk.Button(bar, text="Save Log", command=self.save_log, bg=WHITE, fg="#1E4B9B", relief=tk.SOLID, bd=1, padx=10).pack(side=tk.RIGHT)

    def build_summary(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        self.summary_vars = {
            "total": tk.StringVar(value="0"),
            "processed": tk.StringVar(value="0"),
            "pending": tk.StringVar(value="0"),
            "completed": tk.StringVar(value="0"),
        }
        cards = [
            ("Total Selected", "total", 0, 0),
            ("Processed", "processed", 0, 1),
            ("Pending", "pending", 1, 0),
            ("Completed", "completed", 1, 1),
        ]
        for label, key, r, c in cards:
            frame = tk.Frame(parent, bg="#FAFBFD", highlightbackground="#E6E8EE", highlightthickness=1)
            frame.grid(row=r, column=c, sticky="nsew", padx=(0 if c == 0 else 8, 0), pady=(0 if r == 0 else 8, 8))
            tk.Label(frame, text=label, bg="#FAFBFD", fg=TEXT, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(10, 0))
            tk.Label(frame, textvariable=self.summary_vars[key], bg="#FAFBFD", fg="#1E4B9B", font=("Segoe UI", 21, "bold")).pack(anchor="w", padx=12, pady=(3, 8))
        tk.Label(parent, text="Overall Progress", bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w", pady=(6, 2))
        self.percent_label = tk.Label(parent, text="0%", bg=WHITE, fg=TEXT, font=("Segoe UI", 9, "bold"))
        self.percent_label.grid(row=2, column=1, sticky="e", pady=(6, 2))
        self.progress = ttk.Progressbar(parent, maximum=100)
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew")

    def update_summary(self, total=None, processed=None, pending=None, completed=None):
        current_total = int(self.summary_vars.get("total", tk.StringVar(value="0")).get()) if hasattr(self, "summary_vars") else 0
        current_processed = int(self.summary_vars.get("processed", tk.StringVar(value="0")).get()) if hasattr(self, "summary_vars") else 0
        current_completed = int(self.summary_vars.get("completed", tk.StringVar(value="0")).get()) if hasattr(self, "summary_vars") else 0
        if total is None:
            total = current_total
        if processed is None:
            processed = current_processed
        if completed is None:
            completed = current_completed
        if pending is None:
            pending = max(0, total - processed)
        if hasattr(self, "summary_vars"):
            self.summary_vars["total"].set(str(total))
            self.summary_vars["processed"].set(str(processed))
            self.summary_vars["pending"].set(str(pending))
            self.summary_vars["completed"].set(str(completed))
        percent = int((processed / total) * 100) if total else 0
        if hasattr(self, "progress"):
            self.progress["value"] = percent
            self.percent_label.configure(text=f"{percent}%")

    def enqueue_log(self, line):
        self.log_queue.put(line)

    def enqueue_progress(self, payload):
        self.progress_queue.put(payload)

    def process_queues(self):
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            self.write_log(line)
        while not self.progress_queue.empty():
            payload = self.progress_queue.get_nowait()
            self.update_summary(
                total=payload.get("total"),
                processed=payload.get("processed"),
                pending=payload.get("pending"),
                completed=payload.get("completed"),
            )
        self.root.after(120, self.process_queues)

    def write_log(self, line):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, line + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def save_log(self):
        path = filedialog.asksaveasfilename(title="Save automation log", defaultextension=".txt", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", tk.END))
        messagebox.showinfo("Saved", f"Log saved:\n{path}")

    def open_script_folder(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        try:
            os.startfile(folder)
        except Exception:
            webbrowser.open(Path(folder).as_uri())

    def build_selected_stores(self):
        selected = self.selected_aliases()
        stores = []
        for alias in selected:
            stores.append({
                "alias": alias,
                "address": ADDRESSES[alias],
                "excel_path": self.file_map.get(alias, ""),
            })
        return stores

    def validate_before_run(self, stores):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Already Running", "Automation is already running.")
            return False
        if not stores:
            messagebox.showwarning("No Store Selected", "Select at least one store.")
            return False
        missing = [s["alias"] for s in stores if not s.get("excel_path")]
        if missing:
            messagebox.showwarning("Missing Files", "Assign an Excel order file for:\n" + "\n".join(missing))
            return False
        if not self.username_var.get().strip() or not self.password_var.get().strip():
            messagebox.showwarning("Credentials Required", "Enter username and password.")
            return False
        return True

    def start_automation(self):
        stores = self.build_selected_stores()
        if not self.validate_before_run(stores):
            return
        self.stop_event.clear()
        self.start_btn.state(["disabled"])
        self.clear_log()
        self.update_summary(total=len(stores), processed=0, completed=0, pending=len(stores))
        self.worker_thread = threading.Thread(target=self.automation_worker, args=(stores,), daemon=True)
        self.worker_thread.start()

    def automation_worker(self, stores):
        try:
            self.automator = CPWHOrderAutomator(
                username=self.username_var.get().strip(),
                password=self.password_var.get().strip(),
                stop_event=self.stop_event,
            )
            self.automator.run(stores)
            log("Browser will remain open until you stop automation or close the app.")
        except Exception:
            log("❌ Automation crashed:")
            log(traceback.format_exc())
        finally:
            self.root.after(0, lambda: self.start_btn.state(["!disabled"]))

    def stop_automation(self):
        self.stop_event.set()
        log("🛑 Stop requested by user.")
        if self.automator:
            try:
                self.automator.close(ask=False)
                log("Browser closed.")
            except Exception as exc:
                log(f"Browser close failed: {exc}")

    def test_login(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showwarning("Already Running", "Stop the current automation before testing login.")
            return
        if not self.username_var.get().strip() or not self.password_var.get().strip():
            messagebox.showwarning("Credentials Required", "Enter username and password.")
            return
        self.stop_event.clear()
        self.start_btn.state(["disabled"])
        threading.Thread(target=self.test_login_worker, daemon=True).start()

    def test_login_worker(self):
        tester = None
        try:
            tester = CPWHOrderAutomator(username=self.username_var.get().strip(), password=self.password_var.get().strip(), stop_event=self.stop_event)
            if tester.login():
                log("✅ Test login passed.")
            else:
                log("❌ Test login failed.")
        except Exception:
            log("❌ Test login crashed:")
            log(traceback.format_exc())
        finally:
            if tester:
                tester.close(ask=False)
            self.root.after(0, lambda: self.start_btn.state(["!disabled"]))

    def on_close(self):
        self.stop_event.set()
        set_log_callback(None)
        set_progress_callback(None)
        if self.automator:
            try:
                self.automator.close(ask=False)
            except Exception:
                pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()

def _enable_dpi_awareness() -> None:
    """Make Windows report physical pixels so winfo_screen* is accurate on
    high-DPI displays (1080p, 1440p, 2K, 4K, DPI-scaled laptops)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system DPI aware
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    _enable_dpi_awareness()
    try:
        app = GFHAccessoriesAutomationGUI()
        app.run()
    except Exception:
        traceback.print_exc()
        try:
            messagebox.showerror("GFH Accessories Ordering — Error",
                                 "The app hit an error during startup.\n\n"
                                 + traceback.format_exc())
        except Exception:
            pass
        if sys.stdin and sys.stdin.isatty():
            input("\nPress Enter to close...")