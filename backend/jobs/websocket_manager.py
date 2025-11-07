"""WebSocket connection manager."""
from collections import defaultdict
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect

from utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, job_id: str, websocket: WebSocket):
        """
        Accept and register a WebSocket connection.

        Args:
            job_id: Job identifier
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[job_id].append(websocket)
        logger.info(f"WebSocket connected", extra={'job_id': job_id})

    def disconnect(self, job_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            job_id: Job identifier
            websocket: WebSocket connection
        """
        if websocket in self.active_connections[job_id]:
            self.active_connections[job_id].remove(websocket)
            logger.info(f"WebSocket disconnected", extra={'job_id': job_id})

    async def broadcast(self, job_id: str, message: dict):
        """
        Broadcast a message to all connections for a job.

        Args:
            job_id: Job identifier
            message: Message to broadcast
        """
        disconnected = []
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
                logger.debug(f"Connection disconnected during broadcast", extra={'job_id': job_id})
            except Exception as e:
                disconnected.append(connection)
                logger.error(f"Error broadcasting to WebSocket: {e}", extra={'job_id': job_id}, exc_info=True)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(job_id, connection)


# Global connection manager
manager = ConnectionManager()
