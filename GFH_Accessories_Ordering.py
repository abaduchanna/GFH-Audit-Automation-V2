# Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved. Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.
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
APP_BG = "#f6f7fb"
NAVY = "#090d26"        # matches theme_manager.py navy — header blends with logo
EMBEDDED_LOGO_B64 = "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O3rtmg3FUu2Sj13u+8Gbbz79yMPPnn7m2Z+47NM/+OHV73/fBxYsXjh3zqyZf1tw+ac/k05nq9Xek6cfd9NNN2zYsDWO65MnT7z+hz/9znXXXnD+R3/ykx+sWLGC2U2cMPErX7n6plt+/NCDT0w7/NBjjj3lzbmv/eB73zvttBn77LPfzJmv7DFi5JFHnrxs5bzvXvu9Y4457AMfOOmN2a+mM5nVq9Y3N+evuurbL7380gP33zNy1PAlSxYfeOCBTzzx9Isv/O3CCy9oa2vLZjMbNmx88MHHa1H129/+6quvvtHW1vzoY0/8+pZbX3nluQ0bNpdK5XETRt11131fvvJazw95W3Zuar/6xQ1HHvm+RYsWH3f8Md+46juT99133333Hjd29MaNmyuV6heuuHLZ0qWrVy9evnz5oYceefxx0++66zenn3HeX5566OEHH0mFLaecei55Cojieu+0ww56+ukH7r//kQs+/EnrzPeu/c4JJxxz+LQTGcy5Hzz72mu/Om7C5Ft/84uTTznxzTfmDeoYcuut9/zXj34cpryn//LggQfuN3nKESuWLd97n73/+uxjGzatLRVLk/bZ5557HvzSlVcJBszgxP5j2jTeIdAXBw4dOJ16ujs+JKcPzTSnap1BcePhzcOX17KPVBMIUizSE+buKHRXJTW9dVA+6c3ZClU3j/XDYW1NU9pbl9fMothsMraccCwoqABFo2QJ9vCCvUM1HuMOqahyve6SovIkCCtWCpZ6vLZ1jlbWojUuMaBOzqYPwpqf9JR8rzvXurJo54mfiKfjpL49ydqlanTqgVOOPe7Iww8/5o03Xrn88itqEZ17/r8NHzbu+ece/tznvv7iK3+zpnLN1Vdt2rRln0nj99v34F/e9Ivzzjvr3z97yTPPvtDe1vGNq7+lPe3Y5bLB9df/x1NPP3vhhZ9nNlde8e+XXnrhnx+495pvf+nue+7+9Ke/ACjf/+73vv/9/3j0sYcKhc58U/DD668+/rhjo3ohSWqkoVDo3n//va/9zpc/dN55xhSieiVJqs7Zq6665re/+xWpPLvKT37yozFjRx191MlLl8899JCj7r33d08++fzhRx1/zTe+cvChB08/+Wx28TXf/NZLL7563PEfECAiGjd+ggh/8lNfevW1V089+aR77r55/psrf3vn70mHjf6RYUOGn3nmKR+5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QWeQvX3zxtbBg4/IDy5b1i6ewPaiIYPyhcrD1XLZCz0g4+VKPsw0tUWFaFyJx2l/ZBCO9lJ5MEoJaREQB+IErXgFQ2uT+krhFa62jlVVpSEgQCYgsuV2W3tfS3hYgC21rTEZdmHk52bG9HgSd6UylDh4tyo0UKRLvYWzzznzpJOPXrly1fvff9jXv34tkaeUn07nBLijffgHzzr9k5+68u57fu978sILL1522WWvvPpUW2tHPt8srIDBitGeVyoXv/DFr//m1zdO3f+Q3kJh6gH7/Of1P1m48PWrr77uxht/eNTRh4LQPpMmf+XKqzdsWNna0rF+w2ZU4Te+8d1jjz2qtbUDRTfnWzyVRvK/dfX10086rq21XZGPoK699ppLL724paXlG9/87jXf/o8jph3ywl8fW7R40X77TVkwf+GDDz3AzqD2giCFAETaOjnyyMOffebZ1taWv/zl+Ztu/k0Y+jffdEN3T+d++069+eY77rzz7scff+z11+d86cqvh6mWQm/hmGOOPefcM19/ffYRR0674b9uATRIXi7T5PuhVv6ll158ww23fP+H3yPy/vSHOy679GP33X9XJtOUzWQRtXVWexRFlTFjJp5yysmXXnLZfX++N/TTb7w586Mf/XAcxW2trZnUUEZubm7P5Zp8P8uOPn7pJQcecNDQoUO+d91PTjt1+mszZ5986ukC+OUrrvz3f7/soYced1Z+8YsbCr3dkyfve+cd999x1x9SqWa3fd/s967s2WmNUgg0IwKUNK0ud2cy2Y50G1XroXEZW9+zNdOuMSmWbCLFlA8InnUag6rVy2L7WhzPrXpvVPzX6vRmpF+P9MyafrXm/a3GL9fqrzhZIGorehZUM3spUYZsJilPpNoH2lOT05KOyppNLF5PpnmmU49Walv9FAqC8LuvIintdXVtue++B4U5qsU/uuGmP9//aBDmTWJXrVg7a/Yb2g+WL1v54MNPaZ21lufPW9HTXV28eE1Pb8+bb8xbtWa99NdLiPTihYseffRxZ6izs/Oab33vrrvvyzcNm/na7KeefF6RWr589bevvv6Bhx8O0oPWrdn85psL1m/YWqlFM1+d/frsBUuXrdm4fsvM1+Z0dld6CoWZf5v9xux5K1asWb9u8/x5ixYtWjLnzQVvzFm6bt3m++57tKerJ47dXXfc+61rvl+rMaqwVCrO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"
EMBEDDED_ICON_B64 = "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"

NAVY_2 = "#050817"
RED = "#f0541c"
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
GFH_SQUARE_ICON_B64 = "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"


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

        # ── Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved. If packed
        # after the expanding body (fill=BOTH, expand=True), the body consumes
        # the whole pack cavity and squeezes this bar to zero height. ────────
        _cbar = tk.Frame(self.root, bg="#090d26", height=24)
        _cbar.pack(fill="x", side="bottom")
        _cbar.pack_propagate(False)
        tk.Label(_cbar, text=f"Developed by Abad Umair Channa | Copyright © 2026 | All rights reserved.",
                 font=("Segoe UI", 8), fg="#9d9db8", bg="#090d26").pack(side="left", padx=14, pady=3)

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

        style.map("Treeview.Heading")
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
        # Try _MEIPASS first (PyInstaller onefile extraction dir)
        import sys as _sys, os as _os
        _meipass = getattr(_sys, "_MEIPASS", None)
        if _meipass:
            for _ico_name in ("gfh_icon_white.ico", "gfh_telecom_llc_icon.ico", "icon.ico"):
                _ico_path = _os.path.join(_meipass, _ico_name)
                if _os.path.exists(_ico_path):
                    try:
                        self.root.iconbitmap(_ico_path)
                    except Exception:
                        pass
                    break
        # Fallback: decode EMBEDDED_ICON_B64 to %TEMP%
        try:
            import base64 as _b64, tempfile as _tf
            _data = _b64.b64decode(EMBEDDED_ICON_B64.strip())
            _tmp_dir = _os.environ.get("TEMP", _tf.gettempdir())
            _ico_path = _os.path.join(_tmp_dir, "gfh_app_icon.ico")
            with open(_ico_path, "wb") as _f:
                _f.write(_data)
            self.root.iconbitmap(_ico_path)
        except Exception:
            pass
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
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GFHTelecom.App")
        except Exception:
            pass
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