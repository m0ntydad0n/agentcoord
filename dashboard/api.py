"""
API for external systems to update the dashboard
"""
import asyncio
import json
from typing import Dict, Any
from .live_dashboard import LiveDashboard

class DashboardAPI:
    def __init__(self, dashboard: LiveDashboard):
        self.dashboard = dashboard
    
    async def update_task_status(self, task_id: str, status: str, progress: int = None, eta: str = None):
        """Update task status via API"""
        updates = {"status": status}
        if progress is not None:
            updates["progress"]