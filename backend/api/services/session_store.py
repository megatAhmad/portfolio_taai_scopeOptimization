"""
Session Store Service for MWCS Backend

Manages in-memory session data for local development.
Each session contains uploaded data, rule configurations, and processing results.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict

from src.upload import UploadedData
from src.rules import RuleBuilder
from src.enhanced_rule_engine import EnhancedRuleEngine
from src.logic_engine import LogicEngine
from src.export import ExportManager

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Container for all session-related data."""
    
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    
    # Data components
    uploaded_data: Optional[UploadedData] = None
    rule_builder: Optional[RuleBuilder] = None
    enhanced_rule_engine: Optional[EnhancedRuleEngine] = None
    logic_engine: Optional[LogicEngine] = None
    export_manager: Optional[ExportManager] = None
    
    # Processing results
    evaluation_results: Optional[dict] = None
    justification_results: Optional[list] = None
    processing_status: str = "idle"  # idle, processing, completed, error
    processing_progress: float = 0.0
    processing_error: Optional[str] = None
    
    def update_access_time(self):
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.now()


class SessionStore:
    """
    In-memory session store for local development.
    
    This is a simple implementation suitable for single-user local usage.
    For production deployment, consider using Redis or a database.
    """
    
    def __init__(self):
        """Initialize the session store."""
        self._sessions: Dict[str, SessionData] = {}
        logger.info("SessionStore initialized")
    
    def create_session(self) -> str:
        """
        Create a new session and return its ID.
        
        Returns:
            str: The generated session ID
        """
        session_id = str(uuid.uuid4())
        session_data = SessionData(session_id=session_id)
        self._sessions[session_id] = session_data
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session data by ID.
        
        Args:
            session_id: The session ID to retrieve
            
        Returns:
            SessionData if found, None otherwise
        """
        session = self._sessions.get(session_id)
        if session:
            session.update_access_time()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session ID to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Deleted session: {session_id}")
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """
        List all active session IDs.
        
        Returns:
            list[str]: List of session IDs
        """
        return list(self._sessions.keys())
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up sessions older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        now = datetime.now()
        to_delete = []
        
        for session_id, session in self._sessions.items():
            age_hours = (now - session.last_accessed).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_delete.append(session_id)
        
        for session_id in to_delete:
            self.delete_session(session_id)
        
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old sessions")
    
    def get_session_count(self) -> int:
        """
        Get the total number of active sessions.
        
        Returns:
            int: Number of active sessions
        """
        return len(self._sessions)


# Global session store instance
_session_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    """
    Get the global session store instance.
    
    Returns:
        SessionStore: The global session store
    """
    global _session_store
    if _session_store is None:
        _session_store = SessionStore()
    return _session_store
