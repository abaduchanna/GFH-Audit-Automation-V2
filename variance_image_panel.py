"""
Variance Image Processing Panel for Tab 2
Integrates OCR IMEI extraction and matching with UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path
from datetime import datetime
import json

from ocr_imei_processor import VarianceImageProcessor


class VarianceImageProcessingPanel:
    """UI Panel for processing variance images with OCR"""
    
    def __init__(self, parent_frame, db_manager, tesseract_path=None):
        """
        Initialize variance image processing panel
        
        Args:
            parent_frame: Parent Tkinter frame
            db_manager: DatabaseManager instance
            tesseract_path: Optional path to Tesseract executable
        """
        self.db_manager = db_manager
        self.processor = VarianceImageProcessor(db_manager, tesseract_path)
        self.parent_frame = parent_frame
        
        self.selected_folder = None
        self.selected_image = None
        self.current_results = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI for image processing"""
        
        # Main container
        main_frame = ttk.LabelFrame(self.parent_frame, text="📸 IMEI Image Analysis (Tesseract OCR)", padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ===== Batch Processing Section =====
        batch_frame = ttk.LabelFrame(main_frame, text="Batch Processing", padding=10)
        batch_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Folder selection
        folder_frame = ttk.Frame(batch_frame)
        folder_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(folder_frame, text="Image Folder:").pack(side=tk.LEFT, padx=5)
        self.folder_label = ttk.Label(folder_frame, text="(none selected)", foreground="blue")
        self.folder_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(
            folder_frame,
            text="📂 Select Folder",
            command=self.select_image_folder
        ).pack(side=tk.RIGHT, padx=5)
        
        # Batch processing buttons
        button_frame = ttk.Frame(batch_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            button_frame,
            text="🔄 Process All Images in Folder",
            command=self.process_batch_images,
            width=30
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="💾 Export Report",
            command=self.export_batch_report
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Clear Results",
            command=self.clear_results
        ).pack(side=tk.LEFT, padx=5)
        
        # ===== Single Image Processing Section =====
        single_frame = ttk.LabelFrame(main_frame, text="Single Image Processing", padding=10)
        single_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Image selection
        image_frame = ttk.Frame(single_frame)
        image_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(image_frame, text="Select Image:").pack(side=tk.LEFT, padx=5)
        self.image_label = ttk.Label(image_frame, text="(none selected)", foreground="blue")
        self.image_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(
            image_frame,
            text="🖼️ Select Image",
            command=self.select_single_image
        ).pack(side=tk.RIGHT, padx=5)
        
        # Process buttons
        process_frame = ttk.Frame(single_frame)
        process_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(
            process_frame,
            text="🔍 Extract IMEIs from Image",
            command=self.process_single_image,
            width=30
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            process_frame,
            text="👁️ Preview Image",
            command=self.preview_image
        ).pack(side=tk.LEFT, padx=5)
        
        # ===== Results Display =====
        results_frame = ttk.LabelFrame(main_frame, text="📊 Results & Matches", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Results tabs
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab: Extracted IMEIs
        self.extracted_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.extracted_tab, text="Extracted IMEIs")
        
        # Tab: Matched Records
        self.matched_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.matched_tab, text="Matched Records")
        
        # Tab: Unmatched IMEIs
        self.unmatched_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.unmatched_tab, text="Unmatched IMEIs")
        
        # Tab: Report Summary
        self.summary_tab = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.summary_tab, text="Report Summary")
        
        # Setup each tab
        self._setup_extracted_tab()
        self._setup_matched_tab()
        self._setup_unmatched_tab()
        self._setup_summary_tab()
        
        # ===== Status Bar =====
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 9)).pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            status_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=300
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
    
    def _setup_extracted_tab(self):
        """Setup extracted IMEIs display"""
        # Treeview
        columns = ("Image", "IMEI", "Valid")
        tree = ttk.Treeview(self.extracted_tab, columns=columns, height=10)
        tree.heading("#0", text="ID")
        tree.column("#0", width=50)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=200)
        
        scrollbar = ttk.Scrollbar(self.extracted_tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.extracted_tree = tree
    
    def _setup_matched_tab(self):
        """Setup matched records display"""
        # Treeview
        columns = ("Image", "IMEI", "DB_IMEI", "Match Type", "Confidence", "Store", "Status")
        tree = ttk.Treeview(self.matched_tab, columns=columns, height=10)
        tree.heading("#0", text="ID")
        tree.column("#0", width=50)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(self.matched_tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.matched_tree = tree
        
        # Auto-update button
        button_frame = ttk.Frame(self.matched_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            button_frame,
            text="✓ Mark All as Cleared",
            command=self.mark_matched_cleared,
            width=30
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="📤 Update Database",
            command=self.update_database_from_matches
        ).pack(side=tk.LEFT, padx=5)
    
    def _setup_unmatched_tab(self):
        """Setup unmatched IMEIs display"""
        # Treeview
        columns = ("Image", "IMEI", "Extraction_Confidence")
        tree = ttk.Treeview(self.unmatched_tab, columns=columns, height=10)
        tree.heading("#0", text="ID")
        tree.column("#0", width=50)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=250)
        
        scrollbar = ttk.Scrollbar(self.unmatched_tab, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.unmatched_tree = tree
        
        # Add to variance button
        button_frame = ttk.Frame(self.unmatched_tab)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            button_frame,
            text="➕ Add as New Variance",
            command=self.add_unmatched_to_variance
        ).pack(side=tk.LEFT, padx=5)
    
    def _setup_summary_tab(self):
        """Setup report summary display"""
        # Text widget for summary
        summary_text = tk.Text(self.summary_tab, height=15, width=60, wrap=tk.WORD)
        summary_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(self.summary_tab, orient=tk.VERTICAL, command=summary_text.yview)
        summary_text.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.summary_text = summary_text
    
    # ===== File Selection =====
    
    def select_image_folder(self):
        """Select folder containing variance images"""
        folder = filedialog.askdirectory(title="Select Folder with Variance Images")
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder)
            
            # Count images in folder
            image_count = len(list(Path(folder).glob('*.[jp][pn]g')) + list(Path(folder).glob('*.png')))
            self.status_var.set(f"Selected folder: {folder} ({image_count} images)")
    
    def select_single_image(self):
        """Select single image file"""
        image = filedialog.askopenfilename(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff"), ("All files", "*.*")]
        )
        if image:
            self.selected_image = image
            self.image_label.config(text=Path(image).name)
            self.status_var.set(f"Selected image: {Path(image).name}")
    
    def preview_image(self):
        """Preview selected image"""
        if not self.selected_image:
            messagebox.showwarning("Warning", "No image selected")
            return
        
        # Open image with default viewer
        import subprocess
        import sys
        
        try:
            if sys.platform == "win32":
                subprocess.Popen(['start', self.selected_image], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(['open', self.selected_image])
            else:
                subprocess.Popen(['xdg-open', self.selected_image])
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image: {str(e)}")
    
    # ===== Processing =====
    
    def process_batch_images(self):
        """Process all images in selected folder"""
        if not self.selected_folder:
            messagebox.showwarning("Warning", "Please select a folder first")
            return
        
        # Run in background thread
        thread = threading.Thread(
            target=self._process_batch_thread,
            daemon=True
        )
        thread.start()
    
    def _process_batch_thread(self):
        """Background thread for batch processing"""
        try:
            self.status_var.set("Processing images...")
            self.progress_var.set(0)
            
            # Process images
            results = self.processor.process_batch(
                self.processor.extractor.extract_batch(self.selected_folder)
            )
            
            self.current_results = self.processor.matcher.get_match_report()
            
            # Update UI
            self._display_results()
            
            self.status_var.set("✓ Batch processing complete")
            self.progress_var.set(100)
            
            messagebox.showinfo(
                "Success",
                f"Processed {len(results)} images\n"
                f"Matched: {self.current_results['total_imeis_matched']} IMEIs"
            )
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
    
    def process_single_image(self):
        """Process single selected image"""
        if not self.selected_image:
            messagebox.showwarning("Warning", "Please select an image first")
            return
        
        # Run in background thread
        thread = threading.Thread(
            target=self._process_single_thread,
            daemon=True
        )
        thread.start()
    
    def _process_single_thread(self):
        """Background thread for single image processing"""
        try:
            self.status_var.set("Processing image...")
            self.progress_var.set(50)
            
            # Process image
            result = self.processor.process_single_image(self.selected_image)
            
            self.current_results = {
                "single_result": result,
                "timestamp": datetime.now().isoformat()
            }
            
            # Display result
            self._display_single_result(result)
            
            self.status_var.set("✓ Image processing complete")
            self.progress_var.set(100)
            
            extracted = len(result.get("extracted_imeis", []))
            matched = len(result.get("matched_records", []))
            messagebox.showinfo(
                "Success",
                f"Extracted: {extracted} IMEIs\n"
                f"Matched: {matched} records"
            )
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Processing failed: {str(e)}")
    
    def _display_results(self):
        """Display batch processing results"""
        if not self.current_results:
            return
        
        # Clear previous results
        for item in self.extracted_tree.get_children():
            self.extracted_tree.delete(item)
        for item in self.matched_tree.get_children():
            self.matched_tree.delete(item)
        for item in self.unmatched_tree.get_children():
            self.unmatched_tree.delete(item)
        
        # Display extracted IMEIs
        idx = 1
        for result in self.current_results.get("detailed_results", []):
            image = result.get("image", "")
            for imei in result.get("extracted_imeis", []):
                self.extracted_tree.insert("", tk.END, text=str(idx), values=(image, imei, "✓"))
                idx += 1
        
        # Display matched records
        idx = 1
        for result in self.current_results.get("detailed_results", []):
            image = result.get("image", "")
            for matched in result.get("matched_records", []):
                self.matched_tree.insert("", tk.END, text=str(idx), values=(
                    image,
                    matched.get("imei", ""),
                    matched.get("database_imei", ""),
                    matched.get("match_type", ""),
                    matched.get("confidence", ""),
                    matched.get("record", {}).get("store", ""),
                    matched.get("record", {}).get("status", "")
                ))
                idx += 1
        
        # Display unmatched IMEIs
        idx = 1
        for result in self.current_results.get("detailed_results", []):
            image = result.get("image", "")
            for imei in result.get("unmatched_imeis", []):
                self.unmatched_tree.insert("", tk.END, text=str(idx), values=(image, imei, "?"))
                idx += 1
        
        # Display summary
        self._display_summary()
    
    def _display_single_result(self, result):
        """Display single image result"""
        # Clear previous
        for item in self.extracted_tree.get_children():
            self.extracted_tree.delete(item)
        for item in self.matched_tree.get_children():
            self.matched_tree.delete(item)
        for item in self.unmatched_tree.get_children():
            self.unmatched_tree.delete(item)
        
        image = result.get("image", "")
        
        # Extracted
        for idx, imei in enumerate(result.get("extracted_imeis", []), 1):
            self.extracted_tree.insert("", tk.END, text=str(idx), values=(image, imei, "✓"))
        
        # Matched
        for idx, matched in enumerate(result.get("matched_records", []), 1):
            self.matched_tree.insert("", tk.END, text=str(idx), values=(
                image,
                matched.get("imei", ""),
                matched.get("database_imei", ""),
                matched.get("match_type", ""),
                matched.get("confidence", ""),
                "",
                ""
            ))
        
        # Unmatched
        for idx, imei in enumerate(result.get("unmatched_imeis", []), 1):
            self.unmatched_tree.insert("", tk.END, text=str(idx), values=(image, imei, "?"))
    
    def _display_summary(self):
        """Display processing summary"""
        if not self.current_results:
            return
        
        summary = self.current_results
        
        text = f"""
OCR IMEI EXTRACTION & MATCHING REPORT
{'='*50}

Timestamp: {summary.get('timestamp', 'N/A')}

STATISTICS
─────────
Total Images Processed: {summary.get('total_images_processed', 0)}
Total IMEIs Extracted: {summary.get('total_imeis_extracted', 0)}
Total IMEIs Matched: {summary.get('total_imeis_matched', 0)}
Total IMEIs Unmatched: {summary.get('total_imeis_unmatched', 0)}
Success Rate: {summary.get('match_success_rate', 0)}%

RESULTS BY IMAGE
────────────────
"""
        
        for result in summary.get('detailed_results', []):
            text += f"\n📸 {result.get('image', 'Unknown')}\n"
            text += f"   Status: {result.get('status', 'UNKNOWN')}\n"
            text += f"   Extracted: {len(result.get('extracted_imeis', []))}\n"
            text += f"   Matched: {len(result.get('matched_records', []))}\n"
            text += f"   Unmatched: {len(result.get('unmatched_imeis', []))}\n"
        
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, text)
        self.summary_text.config(state=tk.DISABLED)
    
    # ===== Database Updates =====
    
    def mark_matched_cleared(self):
        """Mark all matched records as cleared"""
        if not self.current_results:
            messagebox.showwarning("Warning", "No results to update")
            return
        
        count = 0
        for result in self.current_results.get("detailed_results", []):
            for matched in result.get("matched_records", []):
                if self.processor.matcher.update_variance_status(
                    matched.get("record", {}),
                    "CLEARED",
                    f"Cleared via image matching"
                ):
                    count += 1
        
        messagebox.showinfo("Success", f"Marked {count} records as cleared")
    
    def update_database_from_matches(self):
        """Update database with matched records"""
        if not self.current_results:
            messagebox.showwarning("Warning", "No results to update")
            return
        
        count = 0
        for result in self.current_results.get("detailed_results", []):
            for matched in result.get("matched_records", []):
                if self.processor.matcher.update_variance_status(
                    matched.get("record", {}),
                    "MATCHED_FROM_IMAGE",
                    f"Matched: {matched.get('imei')} from {result.get('image')}"
                ):
                    count += 1
        
        messagebox.showinfo("Success", f"Updated {count} records in database")
    
    def add_unmatched_to_variance(self):
        """Add unmatched IMEIs to variance data"""
        # TODO: Implement adding new variance records from unmatched IMEIs
        messagebox.showinfo("Info", "Add to variance - coming soon")
    
    def export_batch_report(self):
        """Export batch processing report"""
        if not self.current_results:
            messagebox.showwarning("Warning", "No results to export")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filepath:
            try:
                saved_path = self.processor.export_report(filepath)
                messagebox.showinfo("Success", f"Report saved to: {saved_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save report: {str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        for item in self.extracted_tree.get_children():
            self.extracted_tree.delete(item)
        for item in self.matched_tree.get_children():
            self.matched_tree.delete(item)
        for item in self.unmatched_tree.get_children():
            self.unmatched_tree.delete(item)
        
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.config(state=tk.DISABLED)
        
        self.current_results = None
        self.status_var.set("Results cleared")
