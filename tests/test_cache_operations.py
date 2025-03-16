"""
test_cache_operations.py

Unit tests for the cache_operations module.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from cache_manager.cache_operations import CacheManager
from cache_manager.agents import AgentName

@pytest.fixture
def mock_file_handler():
    """Create a mock FileHandler instance."""
    handler = MagicMock()
    handler.get_last_modified.return_value = datetime.now()
    return handler

@pytest.fixture
def cache_manager(tmp_path, mock_file_handler):
    """Create a CacheManager instance with a temporary directory."""
    with patch('cache_manager.cache_operations.FileHandler', return_value=mock_file_handler):
        manager = CacheManager(cache_folder=tmp_path)
        return manager

def test_init_creates_cache_folder(tmp_path):
    """Test that CacheManager creates the cache folder if it doesn't exist."""
    cache_path = tmp_path / "cache"
    CacheManager(cache_folder=cache_path)
    assert cache_path.exists()
    assert cache_path.is_dir()

def test_clear_cache_nonexistent_business(cache_manager):
    """Test clearing cache for a nonexistent business."""
    result = json.loads(cache_manager.clear_cache("NONEXISTENT"))
    assert result["status"] == "warning"
    assert "No cache found for business" in result["message"]

def test_clear_cache_success(tmp_path, cache_manager, mock_file_handler):
    """Test successful cache clearing for a business."""
    # Create test directories
    business_path = tmp_path / "BIZ_001"
    business_path.mkdir()
    (business_path / "SEC_Search_Agent").mkdir()
    (business_path / AgentName.FIRM_COMPLIANCE_REPORT.value).mkdir()

    result = json.loads(cache_manager.clear_cache("BIZ_001"))
    
    assert result["status"] == "success"
    assert "SEC_Search_Agent" in result["cleared_agents"]
    assert AgentName.FIRM_COMPLIANCE_REPORT.value not in result["cleared_agents"]
    mock_file_handler.delete_path.assert_called()

def test_clear_all_cache(tmp_path, cache_manager, mock_file_handler):
    """Test clearing cache for all businesses."""
    # Create test directories
    for biz in ["BIZ_001", "BIZ_002"]:
        biz_path = tmp_path / biz
        biz_path.mkdir()
        (biz_path / "SEC_Search_Agent").mkdir()

    result = json.loads(cache_manager.clear_all_cache())
    
    assert result["status"] == "success"
    assert len(result["cleared_businesses"]) == 2
    assert result["total_cleared_agents"] > 0
    mock_file_handler.delete_path.assert_called()

def test_clear_agent_cache_invalid_agent(cache_manager):
    """Test clearing cache with an invalid agent name."""
    result = json.loads(cache_manager.clear_agent_cache("BIZ_001", "INVALID_AGENT"))
    assert result["status"] == "error"
    assert "Invalid agent name" in result["message"]

def test_clear_agent_cache_nonexistent(cache_manager):
    """Test clearing cache for a nonexistent agent directory."""
    result = json.loads(cache_manager.clear_agent_cache("BIZ_001", AgentName.FIRM_COMPLIANCE_REPORT.value))
    assert result["status"] == "warning"
    assert "No cache found for agent" in result["message"]

def test_clear_agent_cache_success(tmp_path, cache_manager, mock_file_handler):
    """Test successful clearing of an agent's cache."""
    # Create test directory
    agent_path = tmp_path / "BIZ_001" / AgentName.FIRM_COMPLIANCE_REPORT.value
    agent_path.mkdir(parents=True)

    mock_file_handler.delete_path.return_value = True
    result = json.loads(cache_manager.clear_agent_cache("BIZ_001", AgentName.FIRM_COMPLIANCE_REPORT.value))
    
    assert result["status"] == "success"
    assert "Cleared cache for agent" in result["message"]
    mock_file_handler.delete_path.assert_called_once()

def test_list_cache_nonexistent_folder(cache_manager):
    """Test listing cache when the cache folder doesn't exist."""
    result = json.loads(cache_manager.list_cache())
    assert result["status"] == "success"
    assert result["message"] == "Listed all businesses with cache (page 1 of 0)"
    assert result["cache"]["businesses"] == []
    assert result["pagination"]["total_items"] == 0
    assert result["pagination"]["total_pages"] == 0

def test_list_cache_all_businesses(tmp_path, cache_manager):
    """Test listing cache for all businesses with pagination."""
    # Create test directories
    for biz in ["BIZ_001", "BIZ_002", "BIZ_003"]:
        (tmp_path / biz).mkdir()

    # Test first page
    result = json.loads(cache_manager.list_cache(page=1, page_size=2))
    assert result["status"] == "success"
    assert len(result["cache"]["businesses"]) == 2
    assert result["pagination"]["total_pages"] == 2
    
    # Test second page
    result = json.loads(cache_manager.list_cache(page=2, page_size=2))
    assert len(result["cache"]["businesses"]) == 1

def test_list_cache_specific_business(tmp_path, cache_manager, mock_file_handler):
    """Test listing cache for a specific business."""
    # Create test structure
    biz_path = tmp_path / "BIZ_001"
    biz_path.mkdir()
    agent_path = biz_path / "SEC_Search_Agent"
    agent_path.mkdir()
    
    # Mock file listing
    mock_file = MagicMock()
    mock_file.name = "test_file.json"
    mock_file_handler.list_files.return_value = [mock_file]
    mock_file_handler.get_last_modified.return_value = datetime.now()

    result = json.loads(cache_manager.list_cache("BIZ_001"))
    
    assert result["status"] == "success"
    assert "BIZ_001" in result["cache"]
    assert "SEC_Search_Agent" in result["cache"]["BIZ_001"]

def test_cleanup_stale_cache(tmp_path, cache_manager, mock_file_handler):
    """Test cleaning up stale cache files."""
    # Create test structure
    biz_path = tmp_path / "BIZ_001"
    biz_path.mkdir()
    agent_path = biz_path / "SEC_Search_Agent"
    agent_path.mkdir()
    
    # Mock file operations
    old_date = datetime.now() - timedelta(days=100)
    mock_file = MagicMock()
    mock_file.name = "old_file.json"
    mock_file_handler.list_files.return_value = [mock_file]
    mock_file_handler.get_last_modified.return_value = old_date

    result = json.loads(cache_manager.cleanup_stale_cache())
    
    assert result["status"] == "success"
    assert "Deleted" in result["message"]
    mock_file_handler.delete_path.assert_called()

def test_cleanup_stale_cache_no_old_files(tmp_path, cache_manager, mock_file_handler):
    """Test cleaning up stale cache when no files are old enough."""
    # Create test structure
    biz_path = tmp_path / "BIZ_001"
    biz_path.mkdir()
    
    # Mock file operations with recent date
    mock_file_handler.get_last_modified.return_value = datetime.now()

    result = json.loads(cache_manager.cleanup_stale_cache())
    
    assert result["status"] == "success"
    assert len(result["deleted_files"]) == 0
    mock_file_handler.delete_path.assert_not_called()

def test_error_handling(tmp_path, cache_manager, mock_file_handler):
    """Test error handling in various operations."""
    mock_file_handler.delete_path.side_effect = Exception("Test error")
    
    # Test clear_cache error handling
    biz_path = tmp_path / "BIZ_001"
    biz_path.mkdir()
    (biz_path / "SEC_Search_Agent").mkdir()
    
    result = json.loads(cache_manager.clear_cache("BIZ_001"))
    assert "SEC_Search_Agent" not in result.get("cleared_agents", []) 