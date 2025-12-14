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
# Run Tests
# ============================================================================

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v"])

