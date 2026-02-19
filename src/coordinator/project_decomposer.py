from typing import Dict, List, Any
from abc import ABC, abstractmethod
import logging

from .master_coordinator import ProjectSpec

logger = logging.getLogger(__name__)

class ProjectDecomposer(ABC):
    """Abstract base class for project decomposition strategies"""
    
    @abstractmethod
    async def decompose(
        self,
        project_spec: ProjectSpec,
        max_sub_projects: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Decompose a project into sub-projects
        
        Returns:
            List of sub-project specifications
        """
        pass

class DefaultProjectDecomposer(ProjectDecomposer):
    """Default implementation of project decomposition"""
    
    async def decompose(
        self,
        project_spec: ProjectSpec,
        max_sub_projects: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Simple decomposition based on project requirements
        """
        sub_projects = []
        requirements = project_spec.requirements
        
        # Basic decomposition by functional