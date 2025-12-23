# PDF Extraction Fix Summary

## Issue Identified

**Problem**: Screenshots extracted from PDF were reported as being from "Page 1" (Table of Contents), but the images actually show Media Maintenance screens which appear on Page 2.

**Root Cause**: The PDF has an unusual structure where:
- Images are stored as shared objects across multiple pages
- The same 40 images appear on both Page 1 and Page 2
- PyMuPDF reports images based on where the image objects are stored, not where they visually appear
- Page 1 text = "Table of Contents"
- Page 2 text = "Media Maintenance (Function ID = MSDMEDMT)"
- But images showing Media Maintenance are stored on Page 1

## Solution Implemented

Added **text-based page matching** to the extraction script:

1. **New Function**: `find_best_matching_page()`
   - Analyzes LLaVA description of the image
   - Extracts Function IDs and keywords
   - Searches surrounding pages (±2 pages) for matching text content
   - Returns the page number with the best content match

2. **Updated Extraction Flow**:
   - Extract images from PDF (as before)
   - Get LLaVA description of image
   - Extract Function ID from description
   - **NEW**: Match image to correct page based on text content
   - Use matched page number for output and context

## Changes Made

### File: `scripts/process_pdf_images_incremental.py`

1. Added `find_best_matching_page()` function (lines ~36-95)
   - Takes image description, Function ID, and page text
   - Scores pages based on keyword matches
   - Returns best matching page number

2. Updated `extract_images_from_pdf()` function
   - Now extracts and stores PDF text for each page
   - Stores `pdf_text_by_page` in image info for later matching

3. Updated main processing loop
   - After LLaVA analysis, calls `find_best_matching_page()`
   - Updates page number if a better match is found
   - Logs page corrections for transparency

## How It Works

```
1. Extract image from PDF (found on Page 1)
   ↓
2. Get LLaVA description: "Media Maintenance screen..."
   ↓
3. Extract Function ID: "MSDMEDMT"
   ↓
4. Search pages 1-3 for "MSDMEDMT" and "Media Maintenance"
   ↓
5. Find Page 2 has matching text → Update page number to 2
   ↓
6. Use Page 2 for output and context
```

## Testing

To test the fix:

1. **Re-run extraction on 2-page PDF**:
   ```bash
   python scripts/process_pdf_images_incremental.py "data/documents/Generic_Wire_ISO_MX_v2_pages_1-2.pdf"
   ```

2. **Verify output**:
   - Screenshots should now be assigned to Page 2 (Media Maintenance)
   - Page context should show Media Maintenance text, not Table of Contents
   - Logs should show page corrections when images are rematched

3. **Check manual file**:
   - Open `Generic Wire ISO  MX_v2_pages_1-2_manual_incremental.txt`
   - Verify screenshots are labeled as "Page 2" instead of "Page 1"
   - Verify page context matches the screenshot content

## Expected Results

**Before Fix**:
- Screenshot 1: Page 1, Image 1 (Table of Contents context)
- Screenshot 2: Page 1, Image 2 (Table of Contents context)
- Screenshot 3: Page 1, Image 3 (Table of Contents context)

**After Fix**:
- Screenshot 1: Page 2, Image 1 (Media Maintenance context) ✅
- Screenshot 2: Page 2, Image 2 (Media Maintenance context) ✅
- Screenshot 3: Page 2, Image 3 (Media Maintenance context) ✅

## Benefits

1. **Accurate Page Assignment**: Images are matched to pages where content actually appears
2. **Better Context**: Page context text matches the screenshot content
3. **Improved RAG**: Better indexing and retrieval with correct page references
4. **Transparency**: Logs show when page corrections are made

## Limitations

- Only searches ±2 pages around the original page (configurable via `search_range`)
- Relies on text matching, so may not work if PDF text is corrupted or missing
- Requires LLaVA description first (adds slight processing overhead)

## Next Steps

1. Test the fix with the 2-page PDF extract
2. If successful, re-extract all images from the full PDF
3. Update documentation to reflect the fix
4. Consider applying same fix to `process_pdf_images.py` (non-incremental version)


