"""
Diagnostic script to check PDF image extraction and page number mapping.

This script helps identify issues with:
1. Which PDF file was used for extraction
2. Page numbers in the extracted images
3. Actual content on those pages
4. Mismatch between reported pages and actual content
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io

def analyze_pdf_images(pdf_path: str):
    """Analyze images in a PDF and show page numbers."""
    print(f"\n{'='*80}")
    print(f"Analyzing PDF: {pdf_path}")
    print(f"{'='*80}\n")
    
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    print(f"Total pages in PDF: {total_pages}\n")
    
    # Extract text from first few pages
    print("Text content from first 3 pages:")
    print("-" * 80)
    for page_num in range(min(3, total_pages)):
        page = doc[page_num]
        text = page.get_text()
        print(f"\nPage {page_num + 1} (first 500 chars):")
        print(text[:500])
        print("-" * 80)
    
    # Count images per page
    print(f"\n\nImage count per page:")
    print("-" * 80)
    total_images = 0
    for page_num in range(total_pages):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        if image_list:
            print(f"Page {page_num + 1}: {len(image_list)} image(s)")
            total_images += len(image_list)
            
            # Show first image details
            if image_list:
                try:
                    xref = image_list[0][0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(image_bytes))
                    print(f"  First image: {image.width}x{image.height} pixels")
                except Exception as e:
                    print(f"  Could not analyze first image: {e}")
        else:
            print(f"Page {page_num + 1}: 0 images")
    
    print(f"\nTotal images found: {total_images}")
    doc.close()
    
    return total_images


def compare_pdfs():
    """Compare the full PDF with the 2-page extract."""
    base_dir = Path("/var/www/chatbot_FC/data/documents")
    
    full_pdf = base_dir / "Generic Wire ISO  MX_v2.pdf"
    extract_pdf = base_dir / "Generic_Wire_ISO_MX_v2_pages_1-2.pdf"
    
    print("\n" + "="*80)
    print("COMPARING PDF FILES")
    print("="*80)
    
    if full_pdf.exists():
        print(f"\n✅ Full PDF exists: {full_pdf}")
        analyze_pdf_images(str(full_pdf))
    else:
        print(f"\n❌ Full PDF not found: {full_pdf}")
    
    if extract_pdf.exists():
        print(f"\n✅ 2-page extract exists: {extract_pdf}")
        analyze_pdf_images(str(extract_pdf))
    else:
        print(f"\n❌ 2-page extract not found: {extract_pdf}")
    
    # Check which PDF was used for screenshot extraction
    manual_file = base_dir / "Generic Wire ISO  MX_v2_manual_incremental.txt"
    if manual_file.exists():
        print(f"\n\n{'='*80}")
        print("CHECKING MANUAL FILE")
        print("="*80)
        with open(manual_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "Source PDF: Generic Wire ISO  MX_v2.pdf" in content:
                print("\n✅ Manual shows source PDF: Generic Wire ISO  MX_v2.pdf (FULL PDF)")
                print("   This means screenshots were extracted from the FULL PDF, not the 2-page extract!")
                print("\n⚠️  ISSUE IDENTIFIED:")
                print("   - Screenshots show 'Page 1' but they're from the FULL PDF")
                print("   - In the full PDF, Page 1 = Table of Contents")
                print("   - But the screenshots show Media Maintenance screens")
                print("   - This suggests images are NOT on Page 1 of the full PDF")
            else:
                print("\n⚠️  Could not determine source PDF from manual")


if __name__ == "__main__":
    compare_pdfs()


