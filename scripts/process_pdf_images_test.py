"""
Non-interactive test script to process first 5 images automatically.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import httpx
from loguru import logger
import time
import hashlib
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.vision import FlexCubeVision
from scripts.process_pdf_images_incremental import (
    extract_images_from_pdf,
    extract_function_id,
    find_best_matching_page,
    calculate_image_hash
)

def describe_image_fast(vision: FlexCubeVision, image_bytes: bytes, page_num: int, context: str = "") -> tuple[str, str]:
    """Fast version with optimized prompt."""
    prompt = f"""Analyze this FlexCube screenshot (page {page_num}).

Identify:
1. Screen/Function Name (look for "Function ID = XXXXX")
2. Main purpose (1-2 sentences)
3. Key visible fields (3-5 items)

CRITICAL: If Function ID found, include as "Function ID = XXXXX".

{context[:200] if context else ''}

Concise description (2-3 paragraphs)."""

    try:
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        max_retries = 2
        timeout_seconds = 180.0
        
        for attempt in range(max_retries):
            try:
                response = vision.client.post(
                    f"{vision.base_url}/api/generate",
                    json={
                        "model": vision.model_name,
                        "prompt": prompt,
                        "images": [image_base64],
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 512
                        }
                    },
                    timeout=timeout_seconds
                )
                response.raise_for_status()
                break
            except (httpx.TimeoutException, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Retry {attempt + 1}/{max_retries}...")
                    time.sleep(2)
                    continue
                else:
                    raise
        
        result = response.json()
        description = result.get("response", "").strip()
        function_id = extract_function_id(description)
        
        if not function_id and context:
            function_id = extract_function_id(context)
        
        return description, function_id
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}", None

def main():
    # Use the full PDF, not the 2-page extract
    pdf_path = Path("/var/www/chatbot_FC/data/documents/Generic Wire ISO  MX_v2.pdf")
    output_file = pdf_path.parent / f"{pdf_path.stem}_test_extract.txt"
    images_dir = pdf_path.parent / f"{pdf_path.stem}_test_images"
    images_dir.mkdir(exist_ok=True)
    
    print("="*80)
    print("PDF IMAGE EXTRACTION TEST - First 5 Pages")
    print("="*80)
    
    # Initialize vision
    print("\nInitializing LLaVA...")
    vision = FlexCubeVision(model_name="llava:7b", base_url="http://localhost:11434")
    
    # Extract images (first 5 pages)
    print("\nExtracting images...")
    images = extract_images_from_pdf(str(pdf_path), min_size=100, max_pages=5)
    print(f"Found {len(images)} unique images")
    
    # Extract PDF text
    print("Extracting PDF text...")
    doc = fitz.open(str(pdf_path))
    pdf_text_by_page = {}
    for page_num in range(min(5, len(doc))):
        page = doc[page_num]
        pdf_text_by_page[page_num + 1] = page.get_text()
    doc.close()
    
    # Process more images to get variety across pages 1-5
    # Since images are deduplicated, we need to process more to see different pages
    max_images = min(15, len(images))  # Process 15 images to get variety
    print(f"\nProcessing first {max_images} images to capture variety across pages 1-5...")
    print("="*80)
    
    manual_content = [
        f"# Test Extract: {pdf_path.name}",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Pages: 1-5",
        f"Images Processed: {max_images}",
        f"\n{'='*80}\n"
    ]
    
    # Process ALL unique images, not just unique Function IDs
    # This shows what's actually visible in the PDF
    processed_function_ids = set()
    processed_count = 0
    
    for idx, image_info in enumerate(images[:max_images], 1):
        original_page = image_info["page_number"]
        image_index = image_info["image_index"]
        
        print(f"\n[{idx}/{max_images}] Processing image from page {original_page}...")
        
        # Get context
        page_context = pdf_text_by_page.get(original_page, "")[:500] if pdf_text_by_page else ""
        
        # Describe with LLaVA
        print(f"  Analyzing with LLaVA...")
        start_time = time.time()
        description, function_id = describe_image_fast(vision, image_info["image_bytes"], original_page, page_context)
        elapsed = time.time() - start_time
        print(f"  ✅ Done ({elapsed:.1f}s)")
        
        # Page matching
        pdf_text = image_info.get("pdf_text_by_page", pdf_text_by_page)
        matched_page = find_best_matching_page(description, function_id or "", pdf_text, original_page, 2)
        
        if matched_page != original_page:
            print(f"  📄 Page correction: {original_page} → {matched_page}")
            page_context = pdf_text.get(matched_page, "")[:500] if pdf_text else ""
        
        # Show Function ID but don't skip duplicates - process all unique images
        if function_id:
            print(f"  📋 Function ID: {function_id}")
            if function_id in processed_function_ids:
                print(f"  ⚠️  Note: Same Function ID as previous, but different image - processing anyway")
            processed_function_ids.add(function_id)
        
        processed_count += 1
        
        # Save image
        image_filename = f"screenshot_{processed_count:03d}_page{matched_page}_img{image_index}.png"
        image_path = images_dir / image_filename
        image = Image.open(io.BytesIO(image_info["image_bytes"]))
        image.save(image_path, "PNG")
        print(f"  💾 Saved: {image_filename}")
        
        # Add to manual
        manual_content.append(f"\n## Screenshot {processed_count}: Page {matched_page}, Image {image_index}")
        if function_id:
            manual_content.append(f"**Function ID:** {function_id}")
        manual_content.append(f"\n**Image:** `{images_dir.name}/{image_filename}`")
        manual_content.append(f"**Dimensions:** {image_info['width']} x {image_info['height']} pixels")
        if page_context:
            manual_content.append(f"\n**Page Context:**\n{page_context[:300]}...")
        manual_content.append(f"\n**Description:**\n{description}")
        manual_content.append(f"\n{'─'*80}\n")
    
    # Save manual
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(manual_content))
    
    print("\n" + "="*80)
    print(f"✅ COMPLETE!")
    print(f"   Images analyzed: {max_images}")
    print(f"   Screenshots processed: {processed_count}")
    print(f"   Unique Function IDs found: {len(processed_function_ids)}")
    print(f"   Manual: {output_file}")
    print(f"   Images: {images_dir}")
    print("="*80)

if __name__ == "__main__":
    main()

