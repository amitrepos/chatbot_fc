# PDF Image Processing Guide

## Overview

This guide explains how to process PDF files that contain screenshots/images and convert them into searchable text manuals for the RAG pipeline.

## Problem Statement

Many FlexCube documentation PDFs contain screenshots that show:
- Screen layouts and UI elements
- Configuration examples
- Step-by-step processes
- Field names and labels

**Current Issue**: The standard PDF text extraction (`PDFReader`) only extracts text, **NOT images**. This means valuable visual information is lost.

## Solution

We use **LLaVA vision model** to:
1. Extract images from PDFs
2. Analyze each screenshot in detail
3. Generate comprehensive text descriptions
4. Create a searchable text manual

## How It Works

### Architecture

```
PDF with Images
    ↓
Extract Images (PyMuPDF)
    ↓
Filter Small Images (icons/logos)
    ↓
For Each Screenshot:
    ↓
    Send to LLaVA Vision Model
    ↓
    Generate Detailed Description
    ↓
Combine into Text Manual
    ↓
Save as .txt file
    ↓
Index in RAG Pipeline
```

### Why This Approach?

✅ **Better than processing images during queries:**
- Images in PDFs are static documentation
- Text descriptions are more searchable
- Faster retrieval (no image processing during queries)
- Better semantic search with embeddings

✅ **Better than OCR:**
- LLaVA understands context and relationships
- Describes UI elements, not just text
- Explains purpose and functionality
- More natural language descriptions

## Usage

### Prerequisites

1. **Install dependencies:**
```bash
pip install PyMuPDF Pillow
```

2. **Ensure LLaVA is running in Ollama:**
```bash
ollama pull llava:7b
```

### Process a PDF

```bash
# Activate virtual environment
source venv/bin/activate

# Process the PDF
python scripts/process_pdf_images.py "data/documents/Generic Wire ISO  MX_v2.pdf"
```

### Custom Output Filename

```bash
python scripts/process_pdf_images.py "data/documents/Generic Wire ISO  MX_v2.pdf" "Generic_Wire_ISO_MX_Manual.txt"
```

## Output Format

The generated manual includes:

1. **Header**: Source PDF, processing date, image count
2. **For Each Screenshot**:
   - Page number and image index
   - Image dimensions and position
   - Page text context (if available)
   - Detailed LLaVA description including:
     - Screen/Function name
     - Purpose and usage
     - Key fields and sections
     - Configuration details
     - Step-by-step context
     - Important notes

### Example Output

```
# Manual: Generic Wire ISO  MX_v2.pdf

Generated from PDF screenshots using LLaVA vision model
Source PDF: Generic Wire ISO  MX_v2.pdf
Total screenshots processed: 15

================================================================================

## Screenshot 1: Page 2, Image 1

**Image Details:**
- Dimensions: 1200 x 800 pixels
- Position on page: (50, 100, 1250, 900)

**Page Context:**
Media Maintenance (Function ID = MSDMEDMT)
Note: For MX Media Code should be FINPLUS...

**Screenshot Description:**

**Screen/Function:** Media Maintenance (MSDMEDMT)
**Description:** Configuration screen for media maintenance in FlexCube

**Detailed Analysis:**
This screenshot shows the Media Maintenance screen (Function ID: MSDMEDMT) in FlexCube.
The screen is used to configure media settings for ISO MX messages. The key field visible
is "Media Code" which should be set to "FINPLUS" for MX messages. The screen displays
a form with various configuration options for media maintenance...

────────────────────────────────────────────────────────────────────────────────
```

## After Processing

### 1. Review the Manual

Check the generated manual to ensure descriptions are accurate:
```bash
cat data/documents/Generic_Wire_ISO_MX_v2_manual.txt
```

### 2. Re-index Documents

The new manual needs to be indexed in the RAG pipeline:

```python
from src.rag.pipeline import FlexCubeRAGPipeline

pipeline = FlexCubeRAGPipeline()
pipeline.index_documents()  # This will include the new manual
```

Or via API (if you have an indexing endpoint):
```bash
curl -X POST http://localhost:8000/api/admin/reindex
```

## Configuration Options

### Minimum Image Size

Filter out small icons/logos (default: 100x100 pixels):

```python
processor.process_pdf(
    pdf_path="path/to/file.pdf",
    min_image_size=150  # Only process images >= 150x150
)
```

### Vision Model Settings

The script uses:
- **Model**: `llava:7b` (configurable)
- **Temperature**: 0.2 (low for factual descriptions)
- **Max tokens**: 2048 (allows detailed descriptions)

## Troubleshooting

### No Images Extracted

**Problem**: Script reports "No significant images found"

**Solutions**:
1. Check if PDF actually contains images (not just text)
2. Lower `min_image_size` threshold
3. Verify PDF is not corrupted

### LLaVA Timeout Errors

**Problem**: Vision model times out

**Solutions**:
1. Increase timeout in `FlexCubeVision` class
2. Process images in smaller batches
3. Check Ollama is running: `curl http://localhost:11434/api/tags`

### Poor Descriptions

**Problem**: LLaVA descriptions are too generic

**Solutions**:
1. Ensure LLaVA model is properly loaded: `ollama show llava:7b`
2. Check image quality (low-res images = poor descriptions)
3. Adjust temperature (lower = more factual, higher = more creative)

## Best Practices

1. **Process PDFs once**: Generate manual, then index it
2. **Review output**: Check descriptions for accuracy
3. **Combine with text**: Manual includes page text context
4. **Update when PDF changes**: Re-process if PDF is updated
5. **Keep originals**: Don't delete original PDFs

## Limitations

1. **Processing time**: Each image takes ~10-30 seconds (LLaVA inference)
2. **Image quality**: Low-res screenshots = less accurate descriptions
3. **Context**: LLaVA may miss some technical details
4. **Language**: Currently optimized for English

## Future Enhancements

- [ ] Batch processing for multiple PDFs
- [ ] OCR fallback for text-heavy images
- [ ] Automatic re-indexing after processing
- [ ] Quality scoring for descriptions
- [ ] Support for other vision models

## Related Files

- **Script**: `scripts/process_pdf_images.py`
- **Vision Module**: `src/rag/vision.py`
- **Document Loader**: `src/rag/document_loader.py`
- **RAG Pipeline**: `src/rag/pipeline.py`


