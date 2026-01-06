"""
Queue Handler Module - HOMES-Engine
Manages task queues with n8n integration and local fallback
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import aiohttp
import logging

from core.error_handler import get_logger, retry, fallback, ErrorContext

logger = get_logger(__name__)


class QueueTask:
    """Represents a single queue task"""
    
    def __init__(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 0,
        task_id: Optional[str] = None
    ):
        self.task_type = task_type
        self.data = data
        self.priority = priority
        self.task_id = task_id or self._generate_id()
        self.created_at = datetime.now().isoformat()
        self.status = "pending"
        self.attempts = 0
    
    def _generate_id(self) -> str:
        """Generate unique task ID"""
        content = f"{self.task_type}_{self.data}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict:
        """Convert task to dictionary"""
        return {
            "task_id": self.task_id,
            "type": self.task_type,
            "data": self.data,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status,
            "attempts": self.attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QueueTask":
        """Create task from dictionary"""
        task = cls(
            task_type=data["type"],
            data=data["data"],
            priority=data.get("priority", 0),
            task_id=data["task_id"]
        )
        task.status = data.get("status", "pending")
        task.created_at = data.get("created_at", datetime.now().isoformat())
        task.attempts = data.get("attempts", 0)
        return task


class QueueHandler:
    """Manages task queues with n8n integration and local fallback"""
    
    def __init__(
        self,
        n8n_webhook_url: Optional[str] = None,
        pending_dir: str = "queue/pending",
        processed_dir: str = "queue/processed"
    ):
        self.n8n_webhook_url = n8n_webhook_url
        self.pending_dir = Path(pending_dir)
        self.processed_dir = Path(processed_dir)
        self.pending_tasks: List[QueueTask] = []
        self.processed_tasks: List[QueueTask] = []
        self.n8n_online = False
        
        # Create directories
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"QueueHandler initialized: {pending_dir} / {processed_dir}")
        
        # Load existing tasks
        self._load_tasks()
    
    def _load_tasks(self):
        """Load pending and processed tasks from disk"""
        try:
            # Load pending
            for file in self.pending_dir.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        task_data = json.load(f)
                        task = QueueTask.from_dict(task_data)
                        self.pending_tasks.append(task)
                except json.JSONDecodeError:
                    logger.warning(f"Skipping corrupted task file: {file}")
            
            # Load processed
            for file in self.processed_dir.glob("*.json"):
                try:
                    with open(file, 'r') as f:
                        task_data = json.load(f)
                        task = QueueTask.from_dict(task_data)
                        self.processed_tasks.append(task)
                except json.JSONDecodeError:
                    logger.warning(f"Skipping corrupted task file: {file}")
            
            logger.info(
                f"Loaded {len(self.pending_tasks)} pending, "
                f"{len(self.processed_tasks)} processed tasks"
            )
        
        except Exception as e:
            logger.error(f"Error loading tasks: {str(e)}")
    
    async def check_n8n_status(self) -> bool:
        """Check if n8n webhook is reachable"""
        if not self.n8n_webhook_url:
            logger.debug("No n8n webhook configured")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                # Try simple GET to webhook URL
                async with session.get(self.n8n_webhook_url, timeout=5) as resp:
                    self.n8n_online = resp.status < 500
                    if self.n8n_online:
                        logger.info("✅ n8n webhook is reachable")
                    else:
                        logger.warning(f"n8n webhook returned status {resp.status}")
                    return self.n8n_online
        
        except Exception as e:
            logger.warning(f"n8n offline: {str(e)}")
            self.n8n_online = False
            return False
    
    @retry(max_attempts=3, delay=1.0)
    async def send_to_n8n(self, task: QueueTask) -> bool:
        """Send task to n8n webhook"""
        if not self.n8n_webhook_url:
            logger.debug("No n8n webhook configured, using local queue")
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.n8n_webhook_url,
                    json=task.to_dict(),
                    timeout=10
                ) as resp:
                    if resp.status == 200:
                        logger.info(f"✅ Task sent to n8n: {task.task_id}")
                        return True
                    else:
                        raise Exception(f"n8n returned status {resp.status}")
        
        except Exception as e:
            logger.error(f"Failed to send to n8n: {str(e)}")
            raise
    
    def _save_task(self, task: QueueTask, directory: Path):
        """Save task to disk"""
        try:
            task_file = directory / f"{task.task_id}.json"
            with open(task_file, 'w') as f:
                json.dump(task.to_dict(), f, indent=2)
            logger.debug(f"Task saved: {task_file}")
        
        except Exception as e:
            logger.error(f"Failed to save task: {str(e)}")
    
    def add_task(
        self,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 0
    ) -> str:
        """
        Add task to queue
        
        Args:
            task_type: Type of task (e.g., "render", "script", "tts")
            data: Task data/parameters
            priority: Priority level (higher = processed first)
        
        Returns:
            Task ID
        """
        # Check for duplicates
        task_id_candidate = hashlib.md5(
            f"{task_type}_{json.dumps(data, sort_keys=True)}".encode()
        ).hexdigest()[:12]
        
        existing = any(t.task_id == task_id_candidate for t in self.pending_tasks)
        if existing:
            logger.info(f"Task already in queue: {task_id_candidate}")
            return task_id_candidate
        
        # Create task
        task = QueueTask(task_type, data, priority, task_id_candidate)
        self.pending_tasks.append(task)
        
        # Sort by priority
        self.pending_tasks.sort(key=lambda t: -t.priority)
        
        # Save to disk
        self._save_task(task, self.pending_dir)
        
        logger.info(f"✨ Task added: {task.task_id} ({task_type})")
        return task.task_id
    
    async def process_queue(self) -> Dict[str, int]:
        """
        Process all pending tasks
        
        Returns:
            Summary of processed tasks
        """
        with ErrorContext("Process Queue"):
            processed = 0
            failed = 0
            
            # Check n8n availability
            await self.check_n8n_status()
            
            while self.pending_tasks:
                task = self.pending_tasks[0]
                
                try:
                    # Try to send to n8n if online
                    if self.n8n_online:
                        success = await self.send_to_n8n(task)
                        if success:
                            task.status = "sent_to_n8n"
                            processed += 1
                            self.pending_tasks.pop(0)
                            self.processed_tasks.append(task)
                            self._save_task(task, self.processed_dir)
                            (self.pending_dir / f"{task.task_id}.json").unlink(missing_ok=True)
                            continue
                    
                    # Fallback: process locally
                    task.status = "processing_local"
                    task.attempts += 1
                    
                    # Simulate local processing (would call actual handler)
                    await asyncio.sleep(0.1)
                    
                    task.status = "completed_local"
                    processed += 1
                    self.pending_tasks.pop(0)
                    self.processed_tasks.append(task)
                    self._save_task(task, self.processed_dir)
                    (self.pending_dir / f"{task.task_id}.json").unlink(missing_ok=True)
                
                except Exception as e:
                    logger.error(f"Error processing task {task.task_id}: {str(e)}")
                    task.attempts += 1
                    if task.attempts >= 3:
                        task.status = "failed"
                        failed += 1
                        self.pending_tasks.pop(0)
                        self.processed_tasks.append(task)
                        self._save_task(task, self.processed_dir)
                    break
            
            summary = {
                "processed": processed,
                "failed": failed,
                "pending": len(self.pending_tasks)
            }
            
            logger.info(f"Queue processing summary: {summary}")
            return summary
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        return {
            "pending_count": len(self.pending_tasks),
            "processed_count": len(self.processed_tasks),
            "n8n_online": self.n8n_online,
            "pending_tasks": [t.to_dict() for t in self.pending_tasks[:5]],  # First 5
        }
    
    def clear_old_tasks(self, days: int = 7):
        """Clear processed tasks older than N days"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        before = len(self.processed_tasks)
        
        self.processed_tasks = [
            t for t in self.processed_tasks
            if datetime.fromisoformat(t.created_at) > cutoff
        ]
        
        logger.info(f"Cleared {before - len(self.processed_tasks)} old tasks")


# Async context manager for queue operations
class QueueContext:
    """Context manager for queue operations"""
    
    def __init__(self, queue_handler: QueueHandler):
        self.queue = queue_handler
    
    async def __aenter__(self):
        logger.info("Entering queue context")
        return self.queue
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"Queue context error: {exc_type.__name__}")
            return False
        else:
            logger.info("Queue context completed successfully")
            return True


if __name__ == "__main__":
    # Example usage
    async def test_queue():
        queue = QueueHandler()
        
        # Add tasks
        queue.add_task("script", {"topic": "AI", "duration": 60})
        queue.add_task("render", {"clips": 5, "fps": 30})
        queue.add_task("tts", {"text": "Hello world", "voice": "en-US"})
        
        # Process queue
        result = await queue.process_queue()
        print(f"Processing result: {result}")
        
        # Get status
        status = queue.get_queue_status()
        print(f"Queue status: {json.dumps(status, indent=2)}")
    
    # Run example
    asyncio.run(test_queue())
