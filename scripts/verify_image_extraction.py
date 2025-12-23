"""
Verify image extraction by checking which images are actually on each page
and comparing with what was extracted.
"""

import sys
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
import io
import hashlib

def get_image_hash(image_bytes: bytes) -> str:
    """Get hash of image for comparison."""
    return hashlib.md5(image_bytes).hexdigest()

def analyze_page_images(pdf_path: str, page_num: int, save_dir: Path = None):
    """Analyze images on a specific page."""
    print(f"\n{'='*80}")
    print(f"Analyzing Page {page_num} of: {pdf_path}")
    print(f"{'='*80}\n")
    
    doc = fitz.open(pdf_path)
    if page_num > len(doc):
        print(f"Error: Page {page_num} doesn't exist (PDF has {len(doc)} pages)")
        doc.close()
        return
    
    page = doc[page_num - 1]  # 0-indexed
    image_list = page.get_images(full=True)
    
    print(f"Found {len(image_list)} image objects on page {page_num}\n")
    
    # Extract text context
    text = page.get_text()
    print(f"Page text (first 300 chars):")
    print(text[:300])
    print("\n" + "-"*80 + "\n")
    
    # Analyze each image
    unique_images = {}
    for img_index, img in enumerate(image_list):
        try:
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))
            
            # Get hash
            img_hash = get_image_hash(image_bytes)
            
            # Get position
            image_rects = page.get_image_rects(xref)
            bbox = None
            if image_rects:
                rect = image_rects[0]
                bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
            
            # Store unique images
            if img_hash not in unique_images:
                unique_images[img_hash] = {
                    'count': 1,
                    'width': image.width,
                    'height': image.height,
                    'bbox': bbox,
                    'xref': xref,
                    'image_bytes': image_bytes
                }
            else:
                unique_images[img_hash]['count'] += 1
            
            # Save first few unique images for inspection
            if len(unique_images) <= 3 and save_dir:
                if img_hash not in [u.get('saved') for u in unique_images.values()]:
                    save_path = save_dir / f"page{page_num}_img{img_index+1}_hash{img_hash[:8]}.png"
                    image.save(save_path, "PNG")
                    unique_images[img_hash]['saved'] = True
                    print(f"Saved: {save_path}")
            
        except Exception as e:
            print(f"Error extracting image {img_index + 1}: {e}")
    
    print(f"\nUnique images found: {len(unique_images)}")
    print("Image details:")
    for idx, (img_hash, info) in enumerate(unique_images.items(), 1):
        print(f"  Image {idx}:")
        print(f"    Hash: {img_hash[:16]}...")
        print(f"    Size: {info['width']}x{info['height']} pixels")
        print(f"    Count: {info['count']} (appears {info['count']} times on page)")
        if info.get('bbox'):
            print(f"    Position: {info['bbox']}")
    
    doc.close()
    return unique_images


def compare_with_extracted_screenshots():
    """Compare page images with extracted screenshots."""
    base_dir = Path("/var/www/chatbot_FC/data/documents")
    full_pdf = base_dir / "Generic Wire ISO  MX_v2.pdf"
    screenshots_dir = base_dir / "Generic Wire ISO  MX_v2_manual_images"
    
    print("\n" + "="*80)
    print("COMPARING WITH EXTRACTED SCREENSHOTS")
    print("="*80)
    
    # Check extracted screenshots
    if screenshots_dir.exists():
        screenshot_files = list(screenshots_dir.glob("screenshot_*.png"))
        print(f"\nFound {len(screenshot_files)} extracted screenshots")
        
        # Parse screenshot filenames
        for screenshot_file in sorted(screenshot_files)[:3]:  # First 3
            name = screenshot_file.name
            # Format: screenshot_001_page1_img1.png
            parts = name.replace('.png', '').split('_')
            if len(parts) >= 4:
                page_num = int(parts[2].replace('page', ''))
                img_index = int(parts[3].replace('img', ''))
                print(f"\n  {name}:")
                print(f"    Reported as: Page {page_num}, Image {img_index}")
    
    # Analyze pages 1 and 2 of full PDF
    save_dir = base_dir / "diagnostic_images"
    save_dir.mkdir(exist_ok=True)
    
    print("\n\nAnalyzing Page 1 (Table of Contents):")
    page1_images = analyze_page_images(str(full_pdf), 1, save_dir)
    
    print("\n\nAnalyzing Page 2 (Media Maintenance):")
    page2_images = analyze_page_images(str(full_pdf), 2, save_dir)
    
    # Check if images match
    if page1_images and page2_images:
        page1_hashes = set(page1_images.keys())
        page2_hashes = set(page2_images.keys())
        
        print("\n\n" + "="*80)
        print("COMPARISON")
        print("="*80)
        print(f"Page 1 unique images: {len(page1_hashes)}")
        print(f"Page 2 unique images: {len(page2_hashes)}")
        print(f"Common images: {len(page1_hashes & page2_hashes)}")
        print(f"Page 1 only: {len(page1_hashes - page2_hashes)}")
        print(f"Page 2 only: {len(page2_hashes - page1_hashes)}")


if __name__ == "__main__":
    compare_with_extracted_screenshots()


