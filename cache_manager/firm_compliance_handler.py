"""
==============================================
📌 FIRM COMPLIANCE HANDLER MODULE OVERVIEW
==============================================
🗂 PURPOSE
This module provides the `FirmComplianceHandler` class to manage compliance report operations
for business entities. It handles retrieval and listing of compliance reports, using business_ref
as the primary identifier and reference_id for versioning.

🔧 USAGE
Instantiate with a cache folder to access cached compliance reports, then use methods like
`get_latest_compliance_report`, `get_compliance_report_by_ref`, or `list_compliance_reports`
to retrieve and list reports with versioning support.

📝 NOTES
- Works with business_ref-based cache directory structure.
- Supports versioned compliance reports with reference_id tracking.
- Returns JSON-formatted strings for downstream processing.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import logging
from datetime import datetime
import re

from .file_handler import FileHandler
from .config import DEFAULT_CACHE_FOLDER

# Configure logging
logger = logging.getLogger("FirmComplianceHandler")

class FirmComplianceHandler:
    """
    Manages compliance report operations for business entities.

    Attributes:
        cache_folder (Path): Base path to the cache directory.
        file_handler (FileHandler): Instance for filesystem operations.
    """

    def __init__(self, cache_folder: Path = DEFAULT_CACHE_FOLDER):
        """
        Initialize the FirmComplianceHandler with a cache folder.

        Args:
            cache_folder (Path): Directory for cached data (default from config).
        """
        self.cache_folder = cache_folder
        self.file_handler = FileHandler(cache_folder)
        
        if not cache_folder.exists():
            logger.warning(f"Cache folder does not exist: {cache_folder}")

    def _parse_report_filename(self, filename: str) -> Dict[str, Any]:
        """
        Parse a compliance report filename to extract metadata.

        Args:
            filename (str): Report filename (e.g., "FirmComplianceReport_B123_v1_20250315.json")

        Returns:
            Dict containing reference_id, version, and date information.
        """
        pattern = r"FirmComplianceReport_([^_]+)_v(\d+)_(\d{8})\.json"
        match = re.match(pattern, filename)
        
        if match:
            reference_id, version, date_str = match.groups()
            return {
                "reference_id": reference_id,
                "version": int(version),
                "date": datetime.strptime(date_str, "%Y%m%d"),
                "filename": filename
            }
        return {}

    def get_latest_compliance_report(self, business_ref: str) -> str:
        """
        Retrieve the latest compliance report for a business.

        Args:
            business_ref (str): Business identifier (e.g., "BIZ_001").

        Returns:
            JSON string containing the latest report or error status.
        """
        try:
            business_dir = self.cache_folder / business_ref
            if not business_dir.exists():
                return json.dumps({
                    "status": "warning",
                    "message": f"Business directory not found: {business_ref}",
                    "business_ref": business_ref,
                    "report": None
                }, indent=2)

            report_files = sorted(
                self.file_handler.list_files(business_dir, "FirmComplianceReport_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            if not report_files:
                return json.dumps({
                    "status": "warning",
                    "message": f"No compliance reports found for business: {business_ref}",
                    "business_ref": business_ref,
                    "report": None
                }, indent=2)

            latest_file = report_files[0]
            if report_data := self.file_handler.read_json(latest_file):
                return json.dumps({
                    "status": "success",
                    "message": f"Retrieved latest compliance report: {latest_file.name}",
                    "business_ref": business_ref,
                    "report": report_data
                }, indent=2)

            return json.dumps({
                "status": "error",
                "message": f"Failed to read latest report: {latest_file.name}",
                "business_ref": business_ref,
                "report": None
            }, indent=2)

        except Exception as e:
            logger.error(f"Error getting latest report for {business_ref}: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Error retrieving latest report: {str(e)}",
                "business_ref": business_ref,
                "report": None
            }, indent=2)

    def get_compliance_report_by_ref(self, business_ref: str, reference_id: str) -> str:
        """
        Retrieve the latest compliance report by reference_id for a business.

        Args:
            business_ref (str): Business identifier (e.g., "BIZ_001").
            reference_id (str): Report identifier (e.g., "B123").

        Returns:
            JSON string containing the requested report or error status.
        """
        try:
            business_dir = self.cache_folder / business_ref
            if not business_dir.exists():
                return json.dumps({
                    "status": "warning",
                    "message": f"Business directory not found: {business_ref}",
                    "business_ref": business_ref,
                    "reference_id": reference_id,
                    "report": None
                }, indent=2)

            # List all files matching the reference_id pattern
            pattern = f"FirmComplianceReport_{reference_id}_v*.json"
            report_files = self.file_handler.list_files(business_dir, pattern)
            
            if not report_files:
                return json.dumps({
                    "status": "warning",
                    "message": f"No reports found for reference_id: {reference_id}",
                    "business_ref": business_ref,
                    "reference_id": reference_id,
                    "report": None
                }, indent=2)

            # Get the latest version
            latest_file = max(
                report_files,
                key=lambda p: self._parse_report_filename(p.name).get("version", 0)
            )

            if report_data := self.file_handler.read_json(latest_file):
                return json.dumps({
                    "status": "success",
                    "message": f"Retrieved compliance report: {latest_file.name}",
                    "business_ref": business_ref,
                    "reference_id": reference_id,
                    "report": report_data
                }, indent=2)

            return json.dumps({
                "status": "error",
                "message": f"Failed to read report: {latest_file.name}",
                "business_ref": business_ref,
                "reference_id": reference_id,
                "report": None
            }, indent=2)

        except Exception as e:
            logger.error(f"Error getting report for {business_ref}/{reference_id}: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Error retrieving report: {str(e)}",
                "business_ref": business_ref,
                "reference_id": reference_id,
                "report": None
            }, indent=2)

    def list_compliance_reports(
        self,
        business_ref: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> str:
        """
        List compliance reports with pagination, optionally filtered by business_ref.

        Args:
            business_ref (Optional[str]): Business identifier (None for all businesses).
            page (int): Page number for pagination (default: 1).
            page_size (int): Number of items per page (default: 10).

        Returns:
            JSON string containing paginated report listings.
        """
        try:
            if business_ref:
                # List reports for a specific business
                business_dir = self.cache_folder / business_ref
                if not business_dir.exists():
                    return json.dumps({
                        "status": "warning",
                        "message": f"Business directory not found: {business_ref}",
                        "business_ref": business_ref,
                        "reports": [],
                        "pagination": {
                            "total_items": 0,
                            "total_pages": 1,
                            "current_page": 1,
                            "page_size": page_size
                        }
                    }, indent=2)

                # Get all reports and group by reference_id
                reports_by_ref: Dict[str, List[Dict[str, Any]]] = {}
                for file_path in self.file_handler.list_files(business_dir, "FirmComplianceReport_*.json"):
                    metadata = self._parse_report_filename(file_path.name)
                    if metadata:
                        ref_id = metadata["reference_id"]
                        if ref_id not in reports_by_ref:
                            reports_by_ref[ref_id] = []
                        reports_by_ref[ref_id].append({
                            **metadata,
                            "last_modified": datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat()
                        })

                # Get latest version for each reference_id
                latest_reports = []
                for ref_id, versions in reports_by_ref.items():
                    latest = max(versions, key=lambda x: x["version"])
                    latest_reports.append({
                        "reference_id": ref_id,
                        "file_name": latest["filename"],
                        "last_modified": latest["last_modified"]
                    })

                # Apply pagination
                total_items = len(latest_reports)
                total_pages = max(1, (total_items + page_size - 1) // page_size)
                current_page = max(1, min(page, total_pages))
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size

                return json.dumps({
                    "status": "success",
                    "message": f"Listed {len(latest_reports)} compliance reports for {business_ref}",
                    "business_ref": business_ref,
                    "reports": latest_reports[start_idx:end_idx],
                    "pagination": {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": current_page,
                        "page_size": page_size
                    }
                }, indent=2)

            else:
                # List reports across all businesses
                try:
                    business_dirs = [
                        d for d in self.file_handler.list_files(self.cache_folder, "*")
                        if d.is_dir()
                    ]
                except Exception as e:
                    logger.error(f"Error listing business directories: {str(e)}")
                    business_dirs = []

                # Calculate pagination for businesses
                total_items = len(business_dirs)
                total_pages = max(1, (total_items + page_size - 1) // page_size)
                current_page = max(1, min(page, total_pages))
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size

                # Process paginated subset of businesses
                reports_by_business = {}
                for business_dir in business_dirs[start_idx:end_idx]:
                    business_ref = business_dir.name
                    reports_by_ref: Dict[str, List[Dict[str, Any]]] = {}

                    for file_path in self.file_handler.list_files(business_dir, "FirmComplianceReport_*.json"):
                        metadata = self._parse_report_filename(file_path.name)
                        if metadata:
                            ref_id = metadata["reference_id"]
                            if ref_id not in reports_by_ref:
                                reports_by_ref[ref_id] = []
                            reports_by_ref[ref_id].append({
                                **metadata,
                                "last_modified": datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ).isoformat()
                            })

                    # Get latest version for each reference_id
                    latest_reports = []
                    for ref_id, versions in reports_by_ref.items():
                        latest = max(versions, key=lambda x: x["version"])
                        latest_reports.append({
                            "reference_id": ref_id,
                            "file_name": latest["filename"],
                            "last_modified": latest["last_modified"]
                        })

                    if latest_reports:
                        reports_by_business[business_ref] = latest_reports

                return json.dumps({
                    "status": "success",
                    "message": f"Listed compliance reports for {len(reports_by_business)} businesses",
                    "reports": reports_by_business,
                    "pagination": {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": current_page,
                        "page_size": page_size
                    }
                }, indent=2)

        except Exception as e:
            logger.error(f"Error listing compliance reports: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Error listing compliance reports: {str(e)}",
                "reports": [],
                "pagination": {
                    "total_items": 0,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": page_size
                }
            }, indent=2) 