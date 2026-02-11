"""
WebSocket Manager Service for MWCS Backend

Manages WebSocket connections for real-time progress updates during processing.
"""

import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Supports multiple connections per session for collaborative viewing.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        # Map of session_id -> set of WebSocket connections
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a new WebSocket connection for a session.
        
        Args:
            websocket: The WebSocket connection to accept
            session_id: The session ID this connection is for
        """
        await websocket.accept()
        
        if session_id not in self._active_connections:
            self._active_connections[session_id] = set()
        
        self._active_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected for session {session_id}. "
                   f"Total connections: {len(self._active_connections[session_id])}")
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
            session_id: The session ID this connection was for
        """
        if session_id in self._active_connections:
            self._active_connections[session_id].discard(websocket)
            
            # Clean up empty session entries
            if not self._active_connections[session_id]:
                del self._active_connections[session_id]
            
            logger.info(f"WebSocket disconnected for session {session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """
        Send a message to all connections for a session.
        
        Args:
            session_id: The session ID to send to
            message: The message dictionary to send (will be JSON serialized)
        """
        if session_id not in self._active_connections:
            logger.warning(f"No active connections for session {session_id}")
            return
        
        # Send to all connections, removing any that fail
        dead_connections = set()
        
        for connection in self._active_connections[session_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                dead_connections.add(connection)
        
        # Clean up dead connections
        for connection in dead_connections:
            self.disconnect(connection, session_id)
    
    async def broadcast_progress(
        self,
        session_id: str,
        current: int,
        total: int,
        message: str = "",
        status: str = "processing"
    ):
        """
        Broadcast processing progress to all connections for a session.
        
        Args:
            session_id: The session ID to broadcast to
            current: Current progress count
            total: Total items to process
            message: Optional status message
            status: Processing status (processing, completed, error)
        """
        progress_data = {
            "type": "progress",
            "session_id": session_id,
            "current": current,
            "total": total,
            "percentage": round((current / total * 100) if total > 0 else 0, 2),
            "message": message,
            "status": status
        }
        
        await self.send_message(session_id, progress_data)
    
    async def broadcast_status(
        self,
        session_id: str,
        status: str,
        message: str = "",
        data: dict = None
    ):
        """
        Broadcast a status update to all connections for a session.
        
        Args:
            session_id: The session ID to broadcast to
            status: Status type (info, success, warning, error)
            message: Status message
            data: Optional additional data
        """
        status_data = {
            "type": "status",
            "session_id": session_id,
            "status": status,
            "message": message,
            "data": data or {}
        }
        
        await self.send_message(session_id, status_data)
    
    async def broadcast_completion(
        self,
        session_id: str,
        success: bool,
        message: str = "",
        results: dict = None
    ):
        """
        Broadcast processing completion to all connections for a session.
        
        Args:
            session_id: The session ID to broadcast to
            success: Whether processing completed successfully
            message: Completion message
            results: Optional results summary
        """
        completion_data = {
            "type": "completion",
            "session_id": session_id,
            "success": success,
            "message": message,
            "results": results or {}
        }
        
        await self.send_message(session_id, completion_data)
    
    def get_connection_count(self, session_id: str = None) -> int:
        """
        Get the number of active connections.
        
        Args:
            session_id: Optional session ID to get count for specific session
            
        Returns:
            int: Number of active connections
        """
        if session_id:
            return len(self._active_connections.get(session_id, set()))
        else:
            return sum(len(conns) for conns in self._active_connections.values())


# Global connection manager instance
_connection_manager: ConnectionManager = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.
    
    Returns:
        ConnectionManager: The global connection manager
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
