"""
==============================================
📌 SUMMARY GENERATOR MODULE OVERVIEW
==============================================
🗂 PURPOSE
This module provides the `SummaryGenerator` class to generate compliance summaries,
taxonomy trees, risk dashboards, and data quality reports from FirmComplianceReport JSON files.
It processes cached firm compliance data to produce actionable insights for regulatory analysis.

🔧 USAGE
Instantiate with a FileHandler and optional FirmComplianceHandler to access cached JSON files,
then call methods like `generate_compliance_summary`, `generate_taxonomy_from_latest_reports`,
`generate_risk_dashboard`, or `generate_data_quality_report` to analyze firm data.

📝 NOTES
- Relies on `file_handler.py` for filesystem operations and `firm_compliance_handler.py` for report filtering.
- Outputs are either JSON strings (for summaries) or human-readable text (for taxonomy, dashboard, and quality reports).
- Designed to work with `FirmComplianceReport_*.json` files in the cache structure.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Set, Union, TypedDict, cast
from collections import defaultdict
import json
import logging
from datetime import datetime

from .file_handler import FileHandler
from .firm_compliance_handler import FirmComplianceHandler

# Configure logging
logger = logging.getLogger(__name__)

class ReportSummary(TypedDict):
    """Type definition for report summary data."""
    business_ref: str
    reference_id: str
    file_name: str
    overall_compliance: bool
    alert_count: int

class SubsectionSummary(TypedDict):
    """Type definition for subsection summary data."""
    business_ref: str
    reference_id: str
    file_name: str
    subsection: str
    compliance: bool
    alert_count: int
    explanation: str

class TaxonomyNode(TypedDict):
    """Type definition for taxonomy tree nodes."""
    _types: Set[str]
    children: Union[Dict[str, Any], List[Any]]

class SummaryGenerator:
    """
    Generates summaries, taxonomy trees, risk dashboards, and data quality reports from firm compliance data.

    Attributes:
        file_handler (FileHandler): Handles filesystem operations for reading JSON files.
        compliance_handler (Optional[FirmComplianceHandler]): Filters and retrieves latest firm compliance reports.
    """

    def __init__(self, file_handler: FileHandler, compliance_handler: Optional[FirmComplianceHandler] = None):
        """
        Initialize the SummaryGenerator with necessary handlers.

        Args:
            file_handler (FileHandler): Instance for filesystem operations.
            compliance_handler (Optional[FirmComplianceHandler]): Instance for compliance report operations.
        """
        self.file_handler = file_handler
        self.compliance_handler = compliance_handler

    def _extract_compliance_data(self, reports: List[Dict[str, Any]], business_ref: str) -> Tuple[List[ReportSummary], List[SubsectionSummary]]:
        """
        Extract compliance data from a list of firm reports for summary generation.

        Args:
            reports (List[Dict[str, Any]]): List of JSON report dictionaries.
            business_ref (str): Firm identifier to associate with the data.

        Returns:
            Tuple[List[ReportSummary], List[SubsectionSummary]]: (report_summary, subsection_summary)
        """
        report_data: List[ReportSummary] = []
        subsection_data: List[SubsectionSummary] = []
        
        for report in reports:
            try:
                biz_ref = report.get('claim', {}).get('business_ref', business_ref)
                ref_id = report.get('reference_id', 'UNKNOWN')
                file_name = report.get('file_name', f"FirmComplianceReport_{ref_id}_v1_20250315.json")
                overall_compliance = report.get('final_evaluation', {}).get('overall_compliance', False)
                alert_count = len(report.get('final_evaluation', {}).get('alerts', []))
                
                report_entry: ReportSummary = {
                    'business_ref': biz_ref,
                    'reference_id': ref_id,
                    'file_name': file_name,
                    'overall_compliance': overall_compliance,
                    'alert_count': alert_count
                }
                report_data.append(report_entry)
                
                if not overall_compliance or alert_count > 0:
                    subsections = [
                        ('search_evaluation', report.get('search_evaluation', {})),
                        ('registration_status', report.get('registration_status', {})),
                        ('regulatory_oversight', report.get('regulatory_oversight', {})),
                        ('disclosures', report.get('disclosures', {})),
                        ('financials', report.get('financials', {})),
                        ('legal', report.get('legal', {})),
                        ('qualifications', report.get('qualifications', {})),
                        ('data_integrity', report.get('data_integrity', {}))
                    ]
                    
                    for section_name, section_data in subsections:
                        subsection_entry: SubsectionSummary = {
                            'business_ref': biz_ref,
                            'reference_id': ref_id,
                            'file_name': file_name,
                            'subsection': section_name,
                            'compliance': section_data.get('compliance', True),
                            'alert_count': len(section_data.get('alerts', [])),
                            'explanation': section_data.get('compliance_explanation', 'N/A')
                        }
                        subsection_data.append(subsection_entry)
            except Exception as e:
                logger.error(f"Error processing report: {str(e)}")
                continue
                
        return report_data, subsection_data

    def generate_compliance_summary(self, firm_path: Path, business_ref: str, page: int = 1, page_size: int = 10) -> str:
        """
        Generate a compliance summary for a specific firm with pagination.

        Args:
            firm_path (Path): Path to the firm's cache folder.
            business_ref (str): Firm identifier (e.g., "BIZ_001").
            page (int): Page number for pagination (default: 1).
            page_size (int): Number of items per page (default: 10).

        Returns:
            str: JSON-formatted summary of firm compliance data.
        """
        try:
            reports = []
            if self.compliance_handler:
                # Use FirmComplianceHandler to get reports
                reports_json = self.compliance_handler.list_compliance_reports(
                    business_ref=business_ref,
                    page=page,
                    page_size=page_size
                )
                reports_data = json.loads(reports_json)
                
                if reports_data.get("status") != "success":
                    return json.dumps({
                        "status": "error",
                        "message": reports_data.get("message", "Failed to retrieve compliance reports"),
                        "business_ref": business_ref,
                        "report_summary": [],
                        "subsection_summary": [],
                        "pagination": reports_data.get("pagination", {
                            "total_items": 0,
                            "total_pages": 1,
                            "current_page": page,
                            "page_size": page_size
                        })
                    }, indent=2)
                
                for report_info in reports_data.get("reports", {}).get(business_ref, []):
                    try:
                        file_path = firm_path / report_info["file_name"]
                        if report_data := self.file_handler.read_json(file_path):
                            report_data['file_name'] = report_info["file_name"]
                            reports.append(report_data)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue
            else:
                # Fallback to direct file reading
                for file_path in self.file_handler.list_files(firm_path, "FirmComplianceReport_*.json"):
                    try:
                        if report_data := self.file_handler.read_json(file_path):
                            report_data['file_name'] = file_path.name
                            reports.append(report_data)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue
            
            if not reports:
                return json.dumps({
                    "status": "error",
                    "message": f"No valid compliance reports found for {business_ref}",
                    "business_ref": business_ref,
                    "report_summary": [],
                    "subsection_summary": [],
                    "pagination": {
                        "total_items": 0,
                        "total_pages": 1,
                        "current_page": page,
                        "page_size": page_size
                    }
                }, indent=2)
            
            report_summary, subsection_summary = self._extract_compliance_data(reports, business_ref)
            
            total_items = len(report_summary)
            total_pages = max(1, (total_items + page_size - 1) // page_size)
            current_page = max(1, min(page, total_pages))
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            
            result = {
                "business_ref": business_ref,
                "status": "success",
                "message": f"Generated compliance summary for {business_ref}",
                "report_summary": report_summary[start_idx:end_idx],
                "subsection_summary": [
                    entry for entry in subsection_summary 
                    if any(report["reference_id"] == entry["reference_id"] 
                          for report in report_summary[start_idx:end_idx])
                ],
                "pagination": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "current_page": current_page,
                    "page_size": page_size
                }
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating compliance summary: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to generate compliance summary: {str(e)}",
                "business_ref": business_ref,
                "report_summary": [],
                "subsection_summary": [],
                "pagination": {
                    "total_items": 0,
                    "total_pages": 1,
                    "current_page": page,
                    "page_size": page_size
                }
            }, indent=2)

    def generate_all_compliance_summaries(self, cache_folder: Path, page: int = 1, page_size: int = 10) -> str:
        """
        Generate a compliance summary for all firms with pagination.

        Args:
            cache_folder (Path): Root cache folder containing firm subdirectories.
            page (int): Page number for pagination (default: 1).
            page_size (int): Number of items per page (default: 10).

        Returns:
            str: JSON-formatted summary of compliance data across all firms.
        """
        try:
            if not cache_folder.exists():
                return json.dumps({
                    "status": "error",
                    "message": f"Cache folder not found at {cache_folder}",
                    "report_summary": [],
                    "subsection_summary": [],
                    "pagination": {
                        "total_items": 0,
                        "total_pages": 1,
                        "current_page": 1,
                        "page_size": page_size
                    }
                }, indent=2)
            
            if self.compliance_handler:
                # Use FirmComplianceHandler to get reports
                reports_json = self.compliance_handler.list_compliance_reports(
                    page=page,
                    page_size=page_size
                )
                reports_data = json.loads(reports_json)
                
                if reports_data.get("status") != "success":
                    return json.dumps({
                        "status": "error",
                        "message": "Failed to retrieve compliance reports",
                        "report_summary": [],
                        "subsection_summary": [],
                        "pagination": reports_data.get("pagination", {
                            "total_items": 0,
                            "total_pages": 1,
                            "current_page": 1,
                            "page_size": page_size
                        })
                    }, indent=2)
                
                all_reports: List[ReportSummary] = []
                all_subsections: List[SubsectionSummary] = []
                
                for business_ref, reports_list in reports_data.get("reports", {}).items():
                    reports: List[Dict[str, Any]] = []
                    for report_info in reports_list:
                        try:
                            file_path = cache_folder / business_ref / report_info["file_name"]
                            if report_data := self.file_handler.read_json(file_path):
                                report_data['file_name'] = report_info["file_name"]
                                reports.append(report_data)
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {str(e)}")
                            continue
                    
                    if reports:
                        report_data, subsection_data = self._extract_compliance_data(reports, business_ref)
                        all_reports.extend(report_data)
                        all_subsections.extend(subsection_data)
                
                return json.dumps({
                    "status": "success",
                    "message": f"Generated compliance summary for {len(reports_data.get('reports', {}))} firms",
                    "report_summary": all_reports,
                    "subsection_summary": all_subsections,
                    "pagination": reports_data.get("pagination", {
                        "total_items": len(all_reports),
                        "total_pages": 1,
                        "current_page": 1,
                        "page_size": page_size
                    })
                }, indent=2)
            
            else:
                # Fallback to direct file reading
                all_reports: List[ReportSummary] = []
                all_subsections: List[SubsectionSummary] = []
                
                try:
                    firm_dirs = [d for d in self.file_handler.list_files(cache_folder, "*") if d.is_dir()]
                except Exception as e:
                    logger.error(f"Error listing directories: {str(e)}")
                    firm_dirs = []
                
                total_items = len(firm_dirs)
                total_pages = max(1, (total_items + page_size - 1) // page_size)
                current_page = max(1, min(page, total_pages))
                start_idx = (current_page - 1) * page_size
                end_idx = start_idx + page_size
                
                for firm_path in firm_dirs[start_idx:end_idx]:
                    try:
                        biz_ref = firm_path.name
                        reports: List[Dict[str, Any]] = []
                        
                        for file_path in self.file_handler.list_files(firm_path, "FirmComplianceReport_*.json"):
                            try:
                                if report_data := self.file_handler.read_json(file_path):
                                    report_data['file_name'] = file_path.name
                                    reports.append(report_data)
                            except Exception as e:
                                logger.error(f"Error reading file {file_path}: {str(e)}")
                                continue
                        
                        if reports:
                            report_data, subsection_data = self._extract_compliance_data(reports, biz_ref)
                            all_reports.extend(report_data)
                            all_subsections.extend(subsection_data)
                            
                    except Exception as e:
                        logger.error(f"Error processing firm {firm_path}: {str(e)}")
                        continue
                
                return json.dumps({
                    "status": "success",
                    "message": f"Generated compliance summary for {len(firm_dirs)} firms",
                    "report_summary": all_reports,
                    "subsection_summary": all_subsections,
                    "pagination": {
                        "total_items": total_items,
                        "total_pages": total_pages,
                        "current_page": current_page,
                        "page_size": page_size
                    }
                }, indent=2)
            
        except Exception as e:
            logger.error(f"Error generating all compliance summaries: {str(e)}")
            return json.dumps({
                "status": "error",
                "message": f"Failed to generate compliance summaries: {str(e)}",
                "report_summary": [],
                "subsection_summary": [],
                "pagination": {
                    "total_items": 0,
                    "total_pages": 1,
                    "current_page": 1,
                    "page_size": page_size
                }
            }, indent=2)

    def _build_tree(self, data: Any) -> TaxonomyNode:
        """
        Recursively build a hierarchical tree from a JSON object for taxonomy generation.

        Args:
            data (Any): JSON data to process (dict, list, or primitive).

        Returns:
            TaxonomyNode: Nested dictionary with "_types" (set of data types) and "children".
        """
        node: TaxonomyNode = {"_types": set(), "children": {}}
        
        if isinstance(data, dict):
            node["_types"].add("dict")
            node["children"] = {
                key: cast(Dict[str, Any], self._build_tree(value))
                for key, value in data.items()
            }
        elif isinstance(data, list):
            node["_types"].add("list")
            node["children"] = [
                cast(Dict[str, Any], self._build_tree(item))
                for item in data
            ]
        else:
            node["_types"].add(type(data).__name__)
            node["children"] = {}
            
        return node

    def _merge_trees(self, base_tree: TaxonomyNode, new_tree: TaxonomyNode) -> None:
        """
        Merge a new taxonomy tree into an existing base tree in-place.

        Args:
            base_tree (TaxonomyNode): The existing tree to merge into.
            new_tree (TaxonomyNode): The new tree to merge from.
        """
        base_tree["_types"].update(new_tree["_types"])
        
        if isinstance(base_tree["children"], dict) and isinstance(new_tree["children"], dict):
            for key, value in new_tree["children"].items():
                if key not in base_tree["children"]:
                    base_tree["children"][key] = value
                else:
                    self._merge_trees(
                        cast(TaxonomyNode, base_tree["children"][key]),
                        cast(TaxonomyNode, value)
                    )
        elif isinstance(base_tree["children"], list) and isinstance(new_tree["children"], list):
            while len(base_tree["children"]) < len(new_tree["children"]):
                base_tree["children"].append({"_types": set(), "children": {}})
            for i in range(len(new_tree["children"])):
                self._merge_trees(
                    cast(TaxonomyNode, base_tree["children"][i]),
                    cast(TaxonomyNode, new_tree["children"][i])
                )

    def _print_tree(self, tree: TaxonomyNode, indent: int = 0, field_name: str = "<root>") -> str:
        """
        Recursively pretty-print the taxonomy tree with indentation.

        Args:
            tree (TaxonomyNode): The taxonomy tree to print.
            indent (int): Current indentation level (default: 0).
            field_name (str): Name of the current field (default: "<root>").

        Returns:
            str: Formatted string representation of the tree.
        """
        lines = []
        prefix = "  " * indent
        type_str = f"{{'{', '.join(sorted(tree['_types']))}'}}"
        lines.append(f"{prefix}- {field_name} (types={type_str})")
        
        if isinstance(tree["children"], dict):
            for key, value in sorted(tree["children"].items()):
                lines.append(self._print_tree(
                    cast(TaxonomyNode, value),
                    indent + 1,
                    field_name=key
                ))
        elif isinstance(tree["children"], list):
            for i, child in enumerate(tree["children"]):
                lines.append(self._print_tree(
                    cast(TaxonomyNode, child),
                    indent + 1,
                    field_name=f"[{i}]"
                ))
            
        return "\n".join(lines)

    def _check_field_value(self, data: Dict[str, Any], field_path: str) -> Tuple[bool, str]:
        """
        Check if a field exists and has a non-null, non-empty value.

        Args:
            data (Dict[str, Any]): The JSON data to check.
            field_path (str): Dot-separated path to the field (e.g., "claim.business_name").

        Returns:
            Tuple[bool, str]: (has_value, status_message)
                - has_value: True if the field has a non-null, non-empty value.
                - status_message: "Has Value", "Missing", "Null", or "Empty" indicating the field's state.
        """
        keys = field_path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False, "Missing"
        if current is None:
            return False, "Null"
        if isinstance(current, str) and not current.strip():
            return False, "Empty"
        return True, "Has Value"

    def generate_taxonomy_from_latest_reports(self) -> str:
        """
        Generate a taxonomy tree from the latest FirmComplianceReport JSON files.

        Returns:
            str: Human-readable representation of the taxonomy tree.
        """
        try:
            if self.compliance_handler:
                reports_json = self.compliance_handler.list_compliance_reports(
                    page=1,
                    page_size=99999
                )
                reports_data = json.loads(reports_json)
                
                if reports_data.get("status") != "success":
                    return f"Error generating taxonomy: {reports_data.get('message', 'Unknown error')}"
                
                reports = []
                for business_ref, report_list in reports_data.get("reports", {}).items():
                    for report_info in report_list:
                        try:
                            file_path = Path(f"{business_ref}/{report_info['file_name']}")
                            if report_data := self.file_handler.read_json(file_path):
                                reports.append(report_data)
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {str(e)}")
                            continue
            else:
                reports = []
                for file_path in self.file_handler.list_files(".", "FirmComplianceReport_*.json"):
                    try:
                        if report_data := self.file_handler.read_json(file_path):
                            reports.append(report_data)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue

            if not reports:
                return "No valid reports found for taxonomy generation"

            # Initialize combined_tree as a proper TaxonomyNode
            combined_tree: TaxonomyNode = {"_types": set(), "children": {}}
            
            for report in reports:
                try:
                    report_tree = self._build_tree(report)
                    self._merge_trees(combined_tree, report_tree)
                except Exception as e:
                    logger.error(f"Error merging taxonomy tree: {str(e)}")
                    continue

            return f"Generated taxonomy tree from {len(reports)} reports:\n{json.dumps(combined_tree, indent=2)}"

        except Exception as e:
            logger.error(f"Error generating taxonomy: {str(e)}")
            return f"Error generating taxonomy: {str(e)}"

    def generate_risk_dashboard(self) -> str:
        """
        Generate a compliance risk dashboard from the latest reports.

        Returns:
            str: Human-readable risk dashboard.
        """
        try:
            if self.compliance_handler:
                reports_json = self.compliance_handler.list_compliance_reports(
                    page=1,
                    page_size=99999
                )
                reports_data = json.loads(reports_json)
                
                if reports_data.get("status") != "success":
                    return f"Error generating risk dashboard: {reports_data.get('message', 'Unknown error')}"
                
                reports = []
                for business_ref, report_list in reports_data.get("reports", {}).items():
                    for report_info in report_list:
                        try:
                            file_path = Path(f"{business_ref}/{report_info['file_name']}")
                            if report_data := self.file_handler.read_json(file_path):
                                reports.append(report_data)
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {str(e)}")
                            continue
            else:
                reports = []
                for file_path in self.file_handler.list_files(".", "FirmComplianceReport_*.json"):
                    try:
                        if report_data := self.file_handler.read_json(file_path):
                            reports.append(report_data)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue

            if not reports:
                return "No valid reports found for risk dashboard generation"

            risk_categories = {
                "Low": [],
                "Medium": [],
                "High": [],
                "Unknown": []
            }

            for report in reports:
                try:
                    alerts = report.get("final_evaluation", {}).get("alerts", [])
                    severity = max((alert.get("severity", "Unknown") for alert in alerts), default="Unknown")
                    risk_categories[severity].append(report.get("claim", {}).get("business_ref", "Unknown"))
                except Exception as e:
                    logger.error(f"Error processing report for risk dashboard: {str(e)}")
                    continue

            dashboard = ["Firm Compliance Risk Dashboard", "-" * 30]
            for risk_level, firms in risk_categories.items():
                dashboard.append(f"\n{risk_level} Risk Firms ({len(firms)}):")
                for firm in firms:
                    dashboard.append(f"- {firm}")

            return "\n".join(dashboard)

        except Exception as e:
            logger.error(f"Error generating risk dashboard: {str(e)}")
            return f"Error generating risk dashboard: {str(e)}"

    def generate_data_quality_report(self) -> str:
        """
        Generate a data quality report checking for non-null, non-empty values.

        Returns:
            str: Human-readable data quality report.
        """
        try:
            if self.compliance_handler:
                reports_json = self.compliance_handler.list_compliance_reports(
                    page=1,
                    page_size=99999
                )
                reports_data = json.loads(reports_json)
                
                if reports_data.get("status") != "success":
                    return f"Error generating data quality report: {reports_data.get('message', 'Unknown error')}"
                
                reports = []
                for business_ref, report_list in reports_data.get("reports", {}).items():
                    for report_info in report_list:
                        try:
                            file_path = Path(f"{business_ref}/{report_info['file_name']}")
                            if report_data := self.file_handler.read_json(file_path):
                                reports.append(report_data)
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {str(e)}")
                            continue
            else:
                reports = []
                for file_path in self.file_handler.list_files(".", "FirmComplianceReport_*.json"):
                    try:
                        if report_data := self.file_handler.read_json(file_path):
                            reports.append(report_data)
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
                        continue

            if not reports:
                return "No valid reports found for data quality analysis"

            total_reports = len(reports)
            field_stats = {
                "claim.business_name": {"present": 0, "missing": 0, "examples": []},
                "claim.business_ref": {"present": 0, "missing": 0, "examples": []},
                "final_evaluation.alerts": {"present": 0, "missing": 0, "examples": []}
            }

            for report in reports:
                try:
                    for field_path, stats in field_stats.items():
                        parts = field_path.split(".")
                        value = report
                        for part in parts:
                            value = value.get(part, {})
                        
                        if value and value != {}:
                            stats["present"] += 1
                            if len(stats["examples"]) < 3:
                                stats["examples"].append(str(value))
                        else:
                            stats["missing"] += 1
                except Exception as e:
                    logger.error(f"Error processing report for data quality: {str(e)}")
                    continue

            report_lines = ["Firm Data Quality Report", "-" * 25]
            for field_path, stats in field_stats.items():
                present_pct = (stats["present"] / total_reports) * 100
                report_lines.extend([
                    f"\n{field_path}:",
                    f"Present: {stats['present']} ({present_pct:.1f}%)",
                    f"Missing: {stats['missing']}",
                    "Examples:" if stats["examples"] else "No examples available"
                ])
                for example in stats["examples"]:
                    report_lines.append(f"- {example}")

            return "\n".join(report_lines)

        except Exception as e:
            logger.error(f"Error generating data quality report: {str(e)}")
            return f"Error generating data quality report: {str(e)}"