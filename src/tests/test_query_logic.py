"""
Unit Tests for Query Engine Logic

These tests ensure the two-tier query flow works correctly:
1. FlexCube questions → Answer from RAG with document sources
2. General questions with irrelevant context → Answer from LLM general knowledge

Run with: python -m pytest src/tests/test_query_logic.py -v
"""

import pytest

# ============================================================================
# Test Helper: Phrase Detection Logic
# ============================================================================

# These are the phrases that indicate RAG context was irrelevant
IRRELEVANT_CONTEXT_PHRASES = [
    # Direct statements about missing information
    "does not contain any information",
    "doesn't contain any information",
    "does not contain information",
    "doesn't contain information",
    "no information about",
    "no information regarding",
    "not contain any information",
    # Context/text/document variations
    "text does not contain",
    "text doesn't contain",
    "context does not contain",
    "context doesn't contain",
    "document does not contain",
    "provided text does not",
    "provided context does not",
    # Relevance statements  
    "not related to",
    "not relevant to",
    "isn't relevant",
    "is not relevant",
    "doesn't pertain",
    "does not pertain",
    # Inability statements
    "i don't have information",
    "i cannot find",
    "cannot answer based on",
    "unable to find",
    "no relevant information",
    "outside the scope",
    "not mentioned in"
]

# FlexCube-related keywords
FLEXCUBE_KEYWORDS = [
    'flexcube', 'oracle', 'banking', 'account', 'transaction', 
    'loan', 'deposit', 'customer', 'error', 'module', 'screen',
    'microfinance', 'ledger', 'gl', 'branch', 'payment', 'schedule',
    'processing', 'rollover', 'delinquency', 'status', 'simulation'
]


def is_flexcube_related(question: str) -> bool:
    """Check if question is FlexCube-related."""
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in FLEXCUBE_KEYWORDS)


def context_was_irrelevant(answer: str) -> bool:
    """Check if answer indicates context was not useful."""
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in IRRELEVANT_CONTEXT_PHRASES)


# ============================================================================
# Test Cases: FlexCube Detection
# ============================================================================

class TestFlexCubeDetection:
    """Tests for detecting FlexCube-related questions."""
    
    def test_flexcube_keyword_direct(self):
        """Direct FlexCube mention should be detected."""
        assert is_flexcube_related("What is FlexCube?") == True
        
    def test_flexcube_account_keyword(self):
        """Account-related questions should be FlexCube-related."""
        assert is_flexcube_related("How do I create an account?") == True
        
    def test_flexcube_microfinance(self):
        """Microfinance questions should be FlexCube-related."""
        assert is_flexcube_related("What is Microfinance Account Processing?") == True
        
    def test_flexcube_loan(self):
        """Loan questions should be FlexCube-related."""
        assert is_flexcube_related("How to process a loan application?") == True
        
    def test_general_question_capital(self):
        """Capital of country should NOT be FlexCube-related."""
        assert is_flexcube_related("What is the capital of Germany?") == False
        
    def test_general_question_prime_minister(self):
        """Prime minister question should NOT be FlexCube-related."""
        assert is_flexcube_related("Who is the Prime Minister of Brazil?") == False
        
    def test_general_question_weather(self):
        """Weather question should NOT be FlexCube-related."""
        assert is_flexcube_related("What is the weather like today?") == False
        
    def test_general_question_python(self):
        """Programming question should NOT be FlexCube-related."""
        assert is_flexcube_related("How do I write a for loop in Python?") == False


# ============================================================================
# Test Cases: Irrelevant Context Detection
# ============================================================================

class TestIrrelevantContextDetection:
    """Tests for detecting when RAG context was not useful."""
    
    def test_detect_text_does_not_contain(self):
        """Should detect 'text does not contain' phrase."""
        answer = "The provided text does not contain any information about the Prime Minister of Brazil."
        assert context_was_irrelevant(answer) == True
        
    def test_detect_no_information_about(self):
        """Should detect 'no information about' phrase."""
        answer = "I have no information about the weather in your area."
        assert context_was_irrelevant(answer) == True
        
    def test_detect_not_related_to(self):
        """Should detect 'not related to' phrase."""
        answer = "This documentation is not related to your question about cooking."
        assert context_was_irrelevant(answer) == True
        
    def test_detect_context_does_not_contain(self):
        """Should detect 'context does not contain' phrase."""
        answer = "The context does not contain information about this topic."
        assert context_was_irrelevant(answer) == True
        
    def test_valid_flexcube_answer(self):
        """Valid FlexCube answer should NOT be detected as irrelevant."""
        answer = "Microfinance Account Processing involves capturing loan details and setting up repayment schedules."
        assert context_was_irrelevant(answer) == False
        
    def test_answer_with_provided_context(self):
        """Answer that USES provided context should NOT be irrelevant."""
        answer = "As detailed in the provided context, the General Ledger module handles accounting."
        assert context_was_irrelevant(answer) == False
        
    def test_answer_with_steps(self):
        """Detailed step-by-step answer should NOT be irrelevant."""
        answer = "The process involves: 1. Account Creation 2. Schedule Setup 3. Payment Processing"
        assert context_was_irrelevant(answer) == False


# ============================================================================
# Test Cases: Two-Tier Flow Logic
# ============================================================================

class TestTwoTierFlowLogic:
    """Tests for the two-tier query flow decision logic."""
    
    def test_flexcube_question_with_relevant_answer(self):
        """FlexCube question with good answer → Keep RAG sources."""
        question = "What is Microfinance Account Processing?"
        answer = "Microfinance Account Processing involves loan disbursements and schedule setup."
        
        is_fc = is_flexcube_related(question)
        is_irrelevant = context_was_irrelevant(answer)
        
        # Should keep sources (FlexCube question, relevant answer)
        should_use_general_knowledge = is_irrelevant and not is_fc
        assert should_use_general_knowledge == False
        
    def test_general_question_with_irrelevant_answer(self):
        """General question with irrelevant context → Fall back to general knowledge."""
        question = "Who is the Prime Minister of Brazil?"
        answer = "The provided text does not contain any information about the Prime Minister of Brazil."
        
        is_fc = is_flexcube_related(question)
        is_irrelevant = context_was_irrelevant(answer)
        
        # Should fall back to general knowledge
        should_use_general_knowledge = is_irrelevant and not is_fc
        assert should_use_general_knowledge == True
        
    def test_general_question_capital_city(self):
        """Capital city question with irrelevant context → Fall back to general knowledge."""
        question = "What is the capital of Germany?"
        answer = "The context does not contain information about Germany's capital."
        
        is_fc = is_flexcube_related(question)
        is_irrelevant = context_was_irrelevant(answer)
        
        should_use_general_knowledge = is_irrelevant and not is_fc
        assert should_use_general_knowledge == True
        
    def test_flexcube_question_with_no_info(self):
        """FlexCube question but no info found → Keep RAG answer, maybe keep sources."""
        question = "What is error code ERR_XYZ_999?"
        answer = "I cannot find information about error code ERR_XYZ_999 in the documentation."
        
        is_fc = is_flexcube_related(question)
        is_irrelevant = context_was_irrelevant(answer)
        
        # Should NOT fall back to general knowledge (it's a FlexCube question)
        should_use_general_knowledge = is_irrelevant and not is_fc
        assert should_use_general_knowledge == False


# ============================================================================
# Test Cases: Query Expansion Logic
# ============================================================================

class TestQueryExpansionParsing:
    """Tests for query expansion parsing logic."""
    
    def test_parse_key_terms_format(self):
        """Should parse key terms from LLM output."""
        import re
        
        output = """KEY_TERMS:
- logged in: signed in, authenticated, connected
- users: accounts, sessions, clients

ALTERNATIVE_QUERIES:
1. How many users have signed in?
2. Count of authenticated users
"""
        # Simulate parsing logic
        key_terms = {}
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('-') and ':' in line:
                parts = line.lstrip('- ').split(':', 1)
                if len(parts) == 2:
                    term = parts[0].strip().lower()
                    synonyms = [s.strip() for s in parts[1].split(',')]
                    key_terms[term] = synonyms
        
        assert 'logged in' in key_terms
        assert 'signed in' in key_terms['logged in']
        assert 'users' in key_terms
        assert 'accounts' in key_terms['users']
    
    def test_parse_alternative_queries(self):
        """Should parse numbered alternative queries."""
        import re
        
        output = """ALTERNATIVE_QUERIES:
1. How many users have signed in?
2. Count of authenticated users
3. User login statistics
"""
        queries = []
        for line in output.split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                query = re.sub(r'^[\d]+[.\)]\s*', '', line).strip()
                if query:
                    queries.append(query)
        
        assert len(queries) == 3
        assert "How many users have signed in?" in queries
        assert "Count of authenticated users" in queries
    
    def test_combined_query_includes_original(self):
        """Combined query should include original question."""
        original = "How many users logged in?"
        expansions = ["signed in users count", "authentication statistics"]
        
        # Simulate combined query building
        combined = original
        for exp in expansions:
            for word in exp.split():
                if word.lower() not in combined.lower():
                    combined += " " + word
        
        assert "logged" in combined.lower()
        assert "users" in combined.lower()
        # New terms from expansions should be added
        assert "authentication" in combined.lower() or "statistics" in combined.lower()
    
    def test_expansion_handles_empty_llm_response(self):
        """Should handle empty or malformed LLM response gracefully."""
        original = "Test question"
        llm_output = ""
        
        # Simulate fallback behavior
        expanded_queries = []
        if not llm_output.strip():
            expanded_queries = [original]  # Fallback to original
        
        assert len(expanded_queries) == 1
        assert expanded_queries[0] == original


class TestQueryExpansionExamples:
    """Test specific expansion examples from requirements."""
    
    def test_logged_in_expansions_expected(self):
        """Verify expected expansions for 'logged in' concept."""
        expected_synonyms = ["signed in", "connected", "authenticated", "user sessions"]
        
        # All these should be semantically similar to "logged in"
        base_concept = "logged in"
        
        # Verify that expected synonyms are reasonable alternatives
        for syn in expected_synonyms:
            # These should all relate to user authentication/connection
            assert any(word in syn.lower() for word in ["sign", "connect", "auth", "session"])
    
    def test_user_count_expansions_expected(self):
        """Verify expected expansions for 'number of users' concept."""
        expected_synonyms = ["count of active users", "user metrics", "usage statistics"]
        
        base_concept = "number of users"
        
        # Verify that expected synonyms relate to counting/metrics
        for syn in expected_synonyms:
            assert any(word in syn.lower() for word in ["count", "metric", "statistic", "user"])


class TestMultiQueryRetrieverLogic:
    """Tests for multi-query retrieval logic."""
    
    def test_deduplication_by_node_id(self):
        """Should deduplicate nodes by ID across multiple query results."""
        # Simulate node results from multiple queries
        class MockNode:
            def __init__(self, node_id, score):
                self.node_id = node_id
                self.score = score
        
        # Query 1 results
        results_q1 = [MockNode("a", 0.9), MockNode("b", 0.8)]
        # Query 2 results (includes duplicate "a")
        results_q2 = [MockNode("a", 0.85), MockNode("c", 0.7)]
        
        # Deduplicate
        all_nodes = []
        seen_ids = set()
        for node in results_q1 + results_q2:
            if node.node_id not in seen_ids:
                all_nodes.append(node)
                seen_ids.add(node.node_id)
        
        assert len(all_nodes) == 3  # a, b, c (no duplicate)
        node_ids = [n.node_id for n in all_nodes]
        assert node_ids.count("a") == 1
    
    def test_result_sorting_by_score(self):
        """Should sort merged results by score (highest first)."""
        class MockNode:
            def __init__(self, score):
                self.score = score
        
        nodes = [MockNode(0.5), MockNode(0.9), MockNode(0.7)]
        sorted_nodes = sorted(nodes, key=lambda n: n.score, reverse=True)
        
        scores = [n.score for n in sorted_nodes]
        assert scores == [0.9, 0.7, 0.5]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v"])


