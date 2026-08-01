# GFH Telecom Automation

GFH Telecom automation suite - Inventory Audit and Accessories Ordering.

## Files
- GFH_Inventory_Audit.py - Inventory audit automation
- GFH_Accessories_Ordering.py - Accessories ordering automation
- gfh_telecom_llc_icon.ico - Application icon (embedded in .exe for taskbar/titlebar/Windows Explorer)

## Build
GitHub Actions automatically builds Windows .exe files on every push to main.
The icon is embedded via PyInstaller --icon flag so it appears in:
- Windows Taskbar
- Window Title Bar
- Windows Explorer
