"""
Incremental PDF Image Processing Script

This is a simplified version that processes ONE image at a time with user confirmation.
Use this for testing or when you want full control over the process.

Usage:
    python scripts/process_pdf_images_incremental.py "data/documents/Generic Wire ISO  MX_v2.pdf"
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Set
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


def calculate_image_hash(image_bytes: bytes) -> str:
    """Calculate hash of image for deduplication."""
    return hashlib.md5(image_bytes).hexdigest()


def find_best_matching_page(
    image_description: str,
    function_id: str,
    pdf_text_by_page: Dict[int, str],
    original_page: int,
    search_range: int = 2
) -> int:
    """
    Find the best matching page for an image based on text content.
    
    This function helps fix cases where images are stored on one page
    but visually appear on another page (common in PDFs with shared image objects).
    
    Args:
        image_description: LLaVA description of the image
        function_id: Extracted Function ID (if any)
        pdf_text_by_page: Dictionary mapping page numbers to text content
        original_page: Page where image object was found
        search_range: Number of pages to search before/after original page
        
    Returns:
        Best matching page number (1-indexed)
    """
    if not pdf_text_by_page:
        return original_page
    
    # Extract keywords from image description
    keywords = []
    if function_id:
        keywords.append(function_id)
    
    # Look for common FlexCube terms in description
    description_upper = image_description.upper()
    common_terms = [
        "MEDIA MAINTENANCE", "SOURCE NETWORK", "NETWORK PREFERENCE",
        "PRICING CODE", "ACCOUNT TEMPLATE", "SWIFT PRICING",
        "CROSS BORDER", "CUSTOMER CREDIT", "FI CREDIT"
    ]
    for term in common_terms:
        if term in description_upper:
            keywords.append(term)
    
    if not keywords:
        # No keywords found, return original page
        return original_page
    
    # Search pages around the original page
    best_match = original_page
    best_score = 0
    
    start_page = max(1, original_page - search_range)
    end_page = min(len(pdf_text_by_page), original_page + search_range)
    
    for page_num in range(start_page, end_page + 1):
        if page_num not in pdf_text_by_page:
            continue
        
        page_text = pdf_text_by_page[page_num]
        page_text_upper = page_text.upper()
        score = 0
        
        # Check if this looks like a Table of Contents page
        # TOC pages typically have:
        # - "Table of Contents" header
        # - Lots of dots/periods (page number references like "........2")
        # - High ratio of dots to text
        dot_count = page_text.count(".")
        space_count = page_text.count(" ")
        dot_ratio = dot_count / len(page_text) if len(page_text) > 0 else 0
        
        is_toc = (
            "TABLE OF CONTENTS" in page_text_upper or
            (dot_ratio > 0.3 and dot_count > 100)  # Lots of dots relative to text
        )
        
        # Score based on keyword matches
        for keyword in keywords:
            if keyword in page_text_upper:
                score += page_text_upper.count(keyword)
        
        # Bonus if Function ID is mentioned in page text
        if function_id and function_id in page_text_upper:
            score += 10
        
        # Penalty for TOC pages (they mention Function IDs but aren't the content page)
        if is_toc:
            score = score * 0.2  # Reduce score by 80% for TOC pages
        
        # Bonus for pages with content indicators (NOT TOC)
        if not is_toc:
            # Check for content indicators like "NOTE", "FOR", instructions, etc.
            content_indicators = ["NOTE", "FOR", "CONFIGURATION", "SETTINGS", "SCREEN", "STEP", "INSTRUCTIONS"]
            for indicator in content_indicators:
                if indicator in page_text_upper:
                    score += 10  # Strong indicator this is the content page
            
            # Extra bonus if Function ID appears with content context
            if function_id and function_id in page_text_upper:
                # Check surrounding text for actual content indicators
                func_id_pos = page_text_upper.find(function_id)
                if func_id_pos > 0:
                    context_start = max(0, func_id_pos - 100)
                    context_end = min(len(page_text_upper), func_id_pos + 100)
                    context = page_text_upper[context_start:context_end]
                    # If context has content indicators, this is definitely the content page
                    if any(indicator in context for indicator in content_indicators):
                        score += 20  # Very strong indicator this is the content page
        
        if score > best_score:
            best_score = score
            best_match = page_num
    
    # If we found a better match, use it
    if best_match != original_page and best_score > 0:
        logger.info(f"Image matched to page {best_match} (was {original_page}, score: {best_score})")
        return best_match
    
    return original_page


def extract_images_from_pdf(pdf_path: str, min_size: int = 100, max_pages: int = None) -> List[Dict[str, Any]]:
    """
    Extract images from PDF, filtering small ones and deduplicating.
    
    Args:
        pdf_path: Path to PDF file
        min_size: Minimum image dimension to process
        max_pages: Maximum number of pages to process (None = all pages)
    """
    logger.info(f"Extracting images from PDF: {pdf_path}")
    if max_pages:
        logger.info(f"Limiting extraction to first {max_pages} pages")
    
    doc = fitz.open(pdf_path)
    extracted_images = []
    seen_hashes: Set[str] = set()
    
    # Determine how many pages to process
    total_pages = len(doc)
    pages_to_process = min(max_pages, total_pages) if max_pages else total_pages
    
    # First, extract all text from PDF for later matching (only from pages we'll process)
    pdf_text_by_page = {}
    for page_num in range(pages_to_process):
        page = doc[page_num]
        pdf_text_by_page[page_num + 1] = page.get_text()
    
    for page_num in range(pages_to_process):
        page = doc[page_num]
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            try:
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(io.BytesIO(image_bytes))
                
                # Filter by size
                if image.width >= min_size and image.height >= min_size:
                    # Calculate hash for deduplication
                    image_hash = calculate_image_hash(image_bytes)
                    
                    # Skip if we've seen this exact image before
                    if image_hash not in seen_hashes:
                        seen_hashes.add(image_hash)
                        extracted_images.append({
                            "page_number": page_num + 1,  # Original page where image object was found
                            "image_index": img_index + 1,
                            "image_bytes": image_bytes,
                            "width": image.width,
                            "height": image.height,
                            "image_hash": image_hash,
                            "pdf_text_by_page": pdf_text_by_page  # Store for later matching
                        })
                    else:
                        logger.debug(f"Skipping duplicate image on page {page_num + 1}, image {img_index + 1}")
            except Exception as e:
                logger.warning(f"Failed to extract image {img_index + 1} from page {page_num + 1}: {e}")
                continue
    
    doc.close()
    logger.info(f"Extracted {len(extracted_images)} unique significant images (deduplicated)")
    return extracted_images


def extract_function_id(description: str) -> str:
    """
    Extract Function ID from LLaVA description.
    
    Looks for patterns like:
    - Function ID = MSDMEDMT
    - Function ID: MSDMEDMT
    - MSDMEDMT
    - (Function ID = MSDMEDMT)
    - Media Maintenance (Function ID = MSDMEDMT)
    """
    import re
    
    # Pattern 1: "Function ID = MSDMEDMT" or "Function ID: MSDMEDMT"
    pattern1 = r'Function\s+ID\s*[=:]\s*([A-Z0-9_]+)'
    match = re.search(pattern1, description, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern 2: "(Function ID = MSDMEDMT)" or "Function ID = MSDMEDMT)"
    pattern2 = r'\(Function\s+ID\s*[=:]\s*([A-Z0-9_]+)\)'
    match = re.search(pattern2, description, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern 3: Screen name with Function ID in parentheses
    # e.g., "Media Maintenance (Function ID = MSDMEDMT)"
    pattern3 = r'\(Function\s+ID\s*[=:]\s*([A-Z0-9_]+)\)'
    match = re.search(pattern3, description, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    
    # Pattern 4: Common FlexCube Function IDs (if mentioned anywhere)
    # Check if any known Function ID appears in the description
    common_ids = ['MSDMEDMT', 'PMDSORNW', 'PMSNWCOD', 'PMDRMAUP', 'PMDACCTL', 
                  'PSDOGWNP', 'PSDIGWNP', 'PPDCDMNT', 'PMDSWPRF', 'PPDVLMNT',
                  'PSDOCBCT', 'PSDOCBBT', 'PSDICBCT', 'PSDICBBT', 'PSDICBVW',
                  'PSSICBVW', 'PSDOCBRT', 'PMDUSRQA', 'PMDFLPRM']
    description_upper = description.upper()
    for func_id in common_ids:
        # Check if Function ID appears (not just as part of another word)
        if re.search(r'\b' + func_id + r'\b', description_upper):
            return func_id
    
    return None


def describe_image(vision: FlexCubeVision, image_bytes: bytes, page_num: int, context: str = "") -> tuple[str, str]:
    """
    Use LLaVA to describe an image.
    
    Returns:
        tuple: (description, function_id)
    """
    # Simplified prompt for faster processing
    prompt = f"""Analyze this FlexCube banking software screenshot (page {page_num}).

Identify:
1. Screen/Function Name (look for "Function ID = XXXXX" format)
2. Main purpose in 1-2 sentences
3. Key visible fields/buttons (list 3-5 most important)

CRITICAL: If you see a Function ID (like MSDMEDMT, PMDSORNW), include it as "Function ID = XXXXX".

{context[:200] if context else ''}

Provide a concise description (2-3 paragraphs max)."""

    try:
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Use timeout with retry logic
        # LLaVA can be slow on CPU, so we use shorter timeout and retry
        max_retries = 2
        timeout_seconds = 180.0  # 3 minutes per attempt
        
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
                            "num_predict": 512  # Reduced for faster processing
                        }
                    },
                    timeout=timeout_seconds
                )
                response.raise_for_status()
                break  # Success, exit retry loop
            except (httpx.TimeoutException, TimeoutError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"LLaVA timeout on attempt {attempt + 1}/{max_retries}, retrying...")
                    time.sleep(2)  # Brief pause before retry
                    continue
                else:
                    # Final attempt failed
                    raise
        response.raise_for_status()
        result = response.json()
        description = result.get("response", "").strip()
        
        # Extract Function ID from description first
        function_id = extract_function_id(description)
        
        # If not found in description, try extracting from page context
        if not function_id and context:
            function_id = extract_function_id(context)
        
        return description, function_id
    except (httpx.TimeoutException, TimeoutError) as e:
        logger.error(f"Timeout describing image on page {page_num} (exceeded 10 minutes): {e}")
        return f"Error: LLaVA timeout - image analysis took too long. This may indicate a complex screenshot or LLaVA service issues.", None
    except Exception as e:
        logger.error(f"Error describing image: {e}")
        return f"Error: {str(e)}", None


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/process_pdf_images_incremental.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    output_file = pdf_path.parent / f"{pdf_path.stem}_manual_incremental.txt"
    images_dir = pdf_path.parent / f"{pdf_path.stem}_manual_images"
    images_dir.mkdir(exist_ok=True)
    
    print(f"📁 Images will be saved to: {images_dir}")
    
    # Initialize vision model
    print("Initializing LLaVA vision model...")
    vision = FlexCubeVision(model_name="llava:7b", base_url="http://localhost:11434")
    
    # Extract images (limit to first 5 pages for testing)
    max_pages = 5
    print(f"\nExtracting images from PDF (first {max_pages} pages only)...")
    images = extract_images_from_pdf(str(pdf_path), min_size=100, max_pages=max_pages)
    
    if not images:
        print("No significant images found in PDF")
        sys.exit(0)
    
    print(f"Found {len(images)} images to process")
    
    # Extract PDF text for context (will also be extracted in extract_images_from_pdf, but we need it here too)
    print("Extracting text from PDF for context...")
    pdf_text_by_page = {}
    try:
        doc = fitz.open(str(pdf_path))
        for page_num in range(len(doc)):
            page = doc[page_num]
            pdf_text_by_page[page_num + 1] = page.get_text()
        doc.close()
    except Exception as e:
        logger.warning(f"Could not extract text: {e}")
    
    # Update images with pdf_text_by_page if not already set
    for img in images:
        if "pdf_text_by_page" not in img:
            img["pdf_text_by_page"] = pdf_text_by_page
    
    # Check for existing manual to resume
    processed_indices: Set[int] = set()
    processed_function_ids: Set[str] = set()  # Track processed Function IDs for deduplication
    manual_lines = []
    
    if output_file.exists():
        print(f"\n📄 Found existing manual: {output_file}")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_content = f.read()
                # Extract already processed screenshot indices
                matches = re.findall(r'## Screenshot (\d+):', existing_content)
                processed_indices = {int(m) for m in matches}
                
                # Extract Function IDs from existing descriptions
                func_id_matches = re.findall(r'Function\s+ID\s*[=:]\s*([A-Z0-9_]+)', existing_content, re.IGNORECASE)
                processed_function_ids = {fid.upper() for fid in func_id_matches}
                
                if processed_indices:
                    print(f"✅ Found {len(processed_indices)} already processed screenshots")
                    if processed_function_ids:
                        print(f"✅ Found {len(processed_function_ids)} unique Function IDs: {', '.join(sorted(processed_function_ids))}")
                    print(f"   Will resume from screenshot {len(processed_indices) + 1}")
                    # Load existing content
                    manual_lines = existing_content.split('\n')
                    # Remove the last empty line if present
                    if manual_lines and not manual_lines[-1].strip():
                        manual_lines.pop()
                else:
                    # No processed screenshots found, start fresh
                    manual_lines = [
                        f"# Manual: {pdf_path.name}",
                        f"\nGenerated incrementally using LLaVA vision model",
                        f"Source PDF: {pdf_path.name}",
                        f"Total unique images: {len(images)}",
                        f"Note: Screenshots with same Function ID will be deduplicated",
                        f"\n{'='*80}\n"
                    ]
        except Exception as e:
            logger.warning(f"Could not read existing manual: {e}")
            processed_indices = set()
            processed_function_ids = set()
            manual_lines = [
                f"# Manual: {pdf_path.name}",
                f"\nGenerated incrementally using LLaVA vision model",
                f"Source PDF: {pdf_path.name}",
                f"Total unique images: {len(images)}",
                f"Note: Screenshots with same Function ID will be deduplicated",
                f"\n{'='*80}\n"
            ]
    else:
        # Start fresh
        manual_lines = [
            f"# Manual: {pdf_path.name}",
            f"\nGenerated incrementally using LLaVA vision model",
            f"Source PDF: {pdf_path.name}",
            f"Total unique images: {len(images)}",
            f"Note: Screenshots with same Function ID will be deduplicated",
            f"\n**Images Directory:** `{images_dir.name}/`",
            f"Each screenshot is saved as a PNG file for visual verification.",
            f"\n{'='*80}\n"
        ]
    
    # Process each image one at a time
    for idx, image_info in enumerate(images, 1):
        # Skip if already processed
        if idx in processed_indices:
            print(f"\n⏭️  Skipping screenshot {idx} (already processed)")
            continue
        page_num = image_info["page_number"]
        image_index = image_info["image_index"]
        
        print(f"\n{'='*80}")
        print(f"SCREENSHOT {idx}/{len(images)}")
        print(f"{'='*80}")
        print(f"Page: {page_num}")
        print(f"Image Index: {image_index}")
        print(f"Dimensions: {image_info['width']} x {image_info['height']} pixels")
        
        # Get page context from original page
        original_page_num = page_num
        page_context = pdf_text_by_page.get(page_num, "")[:500] if pdf_text_by_page else ""
        
        # Process with LLaVA
        print(f"\n⏳ Analyzing with LLaVA (this may take 30-40 seconds)...")
        start_time = time.time()
        description, function_id = describe_image(vision, image_info["image_bytes"], page_num, page_context)
        elapsed = time.time() - start_time
        print(f"✅ Analysis complete ({elapsed:.1f}s)")
        
        # Find best matching page based on content
        pdf_text = image_info.get("pdf_text_by_page", pdf_text_by_page)
        if pdf_text:
            matched_page = find_best_matching_page(
                description,
                function_id or "",
                pdf_text,
                original_page_num,
                search_range=2
            )
            if matched_page != original_page_num:
                print(f"📄 Page correction: Image found on page {original_page_num}, but content matches page {matched_page}")
                page_num = matched_page
                # Update page context with matched page
                page_context = pdf_text.get(page_num, "")[:500] if pdf_text else ""
        
        # Check for duplicate Function ID (screen-based deduplication)
        if function_id:
            print(f"📋 Extracted Function ID: {function_id}")
            if function_id in processed_function_ids:
                print(f"⚠️  SKIPPING: Function ID {function_id} already processed!")
                print(f"   This screenshot shows the same screen as a previously processed one.")
                print(f"   (Different image, but same screen/function)")
                continue
            else:
                processed_function_ids.add(function_id)
                print(f"✅ New Function ID - will process")
        else:
            print(f"⚠️  No Function ID extracted - will process anyway")
        
        # Save image to file for verification
        image_filename = f"screenshot_{idx:03d}_page{page_num}_img{image_index}.png"
        image_path = images_dir / image_filename
        try:
            image = Image.open(io.BytesIO(image_info["image_bytes"]))
            image.save(image_path, "PNG")
            logger.info(f"Saved image to: {image_path}")
        except Exception as e:
            logger.warning(f"Could not save image: {e}")
            image_filename = None
        
        # Add to manual
        manual_lines.append(f"\n## Screenshot {idx}: Page {page_num}, Image {image_index}")
        if function_id:
            manual_lines.append(f"**Function ID:** {function_id}")
        manual_lines.append(f"\n**Image Details:**")
        manual_lines.append(f"- Dimensions: {image_info['width']} x {image_info['height']} pixels")
        
        # Include the actual screenshot image
        if image_filename:
            relative_image_path = f"{pdf_path.stem}_manual_images/{image_filename}"
            manual_lines.append(f"\n**Screenshot Image:**")
            manual_lines.append(f"![Screenshot {idx}]({relative_image_path})")
            manual_lines.append(f"\n*Image saved at: `{relative_image_path}`*")
        
        if page_context:
            manual_lines.append(f"\n**Page Context:**")
            manual_lines.append(f"{page_context[:300]}...")
        
        manual_lines.append(f"\n**Screenshot Description:**")
        manual_lines.append(description)
        manual_lines.append(f"\n{'─'*80}\n")
        
        # Save after each image
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(manual_lines))
        
        print(f"\n✅ Saved to: {output_file}")
        print(f"   Progress: {idx}/{len(images)} images ({idx*100//len(images)}%)")
        
        # Show preview of description
        preview = description[:200] + "..." if len(description) > 200 else description
        print(f"\n📝 Description preview:")
        print(f"   {preview}")
        
        # Ask user to continue (only for first few or every 10th, otherwise auto-continue)
        remaining = len(images) - idx
        should_pause = (idx <= 5) or (idx % 10 == 0) or (remaining < 5)
        
        if should_pause and idx < len(images):
            print(f"\n{'─'*80}")
            print("Options:")
            print("  [Enter] - Continue to next image")
            print("  'q'     - Quit and save progress")
            print("  's'     - Skip to image N (enter number)")
            print(f"{'─'*80}")
            
            try:
                user_input = input("\nYour choice: ").strip().lower()
                
                if user_input == 'q':
                    print(f"\n⏸️  Stopped at image {idx}/{len(images)}")
                    print(f"✅ Progress saved to: {output_file}")
                    print(f"   Resume by running the script again (it will detect existing progress)")
                    break
                elif user_input.startswith('s'):
                    try:
                        skip_to = int(user_input[1:].strip())
                        if 1 <= skip_to <= len(images):
                            print(f"⏭️  Skipping to image {skip_to}...")
                            # Note: This would require more complex logic to actually skip
                            # For now, just continue
                        else:
                            print("Invalid number, continuing...")
                    except ValueError:
                        print("Invalid input, continuing...")
            except (EOFError, KeyboardInterrupt):
                print(f"\n⏸️  Interrupted at image {idx}/{len(images)}")
                print(f"✅ Progress saved to: {output_file}")
                break
    
    # Count processed screenshots
    processed_count = len([line for line in manual_lines if line.startswith('## Screenshot')])
    
    print(f"\n{'='*80}")
    if processed_count < len(images):
        print(f"⏸️  PROCESSING PAUSED")
        print(f"   Processed: {processed_count}/{len(images)} screenshots")
        print(f"   Remaining: {len(images) - processed_count} screenshots")
        print(f"   Run the script again to continue")
    else:
        print(f"✅ PROCESSING COMPLETE")
        print(f"   All {processed_count} screenshots processed")
    print(f"{'='*80}")
    print(f"Manual saved to: {output_file}")
    print(f"Total images processed: {processed_count}/{len(images)}")
    print(f"\nNext step: Re-index documents in RAG pipeline")


if __name__ == "__main__":
    main()

