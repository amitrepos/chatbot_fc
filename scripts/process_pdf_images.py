"""
Script to Extract Images from PDF and Generate Text-Based Manual

This script:
1. Extracts all images from a PDF file
2. Uses LLaVA vision model to describe each screenshot in detail
3. Creates a comprehensive text-based manual
4. Saves the manual as a new document for RAG indexing

Usage:
    python scripts/process_pdf_images.py "data/documents/Generic Wire ISO  MX_v2.pdf"
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF
from PIL import Image
import io
import base64
import httpx
from loguru import logger
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag.vision import FlexCubeVision


class PDFImageProcessor:
    """
    Processes PDF files to extract images and generate text descriptions.
    """
    
    def __init__(
        self,
        vision_model: FlexCubeVision,
        output_dir: str = "/var/www/chatbot_FC/data/documents"
    ):
        """
        Initialize PDF image processor.
        
        Args:
            vision_model: FlexCubeVision instance for image analysis
            output_dir: Directory to save generated manual
        """
        self.vision = vision_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PDF Image Processor initialized. Output directory: {output_dir}")
    
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract all images from a PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of dictionaries containing:
                - page_number: Page number (1-indexed)
                - image_index: Image index on page
                - image_data: PIL Image object
                - bbox: Bounding box (x0, y0, x1, y1)
        """
        logger.info(f"Extracting images from PDF: {pdf_path}")
        
        doc = fitz.open(pdf_path)
        extracted_images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                try:
                    # Get image data
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    
                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(image_bytes))
                    
                    # Get image position on page
                    image_rects = page.get_image_rects(xref)
                    bbox = None
                    if image_rects:
                        rect = image_rects[0]
                        bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
                    
                    extracted_images.append({
                        "page_number": page_num + 1,  # 1-indexed
                        "image_index": img_index + 1,
                        "image_data": image,
                        "image_bytes": image_bytes,
                        "bbox": bbox,
                        "width": image.width,
                        "height": image.height
                    })
                    
                    logger.debug(f"Extracted image {img_index + 1} from page {page_num + 1} "
                               f"({image.width}x{image.height})")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract image {img_index + 1} from page {page_num + 1}: {e}")
                    continue
        
        doc.close()
        logger.info(f"Extracted {len(extracted_images)} images from PDF")
        return extracted_images
    
    def describe_screenshot(
        self,
        image_bytes: bytes,
        page_number: int,
        context: str = ""
    ) -> str:
        """
        Use LLaVA to describe a screenshot in detail.
        
        Args:
            image_bytes: Raw image bytes
            page_number: Page number for context
            context: Additional context about the image
            
        Returns:
            Detailed description of the screenshot
        """
        # Create a specialized prompt for describing FlexCube screenshots
        prompt = f"""You are analyzing a screenshot from a FlexCube banking software manual (page {page_number}).

This screenshot shows a FlexCube screen, configuration, or process flow. Please provide a DETAILED description that includes:

1. **Screen/Function Name**: What screen or function is shown? (Look for Function ID, screen titles, headers)
2. **Purpose**: What is this screen used for? What does it allow users to do?
3. **Key Fields**: List the important fields, buttons, tabs, or sections visible
4. **Configuration Details**: What settings, preferences, or configurations are shown?
5. **Step-by-Step Context**: If this is part of a process, describe the steps shown
6. **Important Notes**: Any warnings, notes, or special instructions visible
7. **Visual Layout**: Describe the layout, sections, and organization of the screen

Be thorough and descriptive. This description will be used to help users understand how to use FlexCube screens.

{context if context else ''}

Provide your description in clear, structured paragraphs."""

        try:
            # Use the vision model to analyze the image
            result = self.vision.analyze_screenshot(
                image_data=image_bytes,
                additional_context=context
            )
            
            # Build comprehensive description
            description_parts = []
            
            if result.get("screen_name"):
                description_parts.append(f"**Screen/Function:** {result['screen_name']}")
            
            if result.get("description"):
                description_parts.append(f"**Description:** {result['description']}")
            
            # Get detailed description from LLaVA
            # We'll make a direct call for more detailed analysis
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            response = self.vision.client.post(
                f"{self.vision.base_url}/api/generate",
                json={
                    "model": self.vision.model_name,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Low temperature for factual descriptions
                        "num_predict": 2048  # Allow longer descriptions
                    }
                }
            )
            response.raise_for_status()
            result_data = response.json()
            detailed_description = result_data.get("response", "").strip()
            
            if detailed_description:
                description_parts.append(f"\n**Detailed Analysis:**\n{detailed_description}")
            
            return "\n\n".join(description_parts) if description_parts else "No description available"
            
        except Exception as e:
            logger.error(f"Error describing screenshot: {e}")
            return f"Error generating description: {str(e)}"
    
    def process_pdf(
        self,
        pdf_path: str,
        output_filename: str = None,
        min_image_size: int = 100
    ) -> str:
        """
        Process a PDF file: extract images, describe them, and create a manual.
        
        Args:
            pdf_path: Path to PDF file
            output_filename: Output filename (default: {pdf_name}_manual.txt)
            min_image_size: Minimum image dimension to process (filters out small icons)
            
        Returns:
            Path to generated manual file
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract images
        images = self.extract_images_from_pdf(str(pdf_path))
        
        # Filter out very small images (likely icons, not screenshots)
        filtered_images = [
            img for img in images
            if img["width"] >= min_image_size and img["height"] >= min_image_size
        ]
        
        logger.info(f"Filtered to {len(filtered_images)} significant images "
                   f"(removed {len(images) - len(filtered_images)} small images/icons)")
        
        if not filtered_images:
            logger.warning("No significant images found in PDF")
            return None
        
        # Generate output filename
        if not output_filename:
            output_filename = f"{pdf_path.stem}_manual.txt"
        
        output_path = self.output_dir / output_filename
        
        # Process each image and build manual
        manual_content = []
        manual_content.append(f"# Manual: {pdf_path.name}")
        manual_content.append(f"\nGenerated from PDF screenshots using LLaVA vision model")
        manual_content.append(f"Source PDF: {pdf_path.name}")
        manual_content.append(f"Total screenshots processed: {len(filtered_images)}")
        manual_content.append(f"\n{'='*80}\n")
        
        # Also extract text from PDF for context
        try:
            import fitz
            doc = fitz.open(str(pdf_path))
            pdf_text_by_page = {}
            for page_num in range(len(doc)):
                page = doc[page_num]
                pdf_text_by_page[page_num + 1] = page.get_text()
            doc.close()
        except Exception as e:
            logger.warning(f"Could not extract text from PDF: {e}")
            pdf_text_by_page = {}
        
        # Check for existing progress file
        progress_file = output_path.with_suffix('.progress')
        processed_indices = set()
        
        if progress_file.exists():
            logger.info(f"Found existing progress file: {progress_file}")
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract already processed indices
                    import re
                    matches = re.findall(r'## Screenshot (\d+):', content)
                    processed_indices = {int(m) for m in matches}
                    logger.info(f"Resuming from image {len(processed_indices) + 1}/{len(filtered_images)}")
                    # Load existing content
                    manual_content = [content]
            except Exception as e:
                logger.warning(f"Could not read progress file: {e}")
                processed_indices = set()
        
        # Process each image incrementally
        for idx, image_info in enumerate(filtered_images, 1):
            # Skip if already processed
            if idx in processed_indices:
                logger.info(f"Skipping already processed image {idx}/{len(filtered_images)}")
                continue
            
            page_num = image_info["page_number"]
            image_index = image_info["image_index"]
            
            logger.info(f"Processing image {idx}/{len(filtered_images)} "
                       f"(Page {page_num}, Image {image_index})")
            print(f"\n{'='*60}")
            print(f"Processing Screenshot {idx}/{len(filtered_images)}")
            print(f"Page {page_num}, Image {image_index}")
            print(f"{'='*60}")
            
            # Get text context from the page
            page_context = ""
            if page_num in pdf_text_by_page:
                page_text = pdf_text_by_page[page_num]
                # Extract relevant text around the image (first 500 chars)
                page_context = page_text[:500] if page_text else ""
            
            # Describe the screenshot
            try:
                description = self.describe_screenshot(
                    image_bytes=image_info["image_bytes"],
                    page_number=page_num,
                    context=page_context
                )
            except Exception as e:
                logger.error(f"Error describing screenshot {idx}: {e}")
                description = f"Error generating description: {str(e)}"
            
            # Add to manual
            new_content = []
            new_content.append(f"\n## Screenshot {idx}: Page {page_num}, Image {image_index}")
            new_content.append(f"\n**Image Details:**")
            new_content.append(f"- Dimensions: {image_info['width']} x {image_info['height']} pixels")
            if image_info.get('bbox'):
                new_content.append(f"- Position on page: {image_info['bbox']}")
            
            # Add page text context if available
            if page_context:
                new_content.append(f"\n**Page Context:**")
                new_content.append(f"{page_context[:300]}...")
            
            new_content.append(f"\n**Screenshot Description:**")
            new_content.append(description)
            new_content.append(f"\n{'─'*80}\n")
            
            # Append to manual content
            manual_content.extend(new_content)
            
            # Save incrementally after each image
            manual_text = "\n".join(manual_content)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(manual_text)
            
            # Also save progress file
            with open(progress_file, 'w', encoding='utf-8') as f:
                f.write(manual_text)
            
            print(f"✅ Saved progress: {idx}/{len(filtered_images)} images processed")
            print(f"   Manual file: {output_path}")
            print(f"   Progress file: {progress_file}")
            
            # Ask user if they want to continue (only for first few, then auto-continue)
            if idx < 5 or idx % 10 == 0:
                print(f"\n⏸️  Paused after image {idx}")
                print("Press Enter to continue to next image, or 'q' to quit and resume later...")
                try:
                    user_input = input().strip().lower()
                    if user_input == 'q':
                        print(f"\n⏸️  Stopped at image {idx}/{len(filtered_images)}")
                        print(f"   Progress saved. Resume by running the script again.")
                        return str(output_path)
                except (EOFError, KeyboardInterrupt):
                    print(f"\n⏸️  Interrupted at image {idx}/{len(filtered_images)}")
                    print(f"   Progress saved. Resume by running the script again.")
                    return str(output_path)
            else:
                # Small delay for other images
                time.sleep(0.5)
        
        # Clean up progress file when done
        if progress_file.exists():
            progress_file.unlink()
            logger.info("Removed progress file (processing complete)")
        
        # Final write (in case of any issues)
        manual_text = "\n".join(manual_content)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(manual_text)
        
        logger.info(f"Manual generated: {output_path}")
        logger.info(f"Manual size: {len(manual_text)} characters")
        logger.info(f"Total images processed: {len(filtered_images)}")
        
        return str(output_path)


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/process_pdf_images.py <pdf_path> [output_filename]")
        print("\nExample:")
        print('  python scripts/process_pdf_images.py "data/documents/Generic Wire ISO  MX_v2.pdf"')
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_filename = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Initialize vision model
    logger.info("Initializing LLaVA vision model...")
    vision = FlexCubeVision(
        model_name="llava:7b",
        base_url="http://localhost:11434"
    )
    
    # Process PDF
    processor = PDFImageProcessor(vision_model=vision)
    
    try:
        output_path = processor.process_pdf(
            pdf_path=pdf_path,
            output_filename=output_filename
        )
        
        if output_path:
            print(f"\n✅ Success! Manual generated: {output_path}")
            print(f"\nNext steps:")
            print(f"1. Review the manual: {output_path}")
            print(f"2. Re-index documents in RAG pipeline to include the new manual")
        else:
            print("\n⚠️  No images found in PDF or processing failed")
            
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

