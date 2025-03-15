import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import re

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CACHE_FOLDER = Path("cache/compliance_reports")
DATE_FORMAT = "%Y%m%d"

def has_significant_changes(new_report: dict, old_report: dict) -> bool:
    """
    Compare two compliance reports to detect significant changes.
    Returns True if significant changes are found, False otherwise.
    """
    try:
        # Check if any required fields are missing
        required_fields = ["final_evaluation"]
        for field in required_fields:
            if field not in new_report or field not in old_report:
                logging.debug(f"Missing required field: {field}")
                return True

        # Check if any fields in final_evaluation are missing
        required_eval_fields = ["overall_compliance", "alert_summary", "alerts"]
        for field in required_eval_fields:
            if field not in new_report["final_evaluation"] or field not in old_report["final_evaluation"]:
                logging.debug(f"Missing field in final_evaluation: {field}")
                return True

        # Compare overall compliance
        if new_report["final_evaluation"]["overall_compliance"] != old_report["final_evaluation"]["overall_compliance"]:
            logging.debug("Overall compliance changed")
            return True

        # Compare alert summary
        new_summary = new_report["final_evaluation"]["alert_summary"]
        old_summary = old_report["final_evaluation"]["alert_summary"]
        for severity in ["high", "medium", "low"]:
            if new_summary.get(severity, 0) != old_summary.get(severity, 0):
                logging.debug(f"Alert count changed for severity {severity}")
                return True

        # Compare alerts
        new_alerts = new_report["final_evaluation"]["alerts"]
        old_alerts = old_report["final_evaluation"]["alerts"]
        if len(new_alerts) != len(old_alerts):
            logging.debug("Alert count changed")
            return True

        # Compare alert contents
        for new_alert, old_alert in zip(sorted(new_alerts, key=lambda x: x.get("type", "")), 
                                      sorted(old_alerts, key=lambda x: x.get("type", ""))):
            if (new_alert.get("type") != old_alert.get("type") or
                new_alert.get("severity") != old_alert.get("severity") or
                new_alert.get("message") != old_alert.get("message")):
                logging.debug("Alert content changed")
                return True

        # Compare section compliance
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
            if section in new_report and section in old_report:
                new_compliance = new_report[section].get("compliance")
                old_compliance = old_report[section].get("compliance")
                if new_compliance != old_compliance:
                    logging.debug(f"Section compliance changed for {section}: {old_compliance} -> {new_compliance}")
                    return True
            else:
                # If any section is missing in either report, consider it a change
                logging.debug(f"Missing section: {section}")
                return True

        logging.debug("No significant changes detected")
        return False

    except Exception as e:
        logging.error(f"Error comparing reports: {e}")
        # Return True on error to ensure a new version is created
        return True

def get_version_number(filename: str) -> int:
    """Extract version number from filename."""
    match = re.search(r"_v(\d+)_", filename)
    return int(match.group(1)) if match else 0

def save_compliance_report(report: dict, business_ref: Optional[str] = None) -> bool:
    """
    Save a compliance report to the cache directory with versioning.
    Returns True if the report was saved successfully, False otherwise.
    """
    try:
        # Validate report format
        if not isinstance(report, dict) or "final_evaluation" not in report:
            logging.error("Invalid report format")
            return False

        # Get business reference from report if not provided
        if not business_ref:
            business_ref = report.get("claim", {}).get("business_ref")
            if not business_ref:
                logging.error("No business reference found in report")
                return False

        # Create cache directory
        cache_dir = CACHE_FOLDER / business_ref
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Get current date and find existing versions
        current_date = datetime.now().strftime(DATE_FORMAT)
        pattern = f"FirmComplianceReport_{business_ref}_v*_{current_date}.json"
        existing_files = sorted(cache_dir.glob(pattern))

        # Determine next version number
        if not existing_files:
            version = 1
        else:
            latest_file = existing_files[-1]
            latest_version = get_version_number(latest_file.stem)
            if latest_version is None:
                version = 1
            else:
                # Check if there are significant changes
                try:
                    with open(latest_file, 'r') as f:
                        content = f.read()
                        if not content:
                            version = latest_version + 1
                        else:
                            latest_report = json.loads(content)
                            if has_significant_changes(report, latest_report):
                                version = latest_version + 1
                            else:
                                logging.info("No significant changes detected, skipping save")
                                return True
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Error reading latest version: {e}")
                    version = latest_version + 1

        # Save new version
        filename = f"FirmComplianceReport_{business_ref}_v{version}_{current_date}.json"
        filepath = cache_dir / filename
        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            logging.info(f"Saved compliance report: {filepath}")
            return True
        except IOError as e:
            logging.error(f"Error saving compliance report: {e}")
            return False

    except Exception as e:
        logging.error(f"Error saving compliance report: {e}")
        return False