"""
Unit tests for the cache_manager CLI module.

Tests the argument parsing, command execution, and error handling of the CLI interface.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import argparse

from cache_manager.cli import setup_argparser, format_output, main
from firm_cache_manager import FirmCacheManager
from cache_manager.firm_compliance_handler import FirmComplianceHandler
from cache_manager.summary_generator import SummaryGenerator
from cache_manager.file_handler import FileHandler

@pytest.fixture
def mock_cache_manager():
    """Fixture providing a mocked FirmCacheManager."""
    mock = Mock(spec=FirmCacheManager)
    mock.cache_folder = Path("/mock/cache")
    return mock

@pytest.fixture
def mock_compliance_handler():
    """Fixture providing a mocked FirmComplianceHandler."""
    return Mock(spec=FirmComplianceHandler)

@pytest.fixture
def mock_file_handler():
    """Fixture providing a mocked FileHandler."""
    return Mock(spec=FileHandler)

@pytest.fixture
def mock_summary_generator():
    """Fixture providing a mocked SummaryGenerator."""
    return Mock(spec=SummaryGenerator)

def test_setup_argparser():
    """Test argument parser setup and configuration."""
    parser = setup_argparser()
    assert isinstance(parser, argparse.ArgumentParser)
    
    # Test cache location argument
    args = parser.parse_args(["--cache-folder", "/test/cache"])
    assert args.cache_folder == "/test/cache"
    
    # Test cache operations arguments
    args = parser.parse_args(["--clear-cache", "BIZ_001"])
    assert args.clear_cache == "BIZ_001"
    
    args = parser.parse_args(["--clear-cache"])
    assert args.clear_cache == "ALL"
    
    args = parser.parse_args(["--clear-compliance", "BIZ_001"])
    assert args.clear_compliance == "BIZ_001"
    
    args = parser.parse_args(["--clear-agent", "BIZ_001", "agent1"])
    assert args.clear_agent == ["BIZ_001", "agent1"]
    
    # Test compliance report operations
    args = parser.parse_args(["--list-compliance-reports", "BIZ_001"])
    assert args.list_compliance_reports == "BIZ_001"
    
    args = parser.parse_args(["--get-latest-compliance", "BIZ_001"])
    assert args.get_latest_compliance == "BIZ_001"
    
    args = parser.parse_args(["--get-compliance-by-ref", "BIZ_001", "REF123"])
    assert args.get_compliance_by_ref == ["BIZ_001", "REF123"]
    
    # Test summary operations
    args = parser.parse_args(["--generate-compliance-summary", "BIZ_001"])
    assert args.generate_compliance_summary == "BIZ_001"
    
    args = parser.parse_args(["--generate-all-summaries"])
    assert args.generate_all_summaries is True
    
    # Test analysis operations
    args = parser.parse_args(["--generate-taxonomy"])
    assert args.generate_taxonomy is True
    
    args = parser.parse_args(["--generate-risk-dashboard"])
    assert args.generate_risk_dashboard is True
    
    args = parser.parse_args(["--generate-data-quality"])
    assert args.generate_data_quality is True
    
    # Test pagination options
    args = parser.parse_args(["--page", "2", "--page-size", "20"])
    assert args.page == 2
    assert args.page_size == 20

def test_format_output(capsys):
    """Test output formatting for different types of results."""
    # Test JSON string
    json_str = '{"status": "success", "data": [1, 2, 3]}'
    format_output(json_str)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "success", "data": [1, 2, 3]}
    
    # Test plain string
    plain_str = "This is a plain string"
    format_output(plain_str)
    captured = capsys.readouterr()
    assert captured.out.strip() == plain_str
    
    # Test dictionary
    dict_result = {"status": "success", "count": 42}
    format_output(dict_result)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == dict_result

@patch("cache_manager.cli.FirmCacheManager")
@patch("cache_manager.cli.FirmComplianceHandler")
@patch("cache_manager.cli.FileHandler")
@patch("cache_manager.cli.SummaryGenerator")
def test_main_clear_cache(
    mock_summary_gen_cls,
    mock_file_handler_cls,
    mock_compliance_cls,
    mock_cache_cls,
    mock_cache_manager,
    capsys
):
    """Test main function with clear cache command."""
    mock_cache_cls.return_value = mock_cache_manager
    mock_cache_manager.clear_cache.return_value = json.dumps({"status": "success"})
    
    with patch("sys.argv", ["cli.py", "--clear-cache", "BIZ_001"]):
        main()
        
    mock_cache_manager.clear_cache.assert_called_once_with("BIZ_001")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"status": "success"}

@patch("cache_manager.cli.FirmCacheManager")
@patch("cache_manager.cli.FirmComplianceHandler")
@patch("cache_manager.cli.FileHandler")
@patch("cache_manager.cli.SummaryGenerator")
def test_main_generate_compliance_summary(
    mock_summary_gen_cls,
    mock_file_handler_cls,
    mock_compliance_cls,
    mock_cache_cls,
    mock_cache_manager,
    mock_summary_generator,
    capsys
):
    """Test main function with generate compliance summary command."""
    mock_cache_cls.return_value = mock_cache_manager
    mock_summary_gen_cls.return_value = mock_summary_generator
    
    summary_result = {
        "status": "success",
        "business_ref": "BIZ_001",
        "report_summary": []
    }
    mock_summary_generator.generate_compliance_summary.return_value = json.dumps(summary_result)
    
    with patch("sys.argv", ["cli.py", "--generate-compliance-summary", "BIZ_001"]):
        main()
        
    mock_summary_generator.generate_compliance_summary.assert_called_once_with(
        firm_path=mock_cache_manager.cache_folder / "BIZ_001",
        business_ref="BIZ_001",
        page=1,
        page_size=10
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out) == summary_result

@patch("cache_manager.cli.FirmCacheManager")
@patch("cache_manager.cli.FirmComplianceHandler")
@patch("cache_manager.cli.FileHandler")
@patch("cache_manager.cli.SummaryGenerator")
def test_main_error_handling(
    mock_summary_gen_cls,
    mock_file_handler_cls,
    mock_compliance_cls,
    mock_cache_cls,
    mock_cache_manager,
    capsys
):
    """Test main function error handling."""
    mock_cache_cls.return_value = mock_cache_manager
    mock_cache_manager.clear_cache.side_effect = Exception("Test error")
    
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["cli.py", "--clear-cache", "BIZ_001"]):
            main()
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    error_output = json.loads(captured.out)
    assert error_output["status"] == "error"
    assert error_output["message"] == "Test error"
    assert error_output["error_type"] == "Exception"

@patch("cache_manager.cli.FirmCacheManager")
@patch("cache_manager.cli.FirmComplianceHandler")
@patch("cache_manager.cli.FileHandler")
@patch("cache_manager.cli.SummaryGenerator")
def test_main_analysis_commands(
    mock_summary_gen_cls,
    mock_file_handler_cls,
    mock_compliance_cls,
    mock_cache_cls,
    mock_cache_manager,
    mock_summary_generator,
    capsys
):
    """Test main function with analysis commands."""
    mock_cache_cls.return_value = mock_cache_manager
    mock_summary_gen_cls.return_value = mock_summary_generator
    
    # Test taxonomy generation
    mock_summary_generator.generate_taxonomy_from_latest_reports.return_value = "Taxonomy tree"
    with patch("sys.argv", ["cli.py", "--generate-taxonomy"]):
        main()
    mock_summary_generator.generate_taxonomy_from_latest_reports.assert_called_once()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Taxonomy tree"
    
    # Test risk dashboard generation
    mock_summary_generator.generate_risk_dashboard.return_value = "Risk dashboard"
    with patch("sys.argv", ["cli.py", "--generate-risk-dashboard"]):
        main()
    mock_summary_generator.generate_risk_dashboard.assert_called_once()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Risk dashboard"
    
    # Test data quality report generation
    mock_summary_generator.generate_data_quality_report.return_value = "Data quality report"
    with patch("sys.argv", ["cli.py", "--generate-data-quality"]):
        main()
    mock_summary_generator.generate_data_quality_report.assert_called_once()
    captured = capsys.readouterr()
    assert captured.out.strip() == "Data quality report"

@patch("cache_manager.cli.FirmCacheManager")
@patch("cache_manager.cli.FirmComplianceHandler")
@patch("cache_manager.cli.FileHandler")
@patch("cache_manager.cli.SummaryGenerator")
def test_main_compliance_operations(
    mock_summary_gen_cls,
    mock_file_handler_cls,
    mock_compliance_cls,
    mock_cache_cls,
    mock_cache_manager,
    capsys
):
    """Test main function with compliance report operations."""
    mock_cache_cls.return_value = mock_cache_manager
    
    # Test get latest compliance report
    mock_cache_manager.get_latest_compliance_report.return_value = json.dumps({
        "status": "success",
        "report": {"id": "latest"}
    })
    with patch("sys.argv", ["cli.py", "--get-latest-compliance", "BIZ_001"]):
        main()
    mock_cache_manager.get_latest_compliance_report.assert_called_once_with("BIZ_001")
    captured = capsys.readouterr()
    assert json.loads(captured.out)["report"]["id"] == "latest"
    
    # Test get compliance by reference
    mock_cache_manager.get_compliance_report_by_ref.return_value = json.dumps({
        "status": "success",
        "report": {"id": "REF123"}
    })
    with patch("sys.argv", ["cli.py", "--get-compliance-by-ref", "BIZ_001", "REF123"]):
        main()
    mock_cache_manager.get_compliance_report_by_ref.assert_called_once_with("BIZ_001", "REF123")
    captured = capsys.readouterr()
    assert json.loads(captured.out)["report"]["id"] == "REF123"
    
    # Test list compliance reports
    mock_cache_manager.list_compliance_reports.return_value = json.dumps({
        "status": "success",
        "reports": []
    })
    with patch("sys.argv", ["cli.py", "--list-compliance-reports", "BIZ_001"]):
        main()
    mock_cache_manager.list_compliance_reports.assert_called_once_with(
        business_ref="BIZ_001",
        page=1,
        page_size=10
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out)["status"] == "success" 