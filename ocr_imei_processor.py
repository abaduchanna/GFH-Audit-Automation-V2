"""
Tesseract OCR Module for IMEI Extraction and Matching
Extracts IMEIs from variance audit images and matches against database
Features:
- Image preprocessing for OCR accuracy
- IMEI detection and validation
- Batch processing multiple images
- Fuzzy matching for OCR errors
- Database matching and status updates
"""

import pytesseract
from PIL import Image
import cv2
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class IMEIExtractor:
    """Extracts IMEIs from images using Tesseract OCR"""
    
    # IMEI pattern: 15 digits
    IMEI_PATTERN = r'\b\d{15}\b'
    # Alternative patterns for incomplete or partially visible IMEIs
    PARTIAL_IMEI_PATTERN = r'\d{10,15}'
    
    def __init__(self, tesseract_path=None):
        """
        Initialize IMEI extractor
        
        Args:
            tesseract_path: Path to Tesseract executable (Windows)
                          Optional if Tesseract is in PATH
        """
        if tesseract_path:
            pytesseract.pytesseract.pytesseract_cmd = tesseract_path
    
    def extract_from_image(self, image_path: str) -> List[str]:
        """
        Extract all IMEIs from an image
        
        Args:
            image_path: Path to image file
            
        Returns:
            List of valid IMEIs found
        """
        try:
            # Preprocess image for better OCR
            processed_image = self._preprocess_image(image_path)
            
            # Extract text using Tesseract
            extracted_text = pytesseract.image_to_string(processed_image)
            
            # Find all IMEIs in extracted text
            imeis = self._extract_imeis_from_text(extracted_text)
            
            return imeis
        
        except Exception as e:
            print(f"Error extracting IMEI from {image_path}: {str(e)}")
            return []
    
    def _preprocess_image(self, image_path: str) -> Image.Image:
        """
        Preprocess image for improved OCR accuracy
        
        Steps:
        1. Read image with OpenCV
        2. Convert to grayscale
        3. Apply thresholding
        4. Denoise
        5. Resize if needed
        """
        # Read image
        img = cv2.imread(image_path)
        
        if img is None:
            raise ValueError(f"Cannot read image: {image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Apply binary thresholding
        _, binary = cv2.threshold(enhanced, 127, 255, cv2.THRESH_BINARY)
        
        # Denoise
        denoised = cv2.fastNlMearsDenoising(binary, h=10)
        
        # Resize if too small (helps OCR)
        height, width = denoised.shape
        if width < 300 or height < 100:
            scale_factor = max(300 / width, 100 / height)
            denoised = cv2.resize(
                denoised,
                None,
                fx=scale_factor,
                fy=scale_factor,
                interpolation=cv2.INTER_CUBIC
            )
        
        # Convert back to PIL Image
        return Image.fromarray(denoised)
    
    def _extract_imeis_from_text(self, text: str) -> List[str]:
        """
        Extract valid IMEIs from OCR text
        
        Args:
            text: Text extracted from image
            
        Returns:
            List of valid 15-digit IMEIs
        """
        imeis = []
        
        # Find all 15-digit sequences
        matches = re.findall(self.IMEI_PATTERN, text)
        imeis.extend(matches)
        
        # Also look for partial patterns and clean them
        partial_matches = re.findall(self.PARTIAL_IMEI_PATTERN, text)
        for match in partial_matches:
            if len(match) == 15 and match not in imeis:
                imeis.append(match)
        
        # Remove duplicates and validate
        valid_imeis = list(set([imei for imei in imeis if self._validate_imei(imei)]))
        
        return valid_imeis
    
    def _validate_imei(self, imei: str) -> bool:
        """
        Validate IMEI using Luhn algorithm
        
        Args:
            imei: IMEI string
            
        Returns:
            True if valid IMEI
        """
        if not re.match(r'^\d{15}$', imei):
            return False
        
        # Luhn algorithm check
        def luhn_check(n):
            digits = [int(d) for d in str(n)]
            digits.reverse()
            total = 0
            for i, d in enumerate(digits):
                if i % 2 == 1:
                    d = d * 2
                    if d > 9:
                        d = d - 9
                total += d
            return total % 10 == 0
        
        return luhn_check(imei)
    
    def extract_batch(self, image_folder: str) -> Dict[str, List[str]]:
        """
        Extract IMEIs from all images in a folder
        
        Args:
            image_folder: Path to folder containing images
            
        Returns:
            Dict mapping image filename to list of IMEIs
        """
        results = {}
        image_paths = []
        
        # Find all image files
        for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            image_paths.extend(Path(image_folder).glob(f'*{ext}'))
            image_paths.extend(Path(image_folder).glob(f'*{ext.upper()}'))
        
        # Process images in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_path = {
                executor.submit(self.extract_from_image, str(path)): path
                for path in image_paths
            }
            
            for future in future_to_path:
                path = future_to_path[future]
                try:
                    imeis = future.result()
                    results[path.name] = imeis
                except Exception as e:
                    print(f"Error processing {path}: {str(e)}")
                    results[path.name] = []
        
        return results


class IMEIMatcher:
    """Matches extracted IMEIs against database variance records"""
    
    def __init__(self, db_manager):
        """
        Initialize IMEI matcher
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db_manager = db_manager
        self.extraction_report = []
        self.match_report = []
    
    def match_image_imeis(self, extracted_imeis: List[str], image_name: str) -> Dict:
        """
        Match extracted IMEIs against variance database
        
        Args:
            extracted_imeis: List of IMEIs from image
            image_name: Name of image file
            
        Returns:
            Dict with matches and status
        """
        matches = {
            "image": image_name,
            "extracted_imeis": extracted_imeis,
            "matched_records": [],
            "unmatched_imeis": [],
            "timestamp": datetime.now().isoformat()
        }
        
        if not extracted_imeis:
            matches["status"] = "NO_IMEI_FOUND"
            return matches
        
        # Get all variance records from database
        variance_records = self._get_variance_records()
        
        for imei in extracted_imeis:
            found = False
            
            # Look for exact match
            for record in variance_records:
                if record.get("imei") == imei:
                    matches["matched_records"].append({
                        "imei": imei,
                        "record": record,
                        "match_type": "EXACT",
                        "confidence": 100
                    })
                    found = True
                    break
            
            # Look for fuzzy match if no exact match
            if not found:
                fuzzy_match = self._find_fuzzy_match(imei, variance_records)
                if fuzzy_match:
                    matches["matched_records"].append(fuzzy_match)
                    found = True
            
            # Track unmatched
            if not found:
                matches["unmatched_imeis"].append(imei)
        
        # Set status
        if matches["matched_records"] and not matches["unmatched_imeis"]:
            matches["status"] = "ALL_MATCHED"
        elif matches["matched_records"]:
            matches["status"] = "PARTIAL_MATCH"
        else:
            matches["status"] = "NO_MATCH"
        
        self.match_report.append(matches)
        return matches
    
    def _get_variance_records(self) -> List[Dict]:
        """Get all variance records from database"""
        try:
            conn = self.db_manager.db_path
            import sqlite3
            conn = sqlite3.connect(conn)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM variance_data")
            records = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return records
        except Exception as e:
            print(f"Error getting variance records: {str(e)}")
            return []
    
    def _find_fuzzy_match(self, imei: str, records: List[Dict], threshold=0.85) -> Optional[Dict]:
        """
        Find fuzzy match for IMEI (handles OCR errors)
        
        Args:
            imei: IMEI from image
            records: List of variance records
            threshold: Match confidence threshold (0-1)
            
        Returns:
            Fuzzy match result or None
        """
        best_match = None
        best_score = 0
        
        for record in records:
            db_imei = record.get("imei", "")
            if not db_imei:
                continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, imei, db_imei).ratio()
            
            if similarity >= threshold and similarity > best_score:
                best_match = {
                    "imei": imei,
                    "database_imei": db_imei,
                    "record": record,
                    "match_type": "FUZZY",
                    "confidence": int(similarity * 100)
                }
                best_score = similarity
        
        return best_match
    
    def update_variance_status(self, matched_record: Dict, status: str, clearance: str = "") -> bool:
        """
        Update variance record with matched status
        
        Args:
            matched_record: Matched variance record
            status: New status (e.g., "MATCHED_FROM_IMAGE")
            clearance: Optional clearance note
            
        Returns:
            True if update successful
        """
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE variance_data 
                SET status = ?, 
                    clearance = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, clearance, matched_record.get("id")))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating variance record: {str(e)}")
            return False
    
    def process_batch(self, extracted_batch: Dict[str, List[str]]) -> List[Dict]:
        """
        Process batch of extracted IMEIs from multiple images
        
        Args:
            extracted_batch: Dict mapping image names to IMEI lists
            
        Returns:
            List of match results
        """
        all_matches = []
        
        for image_name, imeis in extracted_batch.items():
            match_result = self.match_image_imeis(imeis, image_name)
            all_matches.append(match_result)
            
            # Auto-update database for matched records
            for matched in match_result.get("matched_records", []):
                self.update_variance_status(
                    matched.get("record", {}),
                    "MATCHED_FROM_IMAGE",
                    f"Matched from image: {image_name}"
                )
        
        return all_matches
    
    def get_match_report(self) -> Dict:
        """Generate comprehensive matching report"""
        total_images = len(self.match_report)
        total_extracted = sum(len(r.get("extracted_imeis", [])) for r in self.match_report)
        total_matched = sum(len(r.get("matched_records", [])) for r in self.match_report)
        total_unmatched = sum(len(r.get("unmatched_imeis", [])) for r in self.match_report)
        
        match_rate = (total_matched / total_extracted * 100) if total_extracted > 0 else 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_images_processed": total_images,
            "total_imeis_extracted": total_extracted,
            "total_imeis_matched": total_matched,
            "total_imeis_unmatched": total_unmatched,
            "match_success_rate": round(match_rate, 2),
            "detailed_results": self.match_report
        }


class VarianceImageProcessor:
    """High-level processor for variance image analysis"""
    
    def __init__(self, db_manager, tesseract_path=None):
        """
        Initialize processor
        
        Args:
            db_manager: DatabaseManager instance
            tesseract_path: Path to Tesseract executable (Windows)
        """
        self.db_manager = db_manager
        self.extractor = IMEIExtractor(tesseract_path)
        self.matcher = IMEIMatcher(db_manager)
    
    def process_variance_images(self, image_folder: str) -> Dict:
        """
        Complete workflow: Extract IMEIs and match against variance database
        
        Args:
            image_folder: Folder containing variance images
            
        Returns:
            Complete processing report
        """
        print(f"Starting variance image processing from: {image_folder}")
        
        # Step 1: Extract IMEIs from all images
        print("Step 1: Extracting IMEIs from images...")
        extracted_batch = self.extractor.extract_batch(image_folder)
        
        # Step 2: Match extracted IMEIs against database
        print("Step 2: Matching extracted IMEIs against database...")
        match_results = self.matcher.process_batch(extracted_batch)
        
        # Step 3: Generate report
        print("Step 3: Generating report...")
        report = self.matcher.get_match_report()
        
        return report
    
    def process_single_image(self, image_path: str) -> Dict:
        """
        Process a single variance image
        
        Args:
            image_path: Path to image file
            
        Returns:
            Match result
        """
        # Extract IMEI
        imeis = self.extractor.extract_from_image(image_path)
        
        # Match against database
        image_name = Path(image_path).name
        match_result = self.matcher.match_image_imeis(imeis, image_name)
        
        return match_result
    
    def export_report(self, output_path: str) -> str:
        """
        Export processing report to JSON file
        
        Args:
            output_path: Path to save report
            
        Returns:
            Path to saved report
        """
        import json
        
        report = self.matcher.get_match_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return output_path


# Installation Guide for Tesseract OCR
TESSERACT_SETUP = """
TESSERACT OCR INSTALLATION
==========================

Windows:
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run installer (default installation is fine)
3. Tesseract will be installed to: C:\\Program Files\\Tesseract-OCR
4. Installation automatically adds to PATH

Verify Installation:
  - Open Command Prompt
  - Run: tesseract --version
  - Should see version information

Python Package:
  pip install pytesseract

If you want to specify path explicitly:
  pytesseract.pytesseract.pytesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

Linux/Mac:
  sudo apt-get install tesseract-ocr  (Linux)
  brew install tesseract  (Mac)
"""
