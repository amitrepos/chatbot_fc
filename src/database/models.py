"""
SQLAlchemy Database Models

This module defines all database models using SQLAlchemy ORM.
Models correspond to the database schema created in Step 1.
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, DECIMAL, JSON, and_
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import List

from .database import Base


class User(Base):
    """
    User model representing application users.
    
    Attributes:
        id: Primary key
        username: Unique username
        email: Unique email address
        password_hash: Bcrypt hashed password
        full_name: User's full name
        created_at: Account creation timestamp
        last_login: Last login timestamp
        is_active: Whether account is active
        user_type: operational_admin or general_user
        created_by: ID of admin who created this user
        notes: Admin notes about user
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    user_type = Column(String(30), default="general_user", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text)
    
    # Relationships
    created_users = relationship("User", remote_side=[id], backref="creator")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    qa_pairs = relationship("QAPair", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    # Specify foreign_keys to disambiguate between user_id and granted_by foreign keys
    # Will be configured after UserPermission class is defined (see end of file)


class Permission(Base):
    """
    Permission model for RBAC.
    
    Represents a single permission that can be granted to users.
    """
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    category = Column(String(50), index=True)  # chat, documents, dashboard, etc.
    
    # Relationships
    user_permissions = relationship("UserPermission", back_populates="permission", cascade="all, delete-orphan")
    role_template_permissions = relationship("RoleTemplatePermission", back_populates="permission", cascade="all, delete-orphan")


class UserPermission(Base):
    """
    Many-to-Many relationship between Users and Permissions.
    
    Tracks which permissions each user has been granted.
    """
    __tablename__ = "user_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_permissions")
    permission = relationship("Permission", back_populates="user_permissions")


# Configure User.user_permissions relationship after UserPermission is defined
User.user_permissions = relationship(
    "UserPermission",
    foreign_keys=[UserPermission.user_id],
    back_populates="user",
    cascade="all, delete-orphan"
)


class RoleTemplate(Base):
    """
    Role template model for predefined permission sets.
    
    Examples: operational_admin, general_user
    """
    __tablename__ = "role_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_system_template = Column(Boolean, default=True)
    
    # Relationships
    role_template_permissions = relationship("RoleTemplatePermission", back_populates="role_template", cascade="all, delete-orphan")


class RoleTemplatePermission(Base):
    """
    Many-to-Many relationship between Role Templates and Permissions.
    
    Defines which permissions are included in each role template.
    """
    __tablename__ = "role_template_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_template_id = Column(Integer, ForeignKey("role_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Relationships
    role_template = relationship("RoleTemplate", back_populates="role_template_permissions")
    permission = relationship("Permission", back_populates="role_template_permissions")


class Session(Base):
    """
    User session model for tracking active sessions.
    
    Stores JWT token hashes and session metadata.
    """
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


class Conversation(Base):
    """
    Conversation model for grouping Q&A pairs.
    
    Each conversation represents a user's chat session.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    qa_pairs = relationship("QAPair", back_populates="conversation", cascade="all, delete-orphan")


class QAPair(Base):
    """
    Q&A Pair model for storing questions and answers.
    
    Stores all user queries and AI responses for training data collection.
    """
    __tablename__ = "qa_pairs"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Question data
    question = Column(Text, nullable=False)
    question_type = Column(String(20), default="text")  # text or image
    image_path = Column(String(500))  # If image query
    
    # Answer data
    answer = Column(Text, nullable=False)
    sources = Column(JSON)  # Array of source filenames
    answer_source_type = Column(String(50))  # rag, general_knowledge, vision
    
    # Query expansion metadata (for training)
    query_expansion = Column(JSON)  # Original + expanded queries
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processing_time_seconds = Column(DECIMAL(10, 2))
    
    # Relationships
    conversation = relationship("Conversation", back_populates="qa_pairs")
    user = relationship("User", back_populates="qa_pairs")
    feedback = relationship("Feedback", back_populates="qa_pair", cascade="all, delete-orphan")


class Feedback(Base):
    """
    Feedback model for user ratings on answers.
    
    Stores like/dislike and optional comments for training data.
    """
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    qa_pair_id = Column(Integer, ForeignKey("qa_pairs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Feedback data
    rating = Column(Integer, nullable=False, index=True)  # 1 = dislike, 2 = like
    feedback_text = Column(Text)  # Optional user comment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    qa_pair = relationship("QAPair", back_populates="feedback")
    user = relationship("User", back_populates="feedback")


class TrainingDataExport(Base):
    """
    Training data export model for tracking exports.
    
    Future use: Track when training data was exported for model fine-tuning.
    """
    __tablename__ = "training_data_export"
    
    id = Column(Integer, primary_key=True, index=True)
    export_date = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    total_pairs = Column(Integer)
    total_feedback = Column(Integer)
    export_status = Column(String(20), index=True)  # pending, completed, failed
    file_path = Column(String(500))

