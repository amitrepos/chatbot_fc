# PDF Extraction Verification

## Purpose
This document verifies that PDF pages are being extracted correctly for testing the module/submodule filtering functionality.

## Extracted PDFs

### 1. First 2 Pages: `Generic_Wire_ISO_MX_v2_pages_1-2.pdf`
- **Source**: `Generic Wire ISO  MX_v2.pdf`
- **Pages**: 1-2
- **Purpose**: Verify the Table of Contents and initial pages are being read correctly
- **Expected Content**:
  - Page 1: Table of Contents listing all sections
  - Page 2: Maintenance for Generic ISO – MX section

### 2. Page 12: `Generic_Wire_ISO_MX_v2_page_12.pdf`
- **Source**: `Generic Wire ISO  MX_v2.pdf`
- **Page**: 12
- **Purpose**: Verify PPDCDMNT (Pricing Code Detail Maintenance) content
- **Expected Content**: PPDCDMNT section with pricing code maintenance details

## Issue Identified

There appears to be a discrepancy in image extraction:
- **Screenshot**: `screenshot_001_page1_img1.png`
- **Reported as**: Page 1, Image 1 (Media Maintenance)
- **Actually from**: Page 12 (PPDCDMNT - Pricing Code Detail Maintenance)

This suggests the image extraction process may have incorrect page number tracking.

## Verification Steps

1. **Check First 2 Pages PDF**:
   - Open `Generic_Wire_ISO_MX_v2_pages_1-2.pdf`
   - Verify it shows Table of Contents (Page 1) and Maintenance section (Page 2)
   - Confirm no PPDCDMNT content appears in these pages

2. **Check Page 12 PDF**:
   - Open `Generic_Wire_ISO_MX_v2_page_12.pdf`
   - Verify it shows PPDCDMNT (Pricing Code Detail Maintenance) content
   - Compare with `screenshot_001_page1_img1.png` to confirm they match

3. **Upload for Testing**:
   - Upload `Generic_Wire_ISO_MX_v2_pages_1-2.pdf` with module/submodule
   - Test query filtering to ensure it works correctly
   - Verify the content matches expectations

## Next Steps

1. Review the image extraction script (`scripts/process_pdf_images.py`)
2. Fix page number tracking if incorrect
3. Re-extract images with correct page numbers
4. Update the manual document with correct page references

## Files Created

- `data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf` - First 2 pages for verification
- `data/documents/Generic_Wire_ISO_MX_v2_page_12.pdf` - Page 12 for PPDCDMNT verification
- `scripts/extract_pdf_pages.py` - Script to extract specific pages from PDFs


