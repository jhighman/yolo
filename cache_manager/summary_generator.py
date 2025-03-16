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
        Build a taxonomy tree from any data structure.
        
        Args:
            data: Any Python data structure
            
        Returns:
            TaxonomyNode: Tree representation of the data structure
        """
        types = set()
        children: Union[Dict[str, TaxonomyNode], List[Any]] = {}
        
        if isinstance(data, dict):
            types.add("dict")
            children = {
                key: self._build_tree(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            types.add("list")
            children = [self._build_tree(item) for item in data]
        elif isinstance(data, bool):  # Check for bool before int/float since bool is a subclass of int
            types.add("bool")
        elif isinstance(data, (int, float)):
            types.add("number")
        elif isinstance(data, str):
            types.add("str")
        elif data is None:
            types.add("null")
        else:
            types.add(type(data).__name__)
        
        return {
            "_types": types,
            "children": children
        }

    def _merge_trees(self, tree1: TaxonomyNode, tree2: TaxonomyNode) -> None:
        """
        Merge two taxonomy trees in-place.
        
        Args:
            tree1: First tree (modified in-place)
            tree2: Second tree to merge into the first
        """
        tree1["_types"].update(tree2["_types"])
        
        if isinstance(tree1["children"], dict) and isinstance(tree2["children"], dict):
            for key, subtree2 in tree2["children"].items():
                if key in tree1["children"]:
                    self._merge_trees(cast(TaxonomyNode, tree1["children"][key]), subtree2)
                else:
                    cast(Dict[str, TaxonomyNode], tree1["children"])[key] = subtree2

    def generate_taxonomy_from_latest_reports(self) -> str:
        """
        Generate a taxonomy tree from the latest FirmComplianceReport JSON files.
        
        Returns:
            str: Human-readable representation of the taxonomy tree
        """
        try:
            if not self.compliance_handler:
                return "Error: No compliance handler available"
            
            reports_json = self.compliance_handler.list_compliance_reports(page=1, page_size=99999)
            reports_data = json.loads(reports_json)
            
            if reports_data.get("status") != "success":
                return f"Error: {reports_data.get('message', 'Failed to retrieve reports')}"
            
            combined_tree: Optional[TaxonomyNode] = None
            
            for business_ref, reports_list in reports_data.get("reports", {}).items():
                for report_info in reports_list:
                    try:
                        file_path = Path(report_info["file_name"])
                        if report_data := self.file_handler.read_json(file_path):
                            tree = self._build_tree(report_data)
                            if combined_tree is None:
                                combined_tree = tree
                            else:
                                self._merge_trees(combined_tree, tree)
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        continue
            
            if combined_tree is None:
                return "No valid reports found to generate taxonomy"
            
            return self._format_taxonomy_tree(combined_tree)
            
        except Exception as e:
            logger.error(f"Error generating taxonomy: {str(e)}")
            return f"Error generating taxonomy: {str(e)}"

    def _format_taxonomy_tree(self, tree: TaxonomyNode, indent: int = 0) -> str:
        """
        Format a taxonomy tree for human-readable output.
        
        Args:
            tree: TaxonomyNode to format
            indent: Current indentation level
            
        Returns:
            str: Human-readable tree representation
        """
        result = []
        prefix = "  " * indent
        
        types_str = ", ".join(sorted(tree["_types"]))
        result.append(f"{prefix}Types: {types_str}")
        
        if isinstance(tree["children"], dict):
            for key, subtree in sorted(tree["children"].items()):
                result.append(f"{prefix}{key}:")
                result.append(self._format_taxonomy_tree(subtree, indent + 1))
        elif isinstance(tree["children"], list) and tree["children"]:
            result.append(f"{prefix}Items:")
            for subtree in tree["children"]:
                result.append(self._format_taxonomy_tree(subtree, indent + 1))
        
        return "\n".join(result)

    def generate_risk_dashboard(self) -> str:
        """
        Generate a compliance risk dashboard from the latest reports.
        
        Returns:
            str: Human-readable risk dashboard
        """
        try:
            if not self.compliance_handler:
                return "Error: No compliance handler available"
            
            reports_json = self.compliance_handler.list_compliance_reports(page=1, page_size=99999)
            reports_data = json.loads(reports_json)
            
            if reports_data.get("status") != "success":
                return f"Error: {reports_data.get('message', 'Failed to retrieve reports')}"
            
            risk_levels = {"Low": 0, "Medium": 0, "High": 0, "Unknown": 0}
            total_alerts = 0
            top_alerts: Dict[str, int] = defaultdict(int)
            
            for business_ref, reports_list in reports_data.get("reports", {}).items():
                for report_info in reports_list:
                    try:
                        file_path = Path(report_info["file_name"])
                        if report_data := self.file_handler.read_json(file_path):
                            final_eval = report_data.get("final_evaluation", {})
                            risk_level = final_eval.get("overall_risk_level", "Unknown")
                            risk_levels[risk_level] += 1
                            
                            alerts = final_eval.get("alerts", [])
                            total_alerts += len(alerts)
                            
                            for alert in alerts:
                                alert_type = alert.get("alert_type", "Unknown")
                                top_alerts[alert_type] += 1
                                
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        continue
            
            # Format dashboard
            lines = [
                "Firm Compliance Risk Dashboard",
                "===========================",
                "",
                "Risk Level Distribution:",
                f"- High Risk Firms:   {risk_levels['High']}",
                f"- Medium Risk Firms: {risk_levels['Medium']}",
                f"- Low Risk Firms:    {risk_levels['Low']}",
                f"- Unknown Risk:      {risk_levels['Unknown']}",
                "",
                f"Total Alerts: {total_alerts}",
                "",
                "Top Alert Types:",
            ]
            
            # Add top 10 alert types
            for alert_type, count in sorted(top_alerts.items(), key=lambda x: (-x[1], x[0]))[:10]:
                lines.append(f"- {alert_type}: {count}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error generating risk dashboard: {str(e)}")
            return f"Error generating risk dashboard: {str(e)}"

    def generate_data_quality_report(self) -> str:
        """
        Generate a data quality report from the latest reports.
        
        Returns:
            str: Human-readable data quality report
        """
        try:
            if not self.compliance_handler:
                return "Error: No compliance handler available"
            
            reports_json = self.compliance_handler.list_compliance_reports(page=1, page_size=99999)
            reports_data = json.loads(reports_json)
            
            if reports_data.get("status") != "success":
                return f"Error: {reports_data.get('message', 'Failed to retrieve reports')}"
            
            total_reports = 0
            field_stats = {
                "claim.business_name": {"present": 0, "missing": 0, "empty": 0, "examples": set()},
                "claim.business_ref": {"present": 0, "missing": 0, "empty": 0, "examples": set()},
                "final_evaluation.alerts": {"present": 0, "missing": 0, "empty": 0},
                "final_evaluation.overall_compliance": {"present": 0, "missing": 0},
                "final_evaluation.overall_risk_level": {"present": 0, "missing": 0, "examples": set()}
            }
            
            for business_ref, reports_list in reports_data.get("reports", {}).items():
                for report_info in reports_list:
                    try:
                        file_path = Path(report_info["file_name"])
                        if report_data := self.file_handler.read_json(file_path):
                            total_reports += 1
                            
                            # Check claim fields
                            claim = report_data.get("claim", {})
                            self._check_field(field_stats, "claim.business_name", 
                                           claim.get("business_name"), store_example=True)
                            self._check_field(field_stats, "claim.business_ref",
                                           claim.get("business_ref"), store_example=True)
                            
                            # Check final evaluation fields
                            final_eval = report_data.get("final_evaluation", {})
                            self._check_field(field_stats, "final_evaluation.alerts",
                                           final_eval.get("alerts"))
                            self._check_field(field_stats, "final_evaluation.overall_compliance",
                                           final_eval.get("overall_compliance"))
                            self._check_field(field_stats, "final_evaluation.overall_risk_level",
                                           final_eval.get("overall_risk_level"), store_example=True)
                            
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        continue
            
            # Format report
            lines = [
                "Firm Data Quality Report",
                "=====================",
                "",
                f"Total Reports Analyzed: {total_reports}",
                "",
                "Field Statistics:",
            ]
            
            for field, stats in field_stats.items():
                present_pct = (stats["present"] / total_reports * 100) if total_reports > 0 else 0
                lines.extend([
                    f"\n{field}:",
                    f"- Present: {stats['present']} ({present_pct:.1f}%)",
                    f"- Missing: {stats['missing']}",
                    f"- Empty: {stats.get('empty', 0)}"
                ])
                
                if "examples" in stats and stats["examples"]:
                    examples = sorted(stats["examples"])[:3]  # Show up to 3 examples
                    lines.append(f"- Examples: {', '.join(str(ex) for ex in examples)}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error generating data quality report: {str(e)}")
            return f"Error generating data quality report: {str(e)}"

    def _check_field(self, stats: Dict[str, Dict[str, Any]], field: str, value: Any, store_example: bool = False) -> None:
        """Helper method for data quality report to check field presence and content."""
        if value is None:
            stats[field]["missing"] += 1
        else:
            stats[field]["present"] += 1
            if isinstance(value, (str, list)) and not value:
                stats[field]["empty"] += 1
            if store_example and value and len(stats[field]["examples"]) < 5:
                stats[field]["examples"].add(str(value)) 