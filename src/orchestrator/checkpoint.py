"""Checkpoint management for state persistence."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph.checkpoint.memory import MemorySaver as SqliteSaver
    except ImportError:
        SqliteSaver = None  # type: ignore

from ..common.exceptions import CheckpointError, StateRecoveryError


class CheckpointManager:
    """Manages state persistence using LangGraph checkpointers."""
    
    def __init__(self, db_path: str = "checkpoints.db"):
        """Initialize the checkpoint manager.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._saver: SqliteSaver | None = None
        self._conn: sqlite3.Connection | None = None
    
    def _ensure_connection(self) -> None:
        """Ensure database connection is established."""
        if self._conn is None:
            # Ensure directory exists
            db_path = Path(self.db_path)
            if db_path.parent != Path('.'):
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._conn = sqlite3.connect(self.db_path)
            
            if SqliteSaver is not None:
                try:
                    self._saver = SqliteSaver(self._conn)
                except Exception:
                    # Fallback: create tables manually
                    self._create_tables()
                    self._saver = None
            else:
                self._create_tables()
                self._saver = None
    
    def _create_tables(self) -> None:
        """Create checkpoint tables if SqliteSaver is not available."""
        assert self._conn is not None
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT,
                metadata TEXT,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
        """)
        self._conn.commit()
    
    def get_checkpointer(self) -> SqliteSaver:
        """Get the LangGraph checkpointer.
        
        Returns:
            The SqliteSaver instance.
        """
        self._ensure_connection()
        assert self._saver is not None
        return self._saver
    
    async def list_threads(self) -> list[dict[str, Any]]:
        """List all conversation threads.
        
        Returns:
            List of thread information dictionaries.
        """
        self._ensure_connection()
        assert self._conn is not None
        
        try:
            cursor = self._conn.execute("""
                SELECT DISTINCT thread_id, MAX(created_at) as last_updated
                FROM checkpoints
                GROUP BY thread_id
                ORDER BY last_updated DESC
            """)
            
            threads = []
            for row in cursor.fetchall():
                threads.append({
                    "thread_id": row[0],
                    "last_updated": row[1]
                })
            
            return threads
        except sqlite3.Error as e:
            raise CheckpointError("list_threads", str(e))
    
    async def get_thread_state(self, thread_id: str) -> dict[str, Any] | None:
        """Get the latest state for a thread.
        
        Args:
            thread_id: The thread identifier.
            
        Returns:
            The thread state or None if not found.
        """
        self._ensure_connection()
        assert self._saver is not None
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            checkpoint = self._saver.get(config)
            
            if checkpoint is None:
                return None
            
            return {
                "thread_id": thread_id,
                "checkpoint": checkpoint,
                "state": checkpoint.get("channel_values", {})
            }
        except Exception as e:
            raise StateRecoveryError(thread_id, str(e))
    
    async def save_state(
        self,
        thread_id: str,
        state: dict[str, Any],
        metadata: dict[str, Any] | None = None
    ) -> None:
        """Manually save a state checkpoint.
        
        Args:
            thread_id: The thread identifier.
            state: The state to save.
            metadata: Optional metadata.
        """
        self._ensure_connection()
        assert self._saver is not None
        
        try:
            config = {"configurable": {"thread_id": thread_id}}
            
            # Create checkpoint data
            checkpoint = {
                "v": 1,
                "ts": datetime.now().isoformat(),
                "channel_values": state,
                "channel_versions": {},
                "versions_seen": {},
            }
            
            if metadata:
                checkpoint["metadata"] = metadata
            
            self._saver.put(config, checkpoint, metadata or {})
        except Exception as e:
            raise CheckpointError("save_state", str(e))
    
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete all checkpoints for a thread.
        
        Args:
            thread_id: The thread identifier.
            
        Returns:
            True if deleted, False if not found.
        """
        self._ensure_connection()
        assert self._conn is not None
        
        try:
            cursor = self._conn.execute(
                "DELETE FROM checkpoints WHERE thread_id = ?",
                (thread_id,)
            )
            self._conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            raise CheckpointError("delete_thread", str(e))
    
    async def get_thread_history(
        self,
        thread_id: str,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get checkpoint history for a thread.
        
        Args:
            thread_id: The thread identifier.
            limit: Maximum number of checkpoints to return.
            
        Returns:
            List of checkpoint summaries.
        """
        self._ensure_connection()
        assert self._conn is not None
        
        try:
            cursor = self._conn.execute("""
                SELECT checkpoint_id, created_at, metadata
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (thread_id, limit))
            
            history = []
            for row in cursor.fetchall():
                metadata = {}
                if row[2]:
                    try:
                        metadata = json.loads(row[2])
                    except json.JSONDecodeError:
                        pass
                
                history.append({
                    "checkpoint_id": row[0],
                    "created_at": row[1],
                    "metadata": metadata
                })
            
            return history
        except sqlite3.Error as e:
            raise CheckpointError("get_thread_history", str(e))
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            self._saver = None
    
    def __enter__(self) -> "CheckpointManager":
        """Context manager entry."""
        self._ensure_connection()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
