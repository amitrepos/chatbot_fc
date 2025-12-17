"""
Vision Module for FlexCube AI Assistant

This module provides integration with LLaVA vision model via Ollama
for analyzing FlexCube screenshots and extracting error information.

The vision pipeline:
1. Accepts an image (screenshot)
2. Sends to LLaVA for analysis
3. Extracts: error codes, error messages, screen names, context
4. Returns structured information for RAG query
"""

import base64
import httpx
from typing import Optional, Dict, Any
from loguru import logger
from pathlib import Path


class FlexCubeVision:
    """
    Vision module for analyzing FlexCube screenshots.
    
    Uses LLaVA model via Ollama to extract error information
    from FlexCube application screenshots.
    """
    
    def __init__(
        self,
        model_name: str = "llava:7b",
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0
    ):
        """
        Initialize the vision module.
        
        Args:
            model_name: LLaVA model name in Ollama
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
        """
        self.model_name = model_name
        self.base_url = base_url
        self.client = httpx.Client(timeout=timeout)
        
        logger.info(f"Initialized FlexCube Vision: {model_name} at {base_url}")
    
    def encode_image(self, image_data: bytes) -> str:
        """
        Encode image bytes to base64 string.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(image_data).decode('utf-8')
    
    def encode_image_file(self, file_path: str) -> str:
        """
        Read and encode an image file to base64.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Base64 encoded string
        """
        with open(file_path, 'rb') as f:
            return self.encode_image(f.read())
    
    def analyze_screenshot(
        self,
        image_data: bytes,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a FlexCube screenshot and extract error information.
        
        This method sends the image to LLaVA with a specialized prompt
        designed to extract FlexCube-specific information.
        
        Args:
            image_data: Raw image bytes (PNG, JPG, etc.)
            additional_context: Optional user-provided context about the error
            
        Returns:
            dict: Extracted information including:
                - error_code: Extracted error code (if any)
                - error_message: Full error message
                - screen_name: FlexCube screen/module name
                - description: General description of what's shown
                - suggested_query: Suggested query for RAG search
        """
        logger.info("Analyzing FlexCube screenshot with LLaVA")
        
        # Encode the image
        image_base64 = self.encode_image(image_data)
        
        # Create the extraction prompt
        prompt = self._create_extraction_prompt(additional_context)
        
        try:
            # Call LLaVA via Ollama API
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "images": [image_base64],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for factual extraction
                        "num_predict": 1024
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            
            raw_response = result.get("response", "")
            logger.debug(f"LLaVA raw response: {raw_response[:500]}...")
            
            # Parse the response to extract structured information
            extracted = self._parse_extraction_response(raw_response)
            
            logger.info(f"Extracted from screenshot: error_code={extracted.get('error_code')}, "
                       f"screen={extracted.get('screen_name')}")
            
            return extracted
            
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            raise
    
    def _create_extraction_prompt(self, additional_context: Optional[str] = None) -> str:
        """
        Create the prompt for LLaVA to extract error information.
        
        Args:
            additional_context: Optional user-provided context
            
        Returns:
            Formatted prompt string
        """
        base_prompt = """You are analyzing a screenshot from Oracle FlexCube banking software.

Please examine this screenshot carefully and extract the following information:

1. ERROR CODE: Look for any error code (usually in format like ERR_XXX_XXX, ORA-XXXXX, or similar)
2. ERROR MESSAGE: The full error message text shown on screen
3. SCREEN NAME: The name of the FlexCube screen or module (usually shown in the title bar or header)
4. DESCRIPTION: Brief description of what the screenshot shows
5. SUGGESTED QUERY: A search query to find help for this issue in documentation

Please respond in the following format:
ERROR_CODE: [extracted error code or "None found"]
ERROR_MESSAGE: [full error message or "None found"]
SCREEN_NAME: [screen/module name or "Unknown"]
DESCRIPTION: [brief description]
SUGGESTED_QUERY: [suggested search query for documentation]

Be precise and extract exact text from the image. If you cannot find certain information, indicate "None found" or "Unknown"."""

        if additional_context:
            base_prompt += f"\n\nAdditional context from user: {additional_context}"
        
        return base_prompt
    
    def _parse_extraction_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLaVA's response into structured data.
        
        Args:
            response: Raw text response from LLaVA
            
        Returns:
            dict: Parsed extraction results
        """
        result = {
            "error_code": None,
            "error_message": None,
            "screen_name": None,
            "description": None,
            "suggested_query": None,
            "raw_response": response
        }
        
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("ERROR_CODE:"):
                value = line.replace("ERROR_CODE:", "").strip()
                if value.lower() not in ["none found", "none", "n/a", ""]:
                    result["error_code"] = value
                    
            elif line.startswith("ERROR_MESSAGE:"):
                value = line.replace("ERROR_MESSAGE:", "").strip()
                if value.lower() not in ["none found", "none", "n/a", ""]:
                    result["error_message"] = value
                    
            elif line.startswith("SCREEN_NAME:"):
                value = line.replace("SCREEN_NAME:", "").strip()
                if value.lower() not in ["unknown", "none", "n/a", ""]:
                    result["screen_name"] = value
                    
            elif line.startswith("DESCRIPTION:"):
                value = line.replace("DESCRIPTION:", "").strip()
                if value:
                    result["description"] = value
                    
            elif line.startswith("SUGGESTED_QUERY:"):
                value = line.replace("SUGGESTED_QUERY:", "").strip()
                if value:
                    result["suggested_query"] = value
        
        # If no suggested query was extracted, create one from available info
        if not result["suggested_query"]:
            result["suggested_query"] = self._create_fallback_query(result)
        
        return result
    
    def _create_fallback_query(self, extracted: Dict[str, Any]) -> str:
        """
        Create a fallback search query from extracted information.
        
        Args:
            extracted: Dictionary of extracted information
            
        Returns:
            Search query string
        """
        parts = []
        
        if extracted.get("error_code"):
            parts.append(extracted["error_code"])
        
        if extracted.get("error_message"):
            # Take first 50 chars of error message
            msg = extracted["error_message"][:50]
            parts.append(msg)
        
        if extracted.get("screen_name"):
            parts.append(extracted["screen_name"])
        
        if parts:
            return " ".join(parts)
        
        # If nothing extracted, use description
        if extracted.get("description"):
            return extracted["description"][:100]
        
        return "FlexCube error"
    
    def create_rag_query(self, extracted: Dict[str, Any]) -> str:
        """
        Create an optimized query for the RAG pipeline based on extracted info.
        
        Args:
            extracted: Dictionary from analyze_screenshot()
            
        Returns:
            Query string optimized for RAG search
        """
        query_parts = []
        
        # Start with error code if available (most specific)
        if extracted.get("error_code"):
            query_parts.append(f"Error {extracted['error_code']}")
        
        # Add error message context
        if extracted.get("error_message"):
            query_parts.append(extracted["error_message"])
        
        # Add screen context
        if extracted.get("screen_name"):
            query_parts.append(f"in {extracted['screen_name']}")
        
        # Combine into a natural question
        if query_parts:
            base_query = " ".join(query_parts)
            return f"How do I resolve {base_query}?"
        
        # Fallback to suggested query
        if extracted.get("suggested_query"):
            return extracted["suggested_query"]
        
        # Last resort
        return "FlexCube error troubleshooting"
    
    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()


# Factory function for easy instantiation
def create_vision_module(
    model_name: str = "llava:7b",
    base_url: str = "http://localhost:11434"
) -> FlexCubeVision:
    """
    Create a FlexCubeVision instance.
    
    Args:
        model_name: LLaVA model name
        base_url: Ollama API URL
        
    Returns:
        FlexCubeVision instance
    """
    return FlexCubeVision(model_name=model_name, base_url=base_url)


