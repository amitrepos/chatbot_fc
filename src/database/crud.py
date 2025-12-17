"""
Database CRUD Operations

This module provides Create, Read, Update, Delete operations for database models.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from loguru import logger

from .models import (
    User, Permission, UserPermission, RoleTemplate, RoleTemplatePermission,
    Session as SessionModel, Conversation, QAPair, Feedback
)


# ============================================================================
# User CRUD Operations
# ============================================================================

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()


def create_user(
    db: Session,
    username: str,
    email: str,
    password_hash: str,
    full_name: Optional[str] = None,
    user_type: str = "general_user",
    created_by: Optional[int] = None
) -> User:
    """Create a new user."""
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        full_name=full_name,
        user_type=user_type,
        created_by=created_by
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created user: {username} (id: {user.id})")
    return user


def update_user_last_login(db: Session, user_id: int):
    """Update user's last login timestamp."""
    user = get_user(db, user_id)
    if user:
        from datetime import datetime
        user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)


# ============================================================================
# Permission CRUD Operations
# ============================================================================

def get_permission(db: Session, permission_id: int) -> Optional[Permission]:
    """Get permission by ID."""
    return db.query(Permission).filter(Permission.id == permission_id).first()


def get_permission_by_name(db: Session, name: str) -> Optional[Permission]:
    """Get permission by name."""
    return db.query(Permission).filter(Permission.name == name).first()


def get_all_permissions(db: Session) -> List[Permission]:
    """Get all permissions."""
    return db.query(Permission).all()


def get_user_permissions(db: Session, user_id: int) -> List[str]:
    """
    Get all permission names for a user.
    
    Returns both direct permissions and permissions from role templates.
    """
    # Get direct user permissions
    direct_perms = db.query(Permission.name).join(
        UserPermission
    ).filter(
        UserPermission.user_id == user_id
    ).all()
    
    direct_permission_names = [p[0] for p in direct_perms]
    
    # Get user's role template
    user = get_user(db, user_id)
    if user and user.user_type:
        # Get permissions from role template
        template_perms = db.query(Permission.name).join(
            RoleTemplatePermission
        ).join(
            RoleTemplate
        ).filter(
            RoleTemplate.name == user.user_type
        ).all()
        
        template_permission_names = [p[0] for p in template_perms]
        
        # Combine and deduplicate
        all_permissions = list(set(direct_permission_names + template_permission_names))
    else:
        all_permissions = direct_permission_names
    
    return all_permissions


def grant_permission(
    db: Session,
    user_id: int,
    permission_id: int,
    granted_by: Optional[int] = None
) -> UserPermission:
    """Grant a permission to a user."""
    user_perm = UserPermission(
        user_id=user_id,
        permission_id=permission_id,
        granted_by=granted_by
    )
    db.add(user_perm)
    db.commit()
    db.refresh(user_perm)
    logger.info(f"Granted permission {permission_id} to user {user_id}")
    return user_perm


def revoke_permission(db: Session, user_id: int, permission_id: int) -> bool:
    """Revoke a permission from a user."""
    user_perm = db.query(UserPermission).filter(
        and_(
            UserPermission.user_id == user_id,
            UserPermission.permission_id == permission_id
        )
    ).first()
    
    if user_perm:
        db.delete(user_perm)
        db.commit()
        logger.info(f"Revoked permission {permission_id} from user {user_id}")
        return True
    return False


# ============================================================================
# Role Template CRUD Operations
# ============================================================================

def get_role_template(db: Session, template_id: int) -> Optional[RoleTemplate]:
    """Get role template by ID."""
    return db.query(RoleTemplate).filter(RoleTemplate.id == template_id).first()


def get_role_template_by_name(db: Session, name: str) -> Optional[RoleTemplate]:
    """Get role template by name."""
    return db.query(RoleTemplate).filter(RoleTemplate.name == name).first()


def assign_role_template_to_user(
    db: Session,
    user_id: int,
    template_name: str
) -> bool:
    """
    Assign a role template to a user by granting all template permissions.
    
    Args:
        db: Database session
        user_id: User ID
        template_name: Role template name (e.g., "general_user")
        
    Returns:
        bool: True if successful
    """
    template = get_role_template_by_name(db, template_name)
    if not template:
        logger.error(f"Role template not found: {template_name}")
        return False
    
    # Get all permissions from template
    template_perms = db.query(RoleTemplatePermission.permission_id).filter(
        RoleTemplatePermission.role_template_id == template.id
    ).all()
    
    permission_ids = [p[0] for p in template_perms]
    
    # Grant all template permissions to user (skip if already granted)
    for perm_id in permission_ids:
        existing = db.query(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == perm_id
            )
        ).first()
        
        if not existing:
            grant_permission(db, user_id, perm_id)
    
    logger.info(f"Assigned role template {template_name} to user {user_id}")
    return True


# ============================================================================
# Conversation CRUD Operations
# ============================================================================

def create_conversation(
    db: Session,
    user_id: int,
    title: Optional[str] = None
) -> Conversation:
    """
    Create a new conversation for a user.
    
    Args:
        db: Database session
        user_id: User ID
        title: Optional conversation title
        
    Returns:
        Conversation: Created conversation
    """
    conversation = Conversation(
        user_id=user_id,
        title=title
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    logger.info(f"Created conversation {conversation.id} for user {user_id}")
    return conversation


def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
    """Get conversation by ID."""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def get_user_conversations(
    db: Session,
    user_id: int,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Conversation]:
    """
    Get all conversations for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Optional limit on number of results
        offset: Offset for pagination
        
    Returns:
        List[Conversation]: List of conversations, ordered by updated_at desc
    """
    query = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.updated_at.desc())
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    return query.all()


def update_conversation_title(
    db: Session,
    conversation_id: int,
    title: str
) -> Optional[Conversation]:
    """Update conversation title."""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        conversation.title = title
        db.commit()
        db.refresh(conversation)
        logger.info(f"Updated conversation {conversation_id} title")
    return conversation


def delete_conversation(db: Session, conversation_id: int) -> bool:
    """Delete a conversation and all its Q&A pairs."""
    conversation = get_conversation(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.commit()
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    return False


# ============================================================================
# Q&A Pair CRUD Operations
# ============================================================================

def create_qa_pair(
    db: Session,
    user_id: int,
    question: str,
    answer: str,
    conversation_id: Optional[int] = None,
    question_type: str = "text",
    image_path: Optional[str] = None,
    sources: Optional[List[str]] = None,
    answer_source_type: Optional[str] = None,
    query_expansion: Optional[dict] = None,
    processing_time_seconds: Optional[float] = None
) -> QAPair:
    """
    Create a new Q&A pair.
    
    Args:
        db: Database session
        user_id: User ID
        question: User's question
        answer: AI's answer
        conversation_id: Optional conversation ID
        question_type: "text" or "image"
        image_path: Path to image if image query
        sources: List of source filenames
        answer_source_type: "rag", "general_knowledge", or "vision"
        query_expansion: Query expansion metadata
        processing_time_seconds: Time taken to process query
        
    Returns:
        QAPair: Created Q&A pair
    """
    qa_pair = QAPair(
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        answer=answer,
        question_type=question_type,
        image_path=image_path,
        sources=sources,
        answer_source_type=answer_source_type,
        query_expansion=query_expansion,
        processing_time_seconds=processing_time_seconds
    )
    db.add(qa_pair)
    db.commit()
    db.refresh(qa_pair)
    logger.info(f"Created Q&A pair {qa_pair.id} for user {user_id}")
    return qa_pair


def get_qa_pair(db: Session, qa_pair_id: int) -> Optional[QAPair]:
    """Get Q&A pair by ID."""
    return db.query(QAPair).filter(QAPair.id == qa_pair_id).first()


def get_conversation_qa_pairs(
    db: Session,
    conversation_id: int,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[QAPair]:
    """
    Get all Q&A pairs for a conversation.
    
    Args:
        db: Database session
        conversation_id: Conversation ID
        limit: Optional limit on number of results
        offset: Offset for pagination
        
    Returns:
        List[QAPair]: List of Q&A pairs, ordered by created_at asc
    """
    query = db.query(QAPair).filter(
        QAPair.conversation_id == conversation_id
    ).order_by(QAPair.created_at.asc())
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    return query.all()


def get_user_qa_pairs(
    db: Session,
    user_id: int,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[QAPair]:
    """
    Get all Q&A pairs for a user.
    
    Args:
        db: Database session
        user_id: User ID
        limit: Optional limit on number of results
        offset: Offset for pagination
        
    Returns:
        List[QAPair]: List of Q&A pairs, ordered by created_at desc
    """
    query = db.query(QAPair).filter(
        QAPair.user_id == user_id
    ).order_by(QAPair.created_at.desc())
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    return query.all()


# ============================================================================
# Feedback CRUD Operations
# ============================================================================

def create_feedback(
    db: Session,
    qa_pair_id: int,
    user_id: int,
    rating: int,
    feedback_text: Optional[str] = None
) -> Feedback:
    """
    Create feedback for a Q&A pair.
    
    Args:
        db: Database session
        qa_pair_id: Q&A pair ID
        user_id: User ID providing feedback
        rating: 1 = dislike, 2 = like
        feedback_text: Optional comment
        
    Returns:
        Feedback: Created feedback
        
    Raises:
        ValueError: If rating is not 1 or 2
    """
    if rating not in [1, 2]:
        raise ValueError("Rating must be 1 (dislike) or 2 (like)")
    
    # Check if feedback already exists for this Q&A pair from this user
    existing = db.query(Feedback).filter(
        and_(
            Feedback.qa_pair_id == qa_pair_id,
            Feedback.user_id == user_id
        )
    ).first()
    
    if existing:
        # Update existing feedback
        existing.rating = rating
        existing.feedback_text = feedback_text
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated feedback {existing.id} for Q&A pair {qa_pair_id}")
        return existing
    
    feedback = Feedback(
        qa_pair_id=qa_pair_id,
        user_id=user_id,
        rating=rating,
        feedback_text=feedback_text
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    logger.info(f"Created feedback {feedback.id} for Q&A pair {qa_pair_id}")
    return feedback


def get_feedback(db: Session, feedback_id: int) -> Optional[Feedback]:
    """Get feedback by ID."""
    return db.query(Feedback).filter(Feedback.id == feedback_id).first()


def get_qa_pair_feedback(
    db: Session,
    qa_pair_id: int
) -> List[Feedback]:
    """Get all feedback for a Q&A pair."""
    return db.query(Feedback).filter(
        Feedback.qa_pair_id == qa_pair_id
    ).order_by(Feedback.created_at.desc()).all()


def get_user_feedback(
    db: Session,
    user_id: int,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Feedback]:
    """Get all feedback provided by a user."""
    query = db.query(Feedback).filter(
        Feedback.user_id == user_id
    ).order_by(Feedback.created_at.desc())
    
    if limit:
        query = query.limit(limit).offset(offset)
    
    return query.all()


def delete_feedback(db: Session, feedback_id: int) -> bool:
    """Delete feedback."""
    feedback = get_feedback(db, feedback_id)
    if feedback:
        db.delete(feedback)
        db.commit()
        logger.info(f"Deleted feedback {feedback_id}")
        return True
    return False

