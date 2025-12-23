"""
Quick test script to verify page matching logic works correctly.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.process_pdf_images_incremental import find_best_matching_page

def test_page_matching():
    """Test the page matching function with actual PDF text."""
    pdf_path = Path("/var/www/chatbot_FC/data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf")
    
    # Extract text from PDF
    doc = fitz.open(str(pdf_path))
    pdf_text_by_page = {}
    for page_num in range(len(doc)):
        page = doc[page_num]
        pdf_text_by_page[page_num + 1] = page.get_text()
    doc.close()
    
    print("PDF Text by Page:")
    print("="*80)
    for page_num, text in pdf_text_by_page.items():
        print(f"\nPage {page_num} (first 200 chars):")
        print(text[:200])
        print("-"*80)
    
    # Test cases
    print("\n\nTesting Page Matching:")
    print("="*80)
    
    # Test 1: Media Maintenance image description
    test_cases = [
        {
            "name": "Media Maintenance screenshot",
            "description": "The image displays a screenshot of the FlexCube banking software interface, specifically focusing on the 'Media Maintenance' function with a sub-function titled 'Source Network Preference.' This screen is part of the configuration for generic ISO (Message Switching Device) settings in the MX environment.",
            "function_id": "MSDMEDMT",
            "original_page": 1,
            "expected_page": 2
        },
        {
            "name": "Table of Contents (should stay on page 1)",
            "description": "This is a table of contents showing various sections and page numbers.",
            "function_id": None,
            "original_page": 1,
            "expected_page": 1
        }
    ]
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print(f"  Original page: {test['original_page']}")
        print(f"  Expected page: {test['expected_page']}")
        
        matched_page = find_best_matching_page(
            test['description'],
            test['function_id'] or "",
            pdf_text_by_page,
            test['original_page'],
            search_range=2
        )
        
        print(f"  Matched page: {matched_page}")
        
        if matched_page == test['expected_page']:
            print(f"  ✅ PASS - Correctly matched to page {matched_page}")
        else:
            print(f"  ❌ FAIL - Expected page {test['expected_page']}, got {matched_page}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    test_page_matching()


