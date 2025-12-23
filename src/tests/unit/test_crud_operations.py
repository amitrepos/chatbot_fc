"""
Unit Tests for CRUD Operations

Tests database CRUD operations for Conversation, QAPair, and Feedback models.
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime

from src.database.crud import (
    create_conversation, get_conversation, get_user_conversations,
    update_conversation_title, delete_conversation,
    create_qa_pair, get_qa_pair, get_conversation_qa_pairs, get_user_qa_pairs,
    create_feedback, get_feedback, get_qa_pair_feedback, get_user_feedback, delete_feedback
)
from src.database.models import Conversation, QAPair, Feedback


class TestConversationCRUD:
    """Tests for Conversation CRUD operations."""
    
    def test_create_conversation(self, db_session: Session, test_user):
        """Test creating a conversation."""
        conversation = create_conversation(
            db=db_session,
            user_id=test_user.id,
            title="Test Conversation"
        )
        
        assert conversation.id is not None
        assert conversation.user_id == test_user.id
        assert conversation.title == "Test Conversation"
        assert conversation.created_at is not None
    
    def test_get_conversation(self, db_session: Session, test_user):
        """Test retrieving a conversation by ID."""
        conversation = create_conversation(db_session, test_user.id, "Test")
        retrieved = get_conversation(db_session, conversation.id)
        
        assert retrieved is not None
        assert retrieved.id == conversation.id
        assert retrieved.title == "Test"
    
    def test_get_user_conversations(self, db_session: Session, test_user):
        """Test retrieving all conversations for a user."""
        # Create multiple conversations
        conv1 = create_conversation(db_session, test_user.id, "Conv 1")
        conv2 = create_conversation(db_session, test_user.id, "Conv 2")
        
        conversations = get_user_conversations(db_session, test_user.id)
        
        assert len(conversations) >= 2
        # Should be ordered by updated_at desc
        assert conversations[0].updated_at >= conversations[1].updated_at
    
    def test_update_conversation_title(self, db_session: Session, test_user):
        """Test updating conversation title."""
        conversation = create_conversation(db_session, test_user.id, "Old Title")
        updated = update_conversation_title(db_session, conversation.id, "New Title")
        
        assert updated is not None
        assert updated.title == "New Title"
    
    def test_delete_conversation(self, db_session: Session, test_user):
        """Test deleting a conversation."""
        conversation = create_conversation(db_session, test_user.id, "To Delete")
        conv_id = conversation.id
        
        result = delete_conversation(db_session, conv_id)
        assert result == True
        
        # Verify deleted
        retrieved = get_conversation(db_session, conv_id)
        assert retrieved is None


class TestQAPairCRUD:
    """Tests for Q&A Pair CRUD operations."""
    
    def test_create_qa_pair(self, db_session: Session, test_user):
        """Test creating a Q&A pair."""
        qa_pair = create_qa_pair(
            db=db_session,
            user_id=test_user.id,
            question="What is FlexCube?",
            answer="FlexCube is a banking software.",
            question_type="text",
            sources=["doc1.pdf"],
            answer_source_type="rag"
        )
        
        assert qa_pair.id is not None
        assert qa_pair.user_id == test_user.id
        assert qa_pair.question == "What is FlexCube?"
        assert qa_pair.answer == "FlexCube is a banking software."
        assert qa_pair.sources == ["doc1.pdf"]
    
    def test_create_qa_pair_with_conversation(self, db_session: Session, test_user):
        """Test creating Q&A pair with conversation."""
        conversation = create_conversation(db_session, test_user.id, "Test")
        qa_pair = create_qa_pair(
            db=db_session,
            user_id=test_user.id,
            question="Test question",
            answer="Test answer",
            conversation_id=conversation.id
        )
        
        assert qa_pair.conversation_id == conversation.id
    
    def test_get_qa_pair(self, db_session: Session, test_user):
        """Test retrieving Q&A pair by ID."""
        qa_pair = create_qa_pair(
            db_session, test_user.id, "Q?", "A."
        )
        retrieved = get_qa_pair(db_session, qa_pair.id)
        
        assert retrieved is not None
        assert retrieved.id == qa_pair.id
        assert retrieved.question == "Q?"
    
    def test_get_conversation_qa_pairs(self, db_session: Session, test_user):
        """Test retrieving Q&A pairs for a conversation."""
        conversation = create_conversation(db_session, test_user.id, "Test")
        qa1 = create_qa_pair(
            db_session, test_user.id, "Q1", "A1", conversation_id=conversation.id
        )
        qa2 = create_qa_pair(
            db_session, test_user.id, "Q2", "A2", conversation_id=conversation.id
        )
        
        qa_pairs = get_conversation_qa_pairs(db_session, conversation.id)
        
        assert len(qa_pairs) >= 2
        # Should be ordered by created_at asc
        assert qa_pairs[0].created_at <= qa_pairs[1].created_at
    
    def test_get_user_qa_pairs(self, db_session: Session, test_user):
        """Test retrieving all Q&A pairs for a user."""
        qa1 = create_qa_pair(db_session, test_user.id, "Q1", "A1")
        qa2 = create_qa_pair(db_session, test_user.id, "Q2", "A2")
        
        qa_pairs = get_user_qa_pairs(db_session, test_user.id)
        
        assert len(qa_pairs) >= 2
        # Should be ordered by created_at desc
        assert qa_pairs[0].created_at >= qa_pairs[1].created_at


class TestFeedbackCRUD:
    """Tests for Feedback CRUD operations."""
    
    def test_create_feedback_like(self, db_session: Session, test_user):
        """Test creating positive feedback (like)."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        feedback = create_feedback(
            db_session, qa_pair.id, test_user.id, rating=2, feedback_text="Great answer!"
        )
        
        assert feedback.id is not None
        assert feedback.rating == 2
        assert feedback.feedback_text == "Great answer!"
    
    def test_create_feedback_dislike(self, db_session: Session, test_user):
        """Test creating negative feedback (dislike)."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        feedback = create_feedback(
            db_session, qa_pair.id, test_user.id, rating=1
        )
        
        assert feedback.rating == 1
    
    def test_create_feedback_invalid_rating(self, db_session: Session, test_user):
        """Test that invalid rating raises ValueError."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        
        with pytest.raises(ValueError, match="Rating must be 1 or 2"):
            create_feedback(db_session, qa_pair.id, test_user.id, rating=3)
    
    def test_update_existing_feedback(self, db_session: Session, test_user):
        """Test that creating feedback twice updates existing."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        
        feedback1 = create_feedback(db_session, qa_pair.id, test_user.id, rating=1)
        feedback2 = create_feedback(db_session, qa_pair.id, test_user.id, rating=2, feedback_text="Changed my mind")
        
        # Should be same feedback, updated
        assert feedback1.id == feedback2.id
        assert feedback2.rating == 2
        assert feedback2.feedback_text == "Changed my mind"
    
    def test_get_qa_pair_feedback(self, db_session: Session, test_user):
        """Test retrieving all feedback for a Q&A pair."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        feedback = create_feedback(db_session, qa_pair.id, test_user.id, rating=2)
        
        feedbacks = get_qa_pair_feedback(db_session, qa_pair.id)
        
        assert len(feedbacks) >= 1
        assert feedbacks[0].id == feedback.id
    
    def test_delete_feedback(self, db_session: Session, test_user):
        """Test deleting feedback."""
        qa_pair = create_qa_pair(db_session, test_user.id, "Q?", "A.")
        feedback = create_feedback(db_session, qa_pair.id, test_user.id, rating=2)
        feedback_id = feedback.id
        
        result = delete_feedback(db_session, feedback_id)
        assert result == True
        
        # Verify deleted
        retrieved = get_feedback(db_session, feedback_id)
        assert retrieved is None




