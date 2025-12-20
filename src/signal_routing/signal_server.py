"""
Signal Server
HTTP server for receiving trading signals from external platforms
"""

import logging
import threading
from typing import Dict, Optional
from flask import Flask, request, jsonify
from datetime import datetime

from .signal_parser import SignalParser
from .signal_router import SignalRouter
from .signal_queue import SignalQueue

logger = logging.getLogger(__name__)


class SignalServer:
    """HTTP server for receiving and processing trading signals"""
    
    def __init__(self, signal_router: SignalRouter, port: int = 8080, host: str = '0.0.0.0'):
        """
        Initialize signal server
        
        Args:
            signal_router: Signal router instance
            port: Server port (default: 8080)
            host: Server host (default: 0.0.0.0 for all interfaces)
        """
        self.signal_router = signal_router
        self.port = port
        self.host = host
        self.parser = SignalParser()
        self.app = Flask(__name__)
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Create signal queue
        self.signal_queue = SignalQueue(self._process_signal)
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Setup Flask routes"""
        
        @self.app.route('/signal', methods=['GET', 'POST'])
        def handle_signal():
            """Handle signal endpoint"""
            try:
                # Get request data
                if request.method == 'GET':
                    request_data = request.args.to_dict()
                else:  # POST
                    if request.is_json:
                        request_data = request.get_json()
                    else:
                        request_data = request.form.to_dict()
                
                # Parse signal
                signal = self.parser.parse_signal(request_data, request.method)
                
                if not signal:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to parse signal'
                    }), 400
                
                # Validate signal
                is_valid, error_msg = self.parser.validate_signal(signal)
                if not is_valid:
                    return jsonify({
                        'success': False,
                        'error': error_msg
                    }), 400
                
                # Add to queue for processing
                if self.signal_queue.add_signal(signal):
                    return jsonify({
                        'success': True,
                        'message': 'Signal received and queued',
                        'signal': signal
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to queue signal'
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error handling signal request: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            queue_stats = self.signal_queue.get_stats()
            return jsonify({
                'status': 'running' if self.running else 'stopped',
                'port': self.port,
                'queue_stats': queue_stats
            }), 200
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get server statistics"""
            queue_stats = self.signal_queue.get_stats()
            history = self.signal_router.get_execution_history(limit=10)
            return jsonify({
                'queue_stats': queue_stats,
                'recent_executions': history
            }), 200
    
    def _process_signal(self, signal: Dict) -> None:
        """Process signal from queue"""
        try:
            result = self.signal_router.route_signal(signal)
            if result.get('success'):
                logger.info(f"Signal executed successfully: {signal.get('symbol')} {signal.get('action')}")
            else:
                logger.warning(f"Signal execution failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error processing signal: {e}", exc_info=True)
    
    def start(self) -> bool:
        """Start the signal server"""
        if self.running:
            logger.warning("Signal server is already running")
            return False
        
        try:
            # Start signal queue
            self.signal_queue.start()
            
            # Start Flask server in separate thread
            self.running = True
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=True,
                name="SignalServer"
            )
            self.server_thread.start()
            
            logger.info(f"Signal server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Error starting signal server: {e}", exc_info=True)
            self.running = False
            return False
    
    def stop(self) -> None:
        """Stop the signal server"""
        if not self.running:
            return
        
        self.running = False
        
        # Stop signal queue
        self.signal_queue.stop()
        
        # Flask doesn't have a clean shutdown, so we just mark as stopped
        # The thread will exit when the app context is closed
        logger.info("Signal server stopped")
    
    def _run_server(self) -> None:
        """Run Flask server (called in separate thread)"""
        try:
            # Disable Flask's default logging
            import logging as flask_logging
            log = flask_logging.getLogger('werkzeug')
            log.setLevel(flask_logging.WARNING)
            
            self.app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Error running signal server: {e}", exc_info=True)
            self.running = False
    
    def is_running(self) -> bool:
        """Check if server is running"""
        return self.running and self.server_thread and self.server_thread.is_alive()

