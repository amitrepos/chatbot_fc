"""
Script to extract specific pages from a PDF file.

Usage:
    python scripts/extract_pdf_pages.py "data/documents/Generic Wire ISO  MX_v2.pdf" --pages 1,2 --output "data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf"
"""

import sys
import argparse
from pathlib import Path
import PyPDF2

def extract_pages(input_pdf_path: str, output_pdf_path: str, pages: list):
    """
    Extract specific pages from a PDF file.
    
    Args:
        input_pdf_path: Path to input PDF file
        output_pdf_path: Path to output PDF file
        pages: List of page numbers (1-indexed) to extract
    """
    input_path = Path(input_pdf_path)
    output_path = Path(output_pdf_path)
    
    if not input_path.exists():
        print(f"Error: Input file not found: {input_pdf_path}")
        return False
    
    try:
        # Open the input PDF
        with open(input_path, 'rb') as input_file:
            pdf_reader = PyPDF2.PdfReader(input_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            total_pages = len(pdf_reader.pages)
            print(f"Total pages in PDF: {total_pages}")
            
            # Extract specified pages (convert to 0-indexed)
            for page_num in pages:
                if page_num < 1 or page_num > total_pages:
                    print(f"Warning: Page {page_num} is out of range (1-{total_pages}). Skipping.")
                    continue
                
                # Add page (0-indexed)
                page = pdf_reader.pages[page_num - 1]
                pdf_writer.add_page(page)
                print(f"Extracted page {page_num}")
            
            # Write the output PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            print(f"\nSuccessfully created: {output_path}")
            print(f"Extracted {len(pdf_writer.pages)} page(s)")
            return True
            
    except Exception as e:
        print(f"Error extracting pages: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract specific pages from a PDF file")
    parser.add_argument("input_pdf", help="Path to input PDF file")
    parser.add_argument("--pages", required=True, help="Comma-separated list of page numbers (1-indexed)")
    parser.add_argument("--output", help="Path to output PDF file (default: input_name_pages_X-Y.pdf)")
    
    args = parser.parse_args()
    
    # Parse page numbers
    try:
        page_numbers = [int(p.strip()) for p in args.pages.split(',')]
    except ValueError:
        print("Error: Invalid page numbers. Use comma-separated integers (e.g., 1,2,3)")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input_pdf)
        pages_str = "-".join(map(str, sorted(page_numbers)))
        output_path = input_path.parent / f"{input_path.stem}_pages_{pages_str}.pdf"
    
    # Extract pages
    success = extract_pages(args.input_pdf, output_path, page_numbers)
    sys.exit(0 if success else 1)


