"""
Unit tests for the SummaryGenerator class.
"""

import json
import sys
from pathlib import Path
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, cast

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from cache_manager.summary_generator import SummaryGenerator, TaxonomyNode
from cache_manager.file_handler import FileHandler
from cache_manager.firm_compliance_handler import FirmComplianceHandler

@pytest.fixture
def mock_file_handler():
    """Create a mock FileHandler for testing."""
    return Mock()

@pytest.fixture
def mock_compliance_handler():
    """Create a mock FirmComplianceHandler."""
    handler = Mock()
    handler.list_compliance_reports.return_value = json.dumps({
        "status": "success",
        "reports": {
            "BIZ_001": [
                {
                    "file_name": "FirmComplianceReport_REF001_v1.json",
                    "reference_id": "REF001",
                    "timestamp": "2024-03-21T12:00:00Z"
                }
            ]
        },
        "pagination": {
            "total_items": 1,
            "total_pages": 1,
            "current_page": 1,
            "page_size": 10
        }
    })
    return handler

@pytest.fixture
def sample_report():
    """Create a sample compliance report for testing."""
    return {
        "claim": {
            "business_name": "Test Business",
            "business_ref": "BIZ_001"
        },
        "reference_id": "REF001",
        "file_name": "FirmComplianceReport_REF001_v1_20250315.json",
        "final_evaluation": {
            "overall_compliance": True,
            "alerts": [{"message": "Test alert", "severity": "Medium"}]
        }
    }

@pytest.fixture
def summary_generator(mock_file_handler, mock_compliance_handler):
    """Create a SummaryGenerator instance with mocked dependencies."""
    return SummaryGenerator(mock_file_handler, mock_compliance_handler)

def test_init(mock_file_handler, mock_compliance_handler):
    """Test SummaryGenerator initialization."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    assert generator.file_handler == mock_file_handler
    assert generator.compliance_handler == mock_compliance_handler

def test_extract_compliance_data(mock_file_handler, mock_compliance_handler, sample_report):
    """Test _extract_compliance_data method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    reports = [sample_report]
    report_summary, subsection_summary = generator._extract_compliance_data(reports, "BIZ_001")
    
    assert len(report_summary) == 1
    assert report_summary[0]["business_ref"] == "BIZ_001"
    assert report_summary[0]["reference_id"] == "REF001"
    assert report_summary[0]["overall_compliance"] is True
    assert report_summary[0]["alert_count"] == 1
    
    assert len(subsection_summary) > 0
    for section in subsection_summary:
        assert section["business_ref"] == "BIZ_001"
        assert section["reference_id"] == "REF001"
        assert "compliance" in section
        assert "alert_count" in section
        assert "explanation" in section

def test_generate_compliance_summary(mock_file_handler, mock_compliance_handler, sample_report):
    """Test generate_compliance_summary method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_file_handler.list_files.return_value = [Path("/test/cache/BIZ_001/report.json")]
    mock_file_handler.read_json.return_value = sample_report

    result = json.loads(generator.generate_compliance_summary(Path("/test/cache/BIZ_001"), "BIZ_001"))

    assert result["status"] == "success"
    assert result["business_ref"] == "BIZ_001"
    assert len(result["report_summary"]) > 0
    assert len(result["subsection_summary"]) > 0

def test_generate_all_compliance_summaries(mock_file_handler, mock_compliance_handler, sample_report):
    """Test generate_all_compliance_summaries method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_cache_path = MagicMock(spec=Path)
    mock_cache_path.exists.return_value = True
    mock_file_handler.list_files.side_effect = [
        [Path("/test/cache/BIZ_001"), Path("/test/cache/BIZ_002")],  # Firm directories
        [Path("/test/cache/BIZ_001/report.json")],  # Files for BIZ_001
        [Path("/test/cache/BIZ_002/report.json")]   # Files for BIZ_002
    ]
    mock_file_handler.read_json.return_value = sample_report

    result = json.loads(generator.generate_all_compliance_summaries(mock_cache_path))

    assert result["status"] == "success"
    assert len(result["report_summary"]) > 0
    assert len(result["subsection_summary"]) > 0

def test_build_and_merge_trees(mock_file_handler, mock_compliance_handler):
    """Test _build_tree and _merge_trees methods."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    
    data1 = {"key1": "value1", "key2": [1, 2, 3]}
    data2 = {"key1": "value2", "key3": {"nested": True}}
    
    tree1 = generator._build_tree(data1)
    tree2 = generator._build_tree(data2)
    
    assert "dict" in tree1["_types"]
    assert "list" in cast(Dict[str, TaxonomyNode], tree1["children"])["key2"]["_types"]
    assert "str" in cast(Dict[str, TaxonomyNode], tree1["children"])["key1"]["_types"]
    
    generator._merge_trees(tree1, tree2)
    assert "key3" in cast(Dict[str, TaxonomyNode], tree1["children"])
    nested = cast(Dict[str, TaxonomyNode], cast(Dict[str, TaxonomyNode], tree1["children"])["key3"]["children"])
    assert "bool" in nested["nested"]["_types"]

def test_generate_taxonomy(mock_file_handler, mock_compliance_handler, sample_report):
    """Test generate_taxonomy_from_latest_reports method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_file_handler.read_json.return_value = sample_report

    # Mock the compliance handler to return a valid JSON response
    mock_compliance_handler.list_compliance_reports.return_value = json.dumps({
        "status": "success",
        "reports": {
            "BIZ_001": [
                {
                    "file_name": "FirmComplianceReport_REF001_v1.json",
                    "reference_id": "REF001",
                    "timestamp": "2024-03-21T12:00:00Z"
                }
            ]
        }
    })

    result = generator.generate_taxonomy_from_latest_reports()

    # Check for key elements in the taxonomy tree
    assert "Types: dict" in result
    assert "claim:" in result
    assert "final_evaluation:" in result
    assert "alerts:" in result
    assert "overall_compliance:" in result

def test_generate_risk_dashboard(mock_file_handler, mock_compliance_handler, sample_report):
    """Test generate_risk_dashboard method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_file_handler.read_json.return_value = sample_report

    # Mock the compliance handler to return a valid JSON response
    mock_compliance_handler.list_compliance_reports.return_value = json.dumps({
        "status": "success",
        "reports": {
            "BIZ_001": [
                {
                    "file_name": "FirmComplianceReport_REF001_v1.json",
                    "reference_id": "REF001",
                    "timestamp": "2024-03-21T12:00:00Z"
                }
            ]
        }
    })

    result = generator.generate_risk_dashboard()

    assert "Firm Compliance Risk Dashboard" in result

def test_generate_data_quality_report(mock_file_handler, mock_compliance_handler, sample_report):
    """Test generate_data_quality_report method."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_file_handler.read_json.return_value = sample_report

    # Mock the compliance handler to return a valid JSON response
    mock_compliance_handler.list_compliance_reports.return_value = json.dumps({
        "status": "success",
        "reports": {
            "BIZ_001": [
                {
                    "file_name": "FirmComplianceReport_REF001_v1.json",
                    "reference_id": "REF001",
                    "timestamp": "2024-03-21T12:00:00Z"
                }
            ]
        }
    })

    result = generator.generate_data_quality_report()

    assert "Firm Data Quality Report" in result

def test_error_handling(mock_file_handler, mock_compliance_handler):
    """Test error handling in various methods."""
    generator = SummaryGenerator(mock_file_handler, mock_compliance_handler)
    mock_file_handler.read_json.side_effect = Exception("Test error")

    # Mock cache path to exist for all_compliance_summaries test
    mock_cache_path = MagicMock(spec=Path)
    mock_cache_path.exists.return_value = True

    # Mock compliance handler to return error response
    mock_compliance_handler.list_compliance_reports.return_value = json.dumps({
        "status": "error",
        "message": "Failed to retrieve compliance reports"
    })

    # Test compliance summary error handling
    result = json.loads(generator.generate_compliance_summary(Path("/test/cache/BIZ_001"), "BIZ_001"))
    assert result["status"] == "error"
    assert result["message"] == "Failed to retrieve compliance reports"

    # Test all compliance summaries error handling
    result = json.loads(generator.generate_all_compliance_summaries(mock_cache_path))
    assert result["status"] == "error"
    assert result["message"] == "Failed to retrieve compliance reports" 