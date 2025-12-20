"""
Signal Queue Management
Handles concurrent signal processing with queue
"""

import logging
import threading
from queue import Queue, Empty
from typing import Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalQueue:
    """Thread-safe signal queue for processing signals"""
    
    def __init__(self, processor: Callable[[Dict], None]):
        """
        Initialize signal queue
        
        Args:
            processor: Function to process signals (takes signal dict as parameter)
        """
        self.queue = Queue()
        self.processor = processor
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.processed_count = 0
        self.failed_count = 0
    
    def start(self) -> None:
        """Start the queue worker thread"""
        if self.running:
            logger.warning("Signal queue is already running")
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        logger.info("Signal queue started")
    
    def stop(self) -> None:
        """Stop the queue worker thread"""
        if not self.running:
            return
        
        self.running = False
        # Put a None sentinel to wake up the worker
        self.queue.put(None)
        
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
            if self.worker_thread.is_alive():
                logger.warning("Signal queue worker thread did not stop gracefully")
        
        logger.info("Signal queue stopped")
    
    def add_signal(self, signal: Dict) -> bool:
        """
        Add signal to queue
        
        Args:
            signal: Signal dictionary
            
        Returns:
            True if added successfully, False otherwise
        """
        try:
            # Add timestamp
            signal['queued_at'] = datetime.now().isoformat()
            self.queue.put(signal)
            logger.debug(f"Signal added to queue: {signal.get('symbol')} {signal.get('action')}")
            return True
        except Exception as e:
            logger.error(f"Error adding signal to queue: {e}")
            return False
    
    def _worker(self) -> None:
        """Worker thread that processes signals from queue"""
        logger.info("Signal queue worker thread started")
        
        while self.running:
            try:
                # Get signal from queue with timeout
                signal = self.queue.get(timeout=1.0)
                
                # Check for sentinel (None) to stop
                if signal is None:
                    break
                
                # Process signal
                try:
                    self.processor(signal)
                    self.processed_count += 1
                    logger.debug(f"Signal processed: {signal.get('symbol')} {signal.get('action')}")
                except Exception as e:
                    self.failed_count += 1
                    logger.error(f"Error processing signal: {e}", exc_info=True)
                
                # Mark task as done
                self.queue.task_done()
                
            except Empty:
                # Timeout - continue loop to check if still running
                continue
            except Exception as e:
                logger.error(f"Error in signal queue worker: {e}", exc_info=True)
        
        logger.info("Signal queue worker thread stopped")
    
    def get_stats(self) -> Dict[str, int]:
        """Get queue statistics"""
        return {
            'queue_size': self.queue.qsize(),
            'processed': self.processed_count,
            'failed': self.failed_count,
            'running': self.running
        }

