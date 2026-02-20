"""HTTP server for exposing Prometheus metrics."""

import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, Response
import uvicorn
from .metrics import metrics

logger = logging.getLogger(__name__)

class MetricsServer:
    """HTTP server for Prometheus metrics endpoint."""
    
    def __init__(self, port: int = 9090, host: str = "0.0.0.0"):
        self.port = port
        self.host = host
        self.app = FastAPI(title="AgentCoord Metrics", docs_url=None, redoc_url=None)
        self.server: Optional[uvicorn.Server] = None
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Prometheus metrics endpoint."""
            metrics_data = metrics.get_metrics()
            return Response(
                content=metrics_data,
                media_type="text/plain; charset=utf-8"
            )
            
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "service": "agentcoord-metrics"}
    
    async def start(self):
        """Start the metrics server."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False
        )
        self.server = uvicorn.Server(config)
        
        logger.info(f"Starting metrics server on {self.host}:{self.port}")
        await self.server.serve()
        
    async def stop(self):
        """Stop the metrics server."""
        if self.server:
            logger.info("Stopping metrics server")
            self.server.should_exit = True
            await asyncio.sleep(0.1)  # Give server time to shutdown gracefully

# Global metrics server instance
_metrics_server: Optional[MetricsServer] = None

async def start_metrics_server(port: int = 9090, host: str = "0.0.0.0"):
    """Start the global metrics server."""
    global _metrics_server
    if _metrics_server is None:
        _metrics_server = MetricsServer(port=port, host=host)
        await _metrics_server.start()
        
async def stop_metrics_server():
    """Stop the global metrics server."""
    global _metrics_server
    if _metrics_server:
        await _metrics_server.stop()
        _metrics_server = None