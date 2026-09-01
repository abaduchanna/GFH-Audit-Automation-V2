# OCR IMEI Extraction & Matching Module

## Overview

**Tesseract OCR integration** for automated IMEI extraction from variance audit images and intelligent matching against the database.

### Key Features

✅ **Tesseract OCR** - Automatic text extraction from images  
✅ **IMEI Detection** - Finds 15-digit IMEI patterns  
✅ **Fuzzy Matching** - Handles OCR errors (handles misread characters)  
✅ **Luhn Validation** - Ensures extracted IMEIs are valid  
✅ **Batch Processing** - Process entire folders of images  
✅ **Database Matching** - Automatic variance record updates  
✅ **Comprehensive Reporting** - JSON reports with detailed results  

---

## Installation

### 1. Install Python Packages

```bash
pip install pytesseract pillow opencv-python
```

### 2. Install Tesseract OCR

#### Windows
```bash
# Download installer from:
# https://github.com/UB-Mannheim/tesseract/wiki

# Or use Chocolatey:
choco install tesseract

# Or use Windows Package Manager:
winget install UB-Mannheim.Tesseract
```

After installation, verify:
```bash
tesseract --version
```

#### Linux
```bash
sudo apt-get install tesseract-ocr
```

#### macOS
```bash
brew install tesseract
```

### 3. Update requirements.txt

```
pytesseract>=0.3.10
pillow>=9.0.0
opencv-python>=4.6.0
difflib-fuzzy>=0.0.1
numpy>=1.21.0
```

---

## Quick Start

### Extract IMEIs from a Single Image

```python
from ocr_imei_processor import IMEIExtractor

# Initialize
extractor = IMEIExtractor()

# Extract IMEIs
imeis = extractor.extract_from_image("variance_image.jpg")
print(f"Found IMEIs: {imeis}")
# Output: ['123456789012345', '987654321098765']
```

### Match IMEIs Against Database

```python
from ocr_imei_processor import VarianceImageProcessor
from database_manager import DatabaseManager

# Initialize
db = DatabaseManager()
processor = VarianceImageProcessor(db)

# Process single image
result = processor.process_single_image("variance_image.jpg")

print(f"Extracted: {len(result['extracted_imeis'])} IMEIs")
print(f"Matched: {len(result['matched_records'])} records")
print(f"Unmatched: {len(result['unmatched_imeis'])} IMEIs")
```

### Batch Process Folder of Images

```python
from ocr_imei_processor import VarianceImageProcessor
from database_manager import DatabaseManager

# Initialize
db = DatabaseManager()
processor = VarianceImageProcessor(db)

# Process all images in folder
report = processor.process_variance_images("C:\\variance_images\\")

print(f"Total images: {report['total_images_processed']}")
print(f"Success rate: {report['match_success_rate']}%")

# Save report
processor.export_report("ocr_report.json")
```

---

## Tab 2 Integration

### Variance Audit Panel with OCR

The OCR module is integrated into **Tab 2: Variance Audit** via `variance_image_panel.py`:

#### Features in UI

**Batch Processing:**
- Select folder with variance images
- Process all images automatically
- Shows results in 4 tabs:
  - Extracted IMEIs
  - Matched Records
  - Unmatched IMEIs
  - Report Summary

**Single Image Processing:**
- Select individual image
- Extract and match IMEIs
- Preview image in default viewer
- Real-time progress display

**Results Tabs:**
1. **Extracted IMEIs** - All IMEIs found in images
2. **Matched Records** - IMEIs matched to variance database
3. **Unmatched IMEIs** - IMEIs not in database
4. **Report Summary** - Statistics and analysis

**Database Updates:**
- Mark matched as "Cleared"
- Auto-update variance status
- Add unmatched to new variance records

---

## Workflow Example

### Scenario: Process Daily Variance Audit Images

```
1. Upload variance images to: C:\audit_images\
   ├─ store_arizona_001.jpg
   ├─ store_arizona_002.jpg
   ├─ store_colorado_001.jpg
   └─ store_colorado_002.jpg

2. Open app → Tab 2: Variance Audit

3. Click "Select Folder" → Choose C:\audit_images\

4. Click "Process All Images in Folder"
   ↓
   System processes each image:
   - Extracts IMEIs using Tesseract OCR
   - Matches against variance database
   - Displays results

5. Tab: "Extracted IMEIs"
   Shows all 15 IMEIs found across images

6. Tab: "Matched Records"
   Shows which IMEIs matched variance records
   Columns: Image | IMEI | Match Type | Confidence | Store | Status

7. Tab: "Unmatched IMEIs"
   Shows IMEIs not in variance database
   Option: "Add as New Variance"

8. Click "Mark All as Cleared" → Updates database

9. Click "Export Report" → Saves JSON with all details
```

---

## Image Preprocessing

The OCR module automatically improves image quality:

1. **Grayscale Conversion** - Removes color artifacts
2. **CLAHE Enhancement** - Improves contrast
3. **Binary Thresholding** - Separates text from background
4. **Denoising** - Removes image noise
5. **Auto-Resize** - Scales small images for better OCR

Result: **Higher accuracy** even with low-quality images

---

## Matching Algorithms

### Exact Matching
```
Database IMEI: 123456789012345
Extracted IMEI: 123456789012345
Result: EXACT MATCH (100% confidence)
```

### Fuzzy Matching (Handles OCR Errors)
```
Database IMEI: 123456789012345
Extracted IMEI: 123456789012346  (OCR misread last digit)
Similarity: 93.3%
Result: FUZZY MATCH (93% confidence)
```

### Luhn Validation
All extracted IMEIs are validated using Luhn algorithm to ensure they're valid formats.

---

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Single image OCR | 2-5 sec | Depends on image quality |
| Database matching | <1 sec | Per IMEI |
| Batch process 10 images | 30-60 sec | With OCR + matching |
| Export report | <1 sec | JSON generation |

---

## Database Updates

### Automatic Updates When Matched

When an extracted IMEI matches a variance record:

```sql
UPDATE variance_data 
SET status = 'MATCHED_FROM_IMAGE',
    clearance = 'Matched: [IMEI] from [Image]',
    updated_at = CURRENT_TIMESTAMP
WHERE imei = ?
```

### Manual Updates Available

- **Mark as Cleared** - Set status to CLEARED
- **Update Clearance Note** - Add comment/reason
- **Remove from Variance** - Delete record
- **Add New Variance** - From unmatched IMEIs

---

## Report Format (JSON)

```json
{
  "timestamp": "2026-08-31T18:30:00",
  "total_images_processed": 4,
  "total_imeis_extracted": 15,
  "total_imeis_matched": 12,
  "total_imeis_unmatched": 3,
  "match_success_rate": 80.0,
  "detailed_results": [
    {
      "image": "variance_001.jpg",
      "extracted_imeis": ["123456789012345", "987654321098765"],
      "matched_records": [
        {
          "imei": "123456789012345",
          "database_imei": "123456789012345",
          "match_type": "EXACT",
          "confidence": 100,
          "record": {
            "store": "Phoenix Store",
            "status": "Pending"
          }
        }
      ],
      "unmatched_imeis": ["555555555555555"],
      "status": "PARTIAL_MATCH"
    }
  ]
}
```

---

## Troubleshooting

### Issue: "No module named pytesseract"
**Solution:** `pip install pytesseract`

### Issue: "Tesseract is not installed"
**Solution:** Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki

### Issue: "Low OCR accuracy"
**Solutions:**
- Ensure images are well-lit and sharp
- High resolution (>300 DPI)
- Crop images to focus on IMEI area
- Module automatically preprocesses images

### Issue: "Fuzzy matching too aggressive"
**Solution:** Adjust threshold in `IMEIMatcher._find_fuzzy_match()` (default: 0.85 = 85%)

### Issue: "Database not updating"
**Solution:** Ensure variance table has `id` column for updates

---

## Integration with v2 Audit Control Panel

The OCR module works seamlessly with v2 features:

- **During Audit Workflow**: Automatically extract IMEIs from variance images
- **Real-time Updates**: Match results update inventory status
- **15-min Polling**: Can include OCR processing
- **WhatsApp Reports**: Include OCR matching results in status messages

---

## Files Included

```
ocr_imei_processor.py (400+ lines)
├── IMEIExtractor class
│   ├── extract_from_image()
│   ├── extract_batch()
│   └── _preprocess_image()
│
├── IMEIMatcher class
│   ├── match_image_imeis()
│   ├── update_variance_status()
│   └── process_batch()
│
└── VarianceImageProcessor class
    ├── process_variance_images()
    └── export_report()

variance_image_panel.py (600+ lines)
├── VarianceImageProcessingPanel class
├── Batch processing UI
├── Single image processing UI
└── 4 result display tabs
```

---

## Next Steps

1. Install Tesseract OCR
2. Run: `pip install -r requirements.txt`
3. Open app → Tab 2: Variance Audit
4. Upload variance images
5. Click "Process All Images in Folder"
6. Review matched/unmatched results
7. Update database automatically

---

## Support

- **Email**: abad@gfh.pk
- **GitHub**: github.com/abaduchanna
- **Issues**: Check Tesseract installation first

---

**Version**: 1.0  
**Status**: Production Ready  
**Last Updated**: August 31, 2026
