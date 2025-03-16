"""
cache_operations.py

This module provides the CacheManager class that handles general cache operations for
regulatory data related to business entities. It supports clearing cache (excluding
compliance reports), clearing all cache across businesses, clearing specific agent
caches, listing cached files with pagination, and cleaning up stale cache based on TTL.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

from .agents import AgentName
from .config import DEFAULT_CACHE_FOLDER, CACHE_TTL_DAYS
from .file_handler import FileHandler

# Configure logging
logger = logging.getLogger("CacheOperations")

class CacheManager:
    """Manages general cache operations for business regulatory data."""
    
    def __init__(self, cache_folder: Path = DEFAULT_CACHE_FOLDER, ttl_days: int = CACHE_TTL_DAYS):
        """Initialize the cache manager.
        
        Args:
            cache_folder: Cache directory (default from config)
            ttl_days: Cache expiration period in days (default from config)
        """
        self.cache_folder = cache_folder
        self.ttl_days = ttl_days
        self.file_handler = FileHandler(cache_folder)
        
        if not self.cache_folder.exists():
            logger.warning(f"Cache folder does not exist: {self.cache_folder}")
            self.cache_folder.mkdir(parents=True, exist_ok=True)

    def clear_cache(self, business_ref: str) -> str:
        """Clear all agent caches except FirmComplianceReport for a business.
        
        Args:
            business_ref: Business reference ID (e.g., "BIZ_001")
            
        Returns:
            JSON string with status, cleared agents, and message
        """
        biz_path = self.cache_folder / business_ref
        if not biz_path.exists():
            return json.dumps({
                "business_ref": business_ref,
                "status": "warning",
                "message": f"No cache found for business {business_ref}"
            })
        
        cleared_agents = []
        for item in biz_path.iterdir():
            if (item.is_dir() and 
                item.name != AgentName.FIRM_COMPLIANCE_REPORT.value):
                try:
                    self.file_handler.delete_path(item)
                    cleared_agents.append(item.name)
                except Exception as e:
                    logger.error(f"Failed to clear cache for {item.name}: {str(e)}")
        
        return json.dumps({
            "business_ref": business_ref,
            "cleared_agents": cleared_agents,
            "status": "success",
            "message": f"Cleared cache for {len(cleared_agents)} agents"
        })

    def clear_all_cache(self) -> str:
        """Clear all agent caches except FirmComplianceReport across all businesses.
        
        Returns:
            JSON string with cleared businesses and agent counts
        """
        cleared_businesses = []
        total_cleared_agents = 0
        
        for biz_path in self.cache_folder.iterdir():
            if biz_path.is_dir():
                try:
                    result = json.loads(self.clear_cache(biz_path.name))
                    if result["status"] == "success":
                        cleared_businesses.append({
                            "business_ref": biz_path.name,
                            "cleared_agents": result["cleared_agents"]
                        })
                        total_cleared_agents += len(result["cleared_agents"])
                except Exception as e:
                    logger.error(f"Failed to clear cache for {biz_path.name}: {str(e)}")
        
        return json.dumps({
            "cleared_businesses": cleared_businesses,
            "total_cleared_agents": total_cleared_agents,
            "status": "success",
            "message": f"Cleared cache for {len(cleared_businesses)} businesses, {total_cleared_agents} agents total"
        })

    def clear_agent_cache(self, business_ref: str, agent_name: str) -> str:
        """Clear cache for a specific agent under a business.
        
        Args:
            business_ref: Business reference ID (e.g., "BIZ_001")
            agent_name: Name of the agent (e.g., "SEC_Search_Agent")
            
        Returns:
            JSON string with status and message
        """
        if agent_name not in [a.value for a in AgentName]:
            return json.dumps({
                "business_ref": business_ref,
                "agent_name": agent_name,
                "status": "error",
                "message": f"Invalid agent name: {agent_name}"
            })
        
        agent_path = self.cache_folder / business_ref / agent_name
        if not agent_path.exists():
            return json.dumps({
                "business_ref": business_ref,
                "agent_name": agent_name,
                "status": "warning",
                "message": f"No cache found for agent {agent_name} under {business_ref}"
            })
        
        try:
            self.file_handler.delete_path(agent_path)
            return json.dumps({
                "business_ref": business_ref,
                "agent_name": agent_name,
                "status": "success",
                "message": f"Cleared cache for agent {agent_name} under {business_ref}"
            })
        except Exception as e:
            logger.error(f"Failed to clear cache for {agent_name}: {str(e)}")
            return json.dumps({
                "business_ref": business_ref,
                "agent_name": agent_name,
                "status": "error",
                "message": f"Failed to clear cache: {str(e)}"
            })

    def list_cache(self, business_ref: Optional[str] = None, page: int = 1, page_size: int = 10) -> str:
        """List cached files for all businesses or a specific business with pagination.
        
        Args:
            business_ref: Optional business reference ID (None or "ALL" for all)
            page: Page number (default: 1)
            page_size: Items per page (default: 10)
            
        Returns:
            JSON string with cache contents and pagination info
        """
        if not self.cache_folder.exists():
            return json.dumps({
                "status": "warning",
                "message": "Cache folder does not exist",
                "cache": {},
                "pagination": {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size
                }
            })
        
        try:
            # List all businesses
            if business_ref is None or business_ref == "ALL":
                businesses = [b.name for b in self.cache_folder.iterdir() if b.is_dir()]
                total_items = len(businesses)
                total_pages = (total_items + page_size - 1) // page_size
                
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_businesses = businesses[start_idx:end_idx]
                
                return json.dumps({
                    "status": "success",
                    "message": f"Listed all businesses with cache (page {page} of {total_pages})",
                    "cache": {"businesses": paginated_businesses},
                    "pagination": {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": page,
                        "page_size": page_size
                    }
                })
            
            # List specific business
            biz_path = self.cache_folder / business_ref
            if not biz_path.exists():
                return json.dumps({
                    "status": "warning",
                    "message": f"No cache found for business {business_ref}",
                    "cache": {},
                    "pagination": {
                        "total_items": 0,
                        "total_pages": 0,
                        "current_page": page,
                        "page_size": page_size
                    }
                })
            
            cache_contents: Dict[str, Dict[str, List[Dict[str, str]]]] = {business_ref: {}}
            all_files = []
            
            # Collect all files with their agent names
            for agent_dir in biz_path.iterdir():
                if agent_dir.is_dir():
                    agent_files = []
                    for file_path in self.file_handler.list_files(agent_dir, "*.json"):
                        last_modified = self.file_handler.get_last_modified(file_path)
                        agent_files.append({
                            "file_name": file_path.name,
                            "last_modified": last_modified.isoformat()
                        })
                    # Always add the agent directory to the cache contents, even if empty
                    cache_contents[business_ref][agent_dir.name] = agent_files
                    all_files.extend(agent_files)
            
            # Apply pagination
            total_items = len(all_files)
            total_pages = (total_items + page_size - 1) // page_size
            
            return json.dumps({
                "status": "success",
                "message": f"Cache contents for {business_ref} (page {page} of {total_pages})",
                "cache": cache_contents,
                "pagination": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": page,
                    "page_size": page_size
                }
            })
            
        except Exception as e:
            logger.error(f"Failed to list cache: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to list cache: {str(e)}",
                "cache": {},
                "pagination": {
                    "total_items": 0,
                    "total_pages": 0,
                    "current_page": page,
                    "page_size": page_size
                }
            })

    def cleanup_stale_cache(self) -> str:
        """Delete cache files older than ttl_days, excluding FirmComplianceReport.
        
        Returns:
            JSON string with deleted files
        """
        if not self.cache_folder.exists():
            return json.dumps({
                "status": "warning",
                "message": "Cache folder does not exist",
                "deleted_files": []
            })
        
        cutoff_date = datetime.now() - timedelta(days=self.ttl_days)
        deleted_files = []
        
        try:
            for biz_path in self.cache_folder.iterdir():
                if not biz_path.is_dir():
                    continue
                    
                for agent_dir in biz_path.iterdir():
                    if (agent_dir.is_dir() and 
                        agent_dir.name != AgentName.FIRM_COMPLIANCE_REPORT.value):
                        for file_path in self.file_handler.list_files(agent_dir, "*.json"):
                            try:
                                last_modified = self.file_handler.get_last_modified(file_path)
                                if last_modified < cutoff_date:
                                    if self.file_handler.delete_path(file_path):
                                        deleted_files.append(str(file_path.relative_to(self.cache_folder)))
                            except Exception as e:
                                logger.error(f"Failed to process {file_path}: {str(e)}")
            
            return json.dumps({
                "status": "success",
                "message": f"Deleted {len(deleted_files)} stale cache files",
                "deleted_files": deleted_files
            })
            
        except Exception as e:
            logger.error(f"Failed to cleanup stale cache: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to cleanup stale cache: {str(e)}",
                "deleted_files": deleted_files
            }) 