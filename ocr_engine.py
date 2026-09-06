#!/usr/bin/env python3
"""
OCR Engine - IMEI Extraction from Images

Monitors WhatsApp for uploaded variance images, runs OCR, extracts IMEIs.

Dependencies:
    - pytesseract
    - pillow
    - opencv-python
    - Tesseract-OCR (system binary)

Usage:
    from ocr_engine import OCREngine
    engine = OCREngine()
    imeis = engine.extract_imeis_from_image("path/to/image.png")
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

try:
    import pytesseract
    from PIL import Image
    import cv2
    import numpy as np
except ImportError:
    raise ImportError(
        "Required: pip install pytesseract pillow opencv-python\n"
        "Also install: Tesseract-OCR (system binary)"
    )

logger = logging.getLogger(__name__)


class OCREngine:
    """OCR engine for IMEI extraction"""
    
    # IMEI regex patterns
    IMEI_PATTERN = r'\b\d{15}\b'  # Standard 15-digit IMEI
    IMEI_PATTERNS = [
        r'\b\d{15}\b',              # 15-digit IMEI
        r'\b\d{14}\b',              # 14-digit (some devices)
        r'IMEI[:\s]+(\d{14,15})',   # IMEI: prefix
        r'(\d{14,15})',             # Fallback: any 14-15 digits
    ]
    
    def __init__(self):
        """Initialize OCR engine"""
        self.verify_tesseract()
    
    @staticmethod
    def verify_tesseract() -> bool:
        """Verify Tesseract is installed"""
        try:
            pytesseract.get_tesseract_version()
            logger.info("✓ Tesseract verified")
            return True
        except Exception as e:
            logger.error(f"Tesseract not found: {e}")
            logger.info("Install: https://github.com/UB-Mannheim/tesseract/wiki")
            return False
    
    def preprocess_image(self, image_path: str) -> Optional[np.ndarray]:
        """Preprocess image for better OCR accuracy"""
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Could not read image: {image_path}")
                return None
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply thresholding
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # Denoise
            denoised = cv2.fastNlMearsDenoising(thresh, None, h=10)
            
            # Upscale for better OCR
            upscaled = cv2.resize(denoised, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            logger.debug("Image preprocessed successfully")
            return upscaled
            
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            return None
    
    def extract_text_from_image(self, image_path: str, preprocess: bool = True) -> Optional[str]:
        """Extract text from image using Tesseract OCR"""
        try:
            logger.info(f"Extracting text from {Path(image_path).name}...")
            
            if preprocess:
                # Use preprocessed image
                processed = self.preprocess_image(image_path)
                if processed is None:
                    return None
                
                # Convert to PIL Image for pytesseract
                pil_img = Image.fromarray(processed)
                text = pytesseract.image_to_string(pil_img)
            else:
                # Use raw image
                text = pytesseract.image_to_string(image_path)
            
            logger.debug(f"Extracted text:\n{text[:200]}...")
            return text
            
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None
    
    def extract_imeis_from_text(self, text: str) -> List[str]:
        """Extract IMEI numbers from OCR text"""
        try:
            imeis = []
            
            # Try each pattern
            for pattern in self.IMEI_PATTERNS:
                matches = re.findall(pattern, text, re.IGNORECASE)
                imeis.extend(matches)
            
            # Remove duplicates and invalid entries
            imeis = list(set(imeis))
            imeis = [imei for imei in imeis if self._validate_imei(imei)]
            
            logger.info(f"Found {len(imeis)} IMEIs: {imeis}")
            return imeis
            
        except Exception as e:
            logger.error(f"IMEI extraction error: {e}")
            return []
    
    @staticmethod
    def _validate_imei(imei: str) -> bool:
        """Validate IMEI checksum (Luhn algorithm)"""
        try:
            # Remove non-digits
            imei = ''.join(filter(str.isdigit, imei))
            
            # Check length
            if len(imei) not in [14, 15]:
                return False
            
            # Luhn check
            total = 0
            for i, digit in enumerate(reversed(imei)):
                d = int(digit)
                if i % 2 == 1:
                    d *= 2
                    if d > 9:
                        d -= 9
                total += d
            
            return total % 10 == 0
            
        except:
            return False
    
    def extract_imeis_from_image(self, image_path: str) -> List[str]:
        """Extract IMEIs from image (preprocess + OCR + parse)"""
        try:
            # Step 1: OCR
            text = self.extract_text_from_image(image_path, preprocess=True)
            if not text:
                return []
            
            # Step 2: Parse IMEIs
            imeis = self.extract_imeis_from_text(text)
            
            return imeis
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return []
    
    def extract_imeis_from_directory(self, directory: str) -> dict:
        """Extract IMEIs from all images in directory"""
        try:
            results = {}
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
            
            for image_file in Path(directory).glob('*'):
                if image_file.suffix.lower() in image_extensions:
                    imeis = self.extract_imeis_from_image(str(image_file))
                    results[image_file.name] = imeis
            
            logger.info(f"Processed {len(results)} images")
            return results
            
        except Exception as e:
            logger.error(f"Directory processing error: {e}")
            return {}


class VarianceReconciler:
    """Match extracted IMEIs against variance dataset"""
    
    def __init__(self):
        self.variance_data = {}  # Dict[imei] = variance_record
        self.cleared_imeis = set()
    
    def load_variances(self, variances: dict):
        """Load variance data"""
        self.variance_data = variances
        logger.info(f"Loaded {len(variances)} variance records")
    
    def reconcile_imeis(self, extracted_imeis: List[str]) -> dict:
        """Match extracted IMEIs against variances"""
        try:
            matches = {
                'cleared': [],
                'not_found': [],
                'partial': []
            }
            
            for imei in extracted_imeis:
                if imei in self.variance_data:
                    matches['cleared'].append(imei)
                    self.cleared_imeis.add(imei)
                else:
                    # Try partial match
                    partial = [v for v in self.variance_data if imei in v or v in imei]
                    if partial:
                        matches['partial'].append({'imei': imei, 'candidates': partial})
                    else:
                        matches['not_found'].append(imei)
            
            logger.info(f"Reconciliation: {len(matches['cleared'])} cleared, "
                       f"{len(matches['not_found'])} not found")
            return matches
            
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
            return {'cleared': [], 'not_found': extracted_imeis, 'partial': []}
    
    def get_cleared_count(self) -> int:
        """Get total cleared IMEI count"""
        return len(self.cleared_imeis)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = OCREngine()
    
    # Test with sample image
    # imeis = engine.extract_imeis_from_image("sample.png")
    # print(f"Extracted IMEIs: {imeis}")
