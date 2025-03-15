"""
test_firm_compliance_report_agent.py

Unit tests for the firm_compliance_report_agent module.
"""

from copy import deepcopy
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock

from agents.firm_compliance_report_agent import (
    has_significant_changes,
    save_compliance_report,
    CACHE_FOLDER,
    DATE_FORMAT
)

# Sample report for testing
SAMPLE_REPORT = {
    "reference_id": "TEST123",
    "claim": {
        "business_name": "Test Business",
        "business_ref": "BIZ_001"
    },
    "search_evaluation": {
        "compliance": False
    },
    "registration_status": {
        "compliance": True
    },
    "regulatory_oversight": {
        "compliance": True
    },
    "disclosures": {
        "compliance": True
    },
    "financials": {
        "compliance": True
    },
    "legal": {
        "compliance": True
    },
    "qualifications": {
        "compliance": True
    },
    "data_integrity": {
        "compliance": True
    },
    "final_evaluation": {
        "overall_compliance": False,
        "alerts": [],
        "alert_summary": {
            "high": 0,
            "medium": 0,
            "low": 0
        }
    }
}

@pytest.fixture
def sample_report():
    """Return a deep copy of the sample report to prevent modification of the original."""
    return deepcopy(SAMPLE_REPORT)

def test_has_significant_changes_overall_compliance(sample_report):
    """Test detection of changes in overall compliance."""
    old_report = deepcopy(sample_report)
    new_report = deepcopy(sample_report)
    new_report["final_evaluation"]["overall_compliance"] = not old_report["final_evaluation"]["overall_compliance"]
    
    assert has_significant_changes(new_report, old_report) is True

def test_has_significant_changes_section_compliance(sample_report):
    """Test detection of changes in section compliance."""
    sections = [
        "search_evaluation",
        "registration_status",
        "regulatory_oversight",
        "disclosures",
        "financials",
        "legal",
        "qualifications",
        "data_integrity"
    ]
    
    for section in sections:
        old_report = deepcopy(sample_report)
        new_report = deepcopy(sample_report)
        new_report[section]["compliance"] = not old_report[section]["compliance"]
        
        assert has_significant_changes(new_report, old_report) is True, f"Failed to detect change in {section}"

def test_has_significant_changes_alert_count(sample_report):
    """Test detection of changes in alert count."""
    old_report = deepcopy(sample_report)
    new_report = deepcopy(sample_report)
    new_report["final_evaluation"]["alerts"] = [
        {"type": "test", "severity": "HIGH", "message": "Test alert"}
    ]
    
    assert has_significant_changes(new_report, old_report) is True

def test_has_significant_changes_alert_severity(sample_report):
    """Test detection of changes in alert severity distribution."""
    old_report = deepcopy(sample_report)
    new_report = deepcopy(sample_report)
    new_report["final_evaluation"]["alert_summary"] = {
        "high": 1,
        "medium": 0,
        "low": 0
    }
    
    assert has_significant_changes(new_report, old_report) is True

def test_has_significant_changes_no_changes(sample_report):
    """Test that no changes are detected when reports are identical."""
    old_report = deepcopy(sample_report)
    new_report = deepcopy(sample_report)
    
    assert has_significant_changes(new_report, old_report) is False

def test_has_significant_changes_handles_missing_fields(sample_report):
    """Test handling of missing fields in reports."""
    old_report = deepcopy(sample_report)
    new_report = deepcopy(sample_report)
    
    # Remove some fields
    del new_report["final_evaluation"]["alert_summary"]
    del old_report["final_evaluation"]["alerts"]
    
    # Should return True when fields are missing (conservative approach)
    assert has_significant_changes(new_report, old_report) is True

@pytest.mark.parametrize("invalid_report", [
    None,
    {"missing_required_fields": True},
    {"final_evaluation": None},
    {"final_evaluation": {"missing_required_fields": True}}
])
def test_save_compliance_report_invalid_report(invalid_report):
    """Test handling of invalid report formats."""
    assert save_compliance_report(invalid_report) is False

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_new_report(mock_file, mock_glob, mock_mkdir, sample_report):
    """Test saving a new report with no existing versions."""
    mock_glob.return_value = []
    
    assert save_compliance_report(sample_report) is True
    
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    mock_file.assert_called_once()
    handle = mock_file()
    
    # Check the full JSON content was written
    written_data = "".join(call[0][0] for call in handle.write.call_args_list)
    assert json.loads(written_data) == sample_report

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_with_existing_version(mock_file, mock_glob, mock_mkdir, sample_report):
    """Test saving a report when a version already exists."""
    # Mock existing file
    current_date = datetime.now().strftime(DATE_FORMAT)
    mock_existing_file = MagicMock()
    mock_existing_file.name = f"FirmComplianceReport_TEST123_v1_{current_date}.json"
    mock_existing_file.stem = f"FirmComplianceReport_TEST123_v1_{current_date}"
    mock_glob.return_value = [mock_existing_file]
    
    # Mock reading existing report with different content
    existing_report = deepcopy(sample_report)
    existing_report["final_evaluation"]["overall_compliance"] = not sample_report["final_evaluation"]["overall_compliance"]
    mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(existing_report)
    
    # Configure mock to handle both read and write operations
    mock_file.side_effect = [
        mock_open(read_data=json.dumps(existing_report)).return_value,
        mock_open().return_value
    ]
    
    assert save_compliance_report(sample_report) is True
    
    # Verify new version was written
    calls = mock_file.call_args_list
    assert len(calls) == 2  # One read, one write

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_no_changes(mock_file, mock_glob, mock_mkdir, sample_report):
    """Test that no new version is saved when there are no significant changes."""
    # Mock existing file
    current_date = datetime.now().strftime(DATE_FORMAT)
    mock_existing_file = MagicMock()
    mock_existing_file.name = f"FirmComplianceReport_TEST123_v1_{current_date}.json"
    mock_existing_file.stem = f"FirmComplianceReport_TEST123_v1_{current_date}"
    mock_glob.return_value = [mock_existing_file]
    
    # Mock reading existing report with same content
    mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(sample_report)
    
    assert save_compliance_report(sample_report) is True
    
    # Verify no new version was written
    calls = mock_file.call_args_list
    assert len(calls) == 1  # Only read, no write

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_custom_business_ref(mock_file, mock_glob, mock_mkdir, sample_report):
    """Test saving a report with a custom business_ref."""
    mock_glob.return_value = []
    custom_ref = "CUSTOM_BIZ_001"
    
    assert save_compliance_report(sample_report, business_ref=custom_ref) is True
    
    # Verify directory creation
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    assert mock_mkdir.called

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_handles_io_error(mock_file, mock_glob, mock_mkdir, sample_report):
    """Test handling of IO errors when saving reports."""
    mock_glob.return_value = []
    mock_file.side_effect = IOError("Test IO Error")
    
    assert save_compliance_report(sample_report) is False

@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.glob")
@patch("builtins.open", new_callable=mock_open)
def test_save_compliance_report_integration(mock_file, mock_glob, mock_mkdir, sample_report):
    """Integration test for saving reports with version handling."""
    current_date = datetime.now().strftime(DATE_FORMAT)
    business_ref = sample_report["claim"]["business_ref"]  # "BIZ_001"
    
    # Create mock files with comparable behavior
    mock_file1 = MagicMock()
    mock_file1.name = f"FirmComplianceReport_{business_ref}_v1_{current_date}.json"
    mock_file1.stem = f"FirmComplianceReport_{business_ref}_v1_{current_date}"
    mock_file1.__lt__ = lambda self, other: self.name < other.name  # Enable sorting
    
    mock_file2 = MagicMock()
    mock_file2.name = f"FirmComplianceReport_{business_ref}_v2_{current_date}.json"
    mock_file2.stem = f"FirmComplianceReport_{business_ref}_v2_{current_date}"
    mock_file2.__lt__ = lambda self, other: self.name < other.name  # Enable sorting
    
    mock_existing_files = [mock_file1, mock_file2]
    mock_glob.return_value = mock_existing_files
    
    # Mock reading latest version with different content
    existing_report = deepcopy(sample_report)
    existing_report["final_evaluation"]["overall_compliance"] = not sample_report["final_evaluation"]["overall_compliance"]
    mock_file.return_value.__enter__.return_value.read.return_value = json.dumps(existing_report)
    mock_file.side_effect = [
        mock_open(read_data=json.dumps(existing_report)).return_value,
        mock_open().return_value
    ]
    
    assert save_compliance_report(sample_report) is True
    
    # Verify new version was written with incremented version number
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
    assert len(mock_file.call_args_list) == 2  # One read, one write 