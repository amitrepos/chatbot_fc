# PDF Image Extraction Issue Analysis

## Problem Statement

Screenshots extracted from the PDF are reported as being from "Page 1", but:
- Page 1 contains the **Table of Contents** (text only)
- The screenshots show **Media Maintenance** screens
- Media Maintenance content appears on **Page 2** (text)

## Root Cause Analysis

### Findings

1. **PDF Structure Issue**: The PDF has an unusual structure where:
   - **40 images are embedded on EVERY page** (all 23 pages)
   - **Pages 1 and 2 have IDENTICAL images** (all 40 image hashes match exactly)
   - This suggests images are shared/reused across pages in the PDF structure

2. **Image Extraction is Technically Correct**:
   - The extraction script correctly finds images on Page 1
   - The page numbers reported are accurate based on where PyMuPDF finds the image objects
   - Image dimensions match: 1029x540, 1031x597, 1037x545

3. **Content Mismatch**:
   - Page 1 text: "Table of Contents" (no Media Maintenance content)
   - Page 2 text: "Media Maintenance (Function ID = MSDMEDMT)"
   - But both pages have the same images showing Media Maintenance screens

### Why This Happens

The PDF appears to have been created in a way where:
- Images are stored once and referenced on multiple pages
- The image objects exist on Page 1, but they visually appear on Page 2
- PyMuPDF reports images based on where the image objects are stored, not where they visually appear

## Current Extraction Process

The extraction scripts (`process_pdf_images.py` and `process_pdf_images_incremental.py`) use:

```python
for page_num in range(len(doc)):
    page = doc[page_num]
    image_list = page.get_images(full=True)
    # Images are assigned to page_num + 1
```

This correctly identifies that images exist on Page 1, but doesn't account for:
- Images that are visually on different pages
- PDFs with shared/reused image objects

## Solutions

### Option 1: Use Text Context to Determine Correct Page (Recommended)

**Approach**: When extracting images, also extract text from the page and use it to determine if the image matches the page content.

**Implementation**:
1. Extract text from the page where image is found
2. Extract text from surrounding pages (±1 page)
3. Use LLaVA or text matching to determine which page's content matches the image
4. Assign the image to the page with matching content

**Pros**:
- More accurate page assignment
- Better context for RAG indexing
- Handles unusual PDF structures

**Cons**:
- More complex
- Requires additional processing

### Option 2: Filter by Image Position on Page

**Approach**: Check if images are actually visible on the page by checking their bounding boxes.

**Implementation**:
1. Get image bounding box position
2. Check if image is within page bounds
3. Only process images that are actually visible on the page

**Pros**:
- Simple to implement
- Filters out hidden/referenced images

**Cons**:
- May not work if images are positioned off-page but still referenced

### Option 3: Use Visual Page Rendering

**Approach**: Render each page as an image and check which rendered page contains the screenshot.

**Implementation**:
1. Render each PDF page to an image
2. Extract screenshots from PDF
3. Use image matching to find which rendered page contains each screenshot

**Pros**:
- Most accurate (matches what user sees)
- Handles all PDF structure issues

**Cons**:
- Resource intensive
- Slower processing

### Option 4: Accept Current Behavior with Better Documentation

**Approach**: Keep current extraction but improve documentation to note that page numbers may not match visual appearance.

**Implementation**:
1. Add warning in extraction output
2. Include text context from surrounding pages
3. Let LLaVA description help identify correct content

**Pros**:
- No code changes needed
- Quick fix

**Cons**:
- Less accurate page references
- May confuse users

## Recommended Solution

**Use Option 1 (Text Context Matching)** because:
1. It provides the most accurate page assignment
2. It improves RAG context by matching images to their actual content pages
3. It's a reasonable balance between accuracy and performance

## Implementation Steps

1. **Modify extraction script** to:
   - Extract text from current page and ±1 pages
   - Use text matching or LLaVA to determine best page match
   - Assign image to page with matching content

2. **Update page number tracking** to use matched page instead of object location

3. **Add validation** to warn when image content doesn't match page text

4. **Re-extract images** with corrected page numbers

## Verification

After implementing the fix:
1. Re-run extraction on `Generic_Wire_ISO_MX_v2_pages_1-2.pdf`
2. Verify screenshots are assigned to Page 2 (Media Maintenance) instead of Page 1
3. Check that extracted images match the text content of their assigned pages

## Files Affected

- `scripts/process_pdf_images.py` - Main extraction script
- `scripts/process_pdf_images_incremental.py` - Incremental extraction script
- `data/documents/Generic Wire ISO  MX_v2_manual_incremental.txt` - Will need regeneration

## Next Steps

1. Implement text-based page matching in extraction scripts
2. Test with the 2-page PDF extract
3. Re-extract all images with correct page numbers
4. Update documentation


