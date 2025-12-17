"""
Query Expander Module

This module provides semantic query expansion to improve RAG retrieval.
It uses the LLM to generate synonyms, related terms, and alternative 
phrasings before vector search - dramatically improving recall for 
semantically similar but lexically different content.

Example:
    "How many users logged in?" 
    → Expands to include: "user sign-ins", "authentication count", 
      "connected users", "login statistics", "active sessions"
"""

import re
from typing import List, Dict, Optional, Tuple
from loguru import logger

from .ollama_llm import OllamaLLM


class QueryExpander:
    """
    Expands user queries with synonyms and semantically related phrases.
    
    Uses Mistral LLM to intelligently generate alternative query formulations
    that capture the same intent but with different vocabulary. This bridges
    the semantic gap between user questions and document content.
    """
    
    def __init__(
        self,
        llm: OllamaLLM,
        max_expansions: int = 5,
        include_original: bool = True
    ):
        """
        Initialize query expander.
        
        Args:
            llm: OllamaLLM instance for generating expansions
            max_expansions: Maximum number of expanded queries to generate
            include_original: Whether to include original query in output
        """
        self._llm = llm
        self._max_expansions = max_expansions
        self._include_original = include_original
        
        logger.info(f"QueryExpander initialized (max_expansions={max_expansions})")
    
    def expand(self, question: str) -> Dict[str, any]:
        """
        Expand a user question into multiple semantically equivalent queries.
        
        Args:
            question: Original user question
            
        Returns:
            Dict containing:
                - original: The original question
                - expanded_queries: List of semantically related queries
                - combined_query: Single optimized query for embedding
                - key_terms: Extracted key concepts and their synonyms
        """
        logger.info(f"Expanding query: {question[:80]}...")
        
        # Step 1: Generate expanded queries using LLM
        expansion_prompt = self._build_expansion_prompt(question)
        
        try:
            response = self._llm.complete(expansion_prompt)
            raw_output = str(response.text).strip()
            logger.debug(f"LLM expansion response: {raw_output[:500]}")
            
            # Step 2: Parse LLM output into structured data
            parsed = self._parse_expansion_output(raw_output, question)
            
            # Step 3: Build combined query for single-vector search
            combined_query = self._build_combined_query(
                question, 
                parsed['expanded_queries'],
                parsed['key_terms']
            )
            
            result = {
                'original': question,
                'expanded_queries': parsed['expanded_queries'][:self._max_expansions],
                'combined_query': combined_query,
                'key_terms': parsed['key_terms']
            }
            
            logger.info(f"Query expanded: {len(result['expanded_queries'])} variations generated")
            return result
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            # Fallback: return original query only
            return {
                'original': question,
                'expanded_queries': [],
                'combined_query': question,
                'key_terms': {}
            }
    
    def _build_expansion_prompt(self, question: str) -> str:
        """
        Build prompt for LLM to generate query expansions.
        
        The prompt instructs the LLM to:
        1. Identify key terms in the question
        2. Generate synonyms for each key term
        3. Create alternative phrasings of the full question
        """
        return f"""You are a search query expansion expert. Your task is to help improve search results by generating synonyms and alternative phrasings.

ORIGINAL QUESTION: {question}

Generate search query expansions following this EXACT format:

KEY_TERMS:
- term1: synonym1, synonym2, synonym3
- term2: synonym1, synonym2, synonym3

ALTERNATIVE_QUERIES:
1. [first alternative phrasing]
2. [second alternative phrasing]
3. [third alternative phrasing]
4. [fourth alternative phrasing]
5. [fifth alternative phrasing]

Rules:
- Focus on semantically equivalent terms (e.g., "logged in" → "signed in", "authenticated", "connected")
- Include domain-specific variations (e.g., "users" → "accounts", "sessions", "clients")
- Keep the same intent/meaning as the original
- For banking/financial context, include industry terms
- Generate exactly 5 alternative queries
- Be concise - no explanations needed

OUTPUT:"""

    def _parse_expansion_output(self, output: str, original_question: str) -> Dict:
        """
        Parse LLM output into structured expansion data.
        
        Args:
            output: Raw LLM response text
            original_question: Original question for fallback
            
        Returns:
            Dict with 'expanded_queries' and 'key_terms'
        """
        result = {
            'expanded_queries': [],
            'key_terms': {}
        }
        
        lines = output.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers
            if 'KEY_TERMS' in line.upper() or 'KEY TERMS' in line.upper():
                current_section = 'terms'
                continue
            elif 'ALTERNATIVE' in line.upper() or 'QUERIES' in line.upper():
                current_section = 'queries'
                continue
            
            # Parse key terms section
            if current_section == 'terms' and ':' in line:
                line_clean = line.lstrip('- •')
                parts = line_clean.split(':', 1)
                if len(parts) == 2:
                    term = parts[0].strip().lower()
                    synonyms = [s.strip() for s in parts[1].split(',') if s.strip()]
                    if term and synonyms:
                        result['key_terms'][term] = synonyms
            
            # Parse alternative queries section
            elif current_section == 'queries':
                # Remove numbering like "1.", "2)", "-", etc.
                query = re.sub(r'^[\d]+[.\)]\s*', '', line)
                query = query.lstrip('- •').strip()
                # Remove brackets if present
                query = query.strip('[]')
                if query and len(query) > 5:  # Avoid too short fragments
                    result['expanded_queries'].append(query)
        
        # Fallback: if parsing failed, try simple extraction
        if not result['expanded_queries']:
            # Look for any sentence-like structures
            sentences = re.findall(r'[A-Z][^.!?]*[.!?]', output)
            for sent in sentences[:5]:
                if len(sent) > 10:
                    result['expanded_queries'].append(sent.strip())
        
        # Always ensure we have at least the original
        if not result['expanded_queries']:
            result['expanded_queries'] = [original_question]
        
        return result
    
    def _build_combined_query(
        self, 
        original: str, 
        expanded: List[str],
        key_terms: Dict[str, List[str]]
    ) -> str:
        """
        Build a single combined query optimized for embedding.
        
        This creates a dense query string that captures the semantic
        essence of both the original and all expansions, suitable for
        single-vector retrieval.
        
        Args:
            original: Original question
            expanded: List of expanded queries
            key_terms: Dictionary of terms and their synonyms
            
        Returns:
            Combined query string
        """
        # Start with original question
        parts = [original]
        
        # Add unique words from expansions (avoid exact duplicates)
        seen_words = set(original.lower().split())
        
        for exp_query in expanded[:3]:  # Use top 3 expansions
            new_words = []
            for word in exp_query.split():
                word_lower = word.lower().strip('.,!?')
                if word_lower not in seen_words and len(word_lower) > 2:
                    new_words.append(word)
                    seen_words.add(word_lower)
            if new_words:
                parts.append(' '.join(new_words))
        
        # Add key synonym terms
        for term, synonyms in key_terms.items():
            for syn in synonyms[:2]:  # Top 2 synonyms per term
                if syn.lower() not in seen_words:
                    parts.append(syn)
                    seen_words.add(syn.lower())
        
        # Join all parts - this creates a semantically rich query
        combined = ' '.join(parts)
        
        # Limit length to avoid embedding truncation (most models: 512 tokens)
        words = combined.split()
        if len(words) > 100:
            combined = ' '.join(words[:100])
        
        logger.debug(f"Combined query ({len(combined)} chars): {combined[:200]}...")
        return combined


class MultiQueryRetriever:
    """
    Retrieves documents using multiple query variations.
    
    Instead of embedding a single query, this retrieves for each
    expanded query separately and merges/deduplicates results.
    Provides better recall at the cost of more retrieval calls.
    """
    
    def __init__(
        self,
        base_retriever,
        query_expander: QueryExpander,
        top_k_per_query: int = 3,
        final_top_k: int = 7
    ):
        """
        Initialize multi-query retriever.
        
        Args:
            base_retriever: LlamaIndex VectorIndexRetriever
            query_expander: QueryExpander instance
            top_k_per_query: Results to fetch per expanded query
            final_top_k: Final number of unique results to return
        """
        self._base_retriever = base_retriever
        self._query_expander = query_expander
        self._top_k_per_query = top_k_per_query
        self._final_top_k = final_top_k
        
        logger.info(f"MultiQueryRetriever initialized (top_k_per_query={top_k_per_query}, final={final_top_k})")
    
    def retrieve(self, question: str) -> List:
        """
        Retrieve documents using expanded queries.
        
        Args:
            question: Original user question
            
        Returns:
            List of retrieved nodes, deduplicated and re-ranked
        """
        # Step 1: Expand the query
        expansion = self._query_expander.expand(question)
        
        # Step 2: Collect all queries to run
        all_queries = [expansion['original']]
        all_queries.extend(expansion['expanded_queries'])
        
        # Step 3: Retrieve for each query
        all_nodes = []
        seen_node_ids = set()
        
        # Temporarily adjust base retriever's top_k
        original_top_k = self._base_retriever.similarity_top_k
        self._base_retriever.similarity_top_k = self._top_k_per_query
        
        try:
            for query in all_queries[:6]:  # Limit to 6 queries max
                logger.debug(f"Retrieving for: {query[:60]}...")
                
                nodes = self._base_retriever.retrieve(query)
                
                for node in nodes:
                    # Deduplicate by node ID
                    node_id = getattr(node, 'node_id', None) or id(node)
                    if node_id not in seen_node_ids:
                        all_nodes.append(node)
                        seen_node_ids.add(node_id)
        finally:
            # Restore original top_k
            self._base_retriever.similarity_top_k = original_top_k
        
        # Step 4: Sort by score and return top results
        all_nodes.sort(key=lambda n: getattr(n, 'score', 0) or 0, reverse=True)
        
        logger.info(f"MultiQuery retrieved {len(all_nodes)} unique nodes, returning top {self._final_top_k}")
        return all_nodes[:self._final_top_k]
    
    def get_expansion_details(self, question: str) -> Dict:
        """
        Get expansion details for debugging/display.
        
        Args:
            question: Original question
            
        Returns:
            Dict with original, expanded_queries, combined_query, key_terms
        """
        return self._query_expander.expand(question)

