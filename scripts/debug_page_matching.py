"""
Debug script to understand why page matching isn't working.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.process_pdf_images_incremental import find_best_matching_page

def debug_page_matching():
    """Debug the page matching function."""
    pdf_path = Path("/var/www/chatbot_FC/data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf")
    
    # Extract text from PDF
    doc = fitz.open(str(pdf_path))
    pdf_text_by_page = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        pdf_text_by_page[page_num + 1] = page.get_text()
    doc.close()
    
    print("Detailed Page Analysis:")
    print("="*80)
    for page_num, text in pdf_text_by_page.items():
        print(f"\nPage {page_num}:")
        print(f"  Length: {len(text)} chars")
        print(f"  Word count: {len(text.split())} words")
        print(f"  Dots count: {text.count('.')}")
        print(f"  Has 'TABLE OF CONTENTS': {'TABLE OF CONTENTS' in text.upper()}")
        print(f"  Has 'NOTE': {'NOTE' in text.upper()}")
        print(f"  Has 'MSDMEDMT': {'MSDMEDMT' in text.upper()}")
        print(f"  Has 'MEDIA MAINTENANCE': {'MEDIA MAINTENANCE' in text.upper()}")
        print(f"  Full text:")
        print(f"  {text[:500]}")
        print("-"*80)
    
    # Test the matching
    description = "The image displays a screenshot of the FlexCube banking software interface, specifically focusing on the 'Media Maintenance' function with a sub-function titled 'Source Network Preference.'"
    function_id = "MSDMEDMT"
    
    print("\n\nTesting Matching Logic:")
    print("="*80)
    print(f"Description: {description[:100]}...")
    print(f"Function ID: {function_id}")
    print(f"Original page: 1")
    
    matched = find_best_matching_page(description, function_id, pdf_text_by_page, 1, 2)
    print(f"Matched page: {matched}")

if __name__ == "__main__":
    debug_page_matching()


