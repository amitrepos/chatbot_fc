"""
PDF to Images Converter for Cursor Viewing

This script converts PDF pages to PNG images so they can be viewed properly in Cursor IDE.
Cursor can display images but not PDFs directly, so this provides a workaround.

Usage:
    python scripts/pdf_to_images_viewer.py "path/to/file.pdf"
    python scripts/pdf_to_images_viewer.py "path/to/file.pdf" --output-dir "custom/output"
    python scripts/pdf_to_images_viewer.py "path/to/file.pdf" --dpi 200
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
from PIL import Image
import io
from loguru import logger

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")


class PDFToImageConverter:
    """
    Converts PDF pages to PNG images for viewing in Cursor IDE.
    
    Cursor IDE can display images but shows PDFs as raw binary data.
    This converter creates image files that can be viewed properly.
    """
    
    def __init__(self, output_dir: Optional[str] = None, dpi: int = 150):
        """
        Initialize PDF to image converter.
        
        Args:
            output_dir: Custom output directory (default: creates folder next to PDF)
            dpi: Resolution for image conversion (default: 150, higher = better quality but larger files)
        """
        self.dpi = dpi
        self.output_dir = output_dir
    
    def convert_pdf_to_images(self, pdf_path: str) -> Path:
        """
        Convert all pages of a PDF to PNG images.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Path to output directory containing images
        """
        pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not pdf_path.suffix.lower() == '.pdf':
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        logger.info(f"Opening PDF: {pdf_path}")
        
        # Determine output directory
        if self.output_dir:
            output_dir = Path(self.output_dir)
        else:
            # Create directory next to PDF with _images suffix
            output_dir = pdf_path.parent / f"{pdf_path.stem}_images"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        
        # Open PDF
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            logger.info(f"PDF has {total_pages} page(s)")
            
            # Convert each page to image
            for page_num in range(total_pages):
                page = doc[page_num]
                
                # Render page to image (pixmap)
                # Scale factor: dpi / 72 (PDF default is 72 DPI)
                zoom = self.dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                
                # Save image
                image_filename = f"page_{page_num + 1:03d}.png"
                image_path = output_dir / image_filename
                image.save(image_path, "PNG", optimize=True)
                
                logger.info(f"  ✓ Page {page_num + 1}/{total_pages} → {image_path.name} ({image.width}x{image.height}px)")
            
            doc.close()
            
            logger.info(f"\n✅ Conversion complete!")
            logger.info(f"📁 Images saved to: {output_dir}")
            logger.info(f"📄 Total pages converted: {total_pages}")
            
            return output_dir
            
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            raise


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Convert PDF pages to PNG images for viewing in Cursor IDE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert PDF to images (default settings)
  python scripts/pdf_to_images_viewer.py "data/documents/file.pdf"
  
  # Custom output directory
  python scripts/pdf_to_images_viewer.py "file.pdf" --output-dir "output/images"
  
  # Higher resolution (300 DPI)
  python scripts/pdf_to_images_viewer.py "file.pdf" --dpi 300
        """
    )
    
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to PDF file to convert"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom output directory (default: creates folder next to PDF with _images suffix)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Resolution for image conversion (default: 150, higher = better quality but larger files)"
    )
    
    args = parser.parse_args()
    
    try:
        converter = PDFToImageConverter(output_dir=args.output_dir, dpi=args.dpi)
        output_dir = converter.convert_pdf_to_images(args.pdf_path)
        
        print(f"\n💡 Tip: Open the PNG images in Cursor to view the PDF content visually!")
        print(f"   Images are located at: {output_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to convert PDF: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


