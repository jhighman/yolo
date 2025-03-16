"""
cache_manager/cli.py

This module provides a command-line interface for interacting with the cache management system.
It supports operations for clearing cache, listing files, retrieving compliance reports,
and generating summaries across businesses.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from firm_cache_manager import FirmCacheManager
from cache_manager.firm_compliance_handler import FirmComplianceHandler
from cache_manager.summary_generator import SummaryGenerator
from cache_manager.file_handler import FileHandler

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('cli', logging.getLogger(__name__))

def setup_argparser() -> argparse.ArgumentParser:
    """Set up the argument parser with all supported commands and options."""
    parser = argparse.ArgumentParser(
        description="Cache Manager CLI - Manage business compliance cache and reports"
    )
    
    # Cache location
    parser.add_argument(
        "--cache-folder",
        type=str,
        help="Override the default cache folder location"
    )
    
    # Cache operations
    parser.add_argument(
        "--clear-cache",
        nargs="?",
        const="ALL",
        help="Clear all cache (except FirmComplianceReport) for a business or all businesses if 'ALL' or no value is specified"
    )
    
    parser.add_argument(
        "--clear-compliance",
        type=str,
        help="Clear only FirmComplianceReport cache for a business"
    )
    
    parser.add_argument(
        "--clear-agent",
        nargs=2,
        metavar=("BUSINESS_REF", "AGENT_NAME"),
        help="Clear cache for a specific agent under a business"
    )
    
    parser.add_argument(
        "--list-cache",
        nargs="?",
        const="ALL",
        help="List all cached files (or specify a business)"
    )
    
    parser.add_argument(
        "--cleanup-stale",
        action="store_true",
        help="Delete stale cache older than 90 days"
    )
    
    # Compliance report operations
    parser.add_argument(
        "--get-latest-compliance",
        type=str,
        help="Get the latest compliance report for a business"
    )
    
    parser.add_argument(
        "--get-compliance-by-ref",
        nargs=2,
        metavar=("BUSINESS_REF", "REFERENCE_ID"),
        help="Get compliance report by reference ID"
    )
    
    parser.add_argument(
        "--list-compliance-reports",
        nargs="?",
        const=None,
        help="List all compliance reports with latest revision (or specify a business)"
    )
    
    # Summary operations
    parser.add_argument(
        "--generate-compliance-summary",
        type=str,
        help="Generate a compliance summary for a specific business"
    )
    
    parser.add_argument(
        "--generate-all-summaries",
        action="store_true",
        help="Generate a compliance summary for all businesses"
    )
    
    # Analysis operations
    parser.add_argument(
        "--generate-taxonomy",
        action="store_true",
        help="Generate a taxonomy tree from latest compliance reports"
    )
    
    parser.add_argument(
        "--generate-risk-dashboard",
        action="store_true",
        help="Generate a risk dashboard from latest compliance reports"
    )
    
    parser.add_argument(
        "--generate-data-quality",
        action="store_true",
        help="Generate a data quality report from latest compliance reports"
    )
    
    # Pagination options
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="Page number for paginated results (default: 1)"
    )
    
    parser.add_argument(
        "--page-size",
        type=int,
        default=10,
        help="Number of items per page (default: 10)"
    )
    
    return parser

def format_output(result: Union[str, Dict[str, Any]], indent: int = 2) -> None:
    """Format and print the command output."""
    if isinstance(result, str):
        try:
            # Try to parse as JSON first
            parsed = json.loads(result)
            print(json.dumps(parsed, indent=indent))
        except json.JSONDecodeError:
            # If not JSON, print as plain text
            print(result)
    else:
        print(json.dumps(result, indent=indent))

def main() -> None:
    """Main entry point for the CLI."""
    parser = setup_argparser()
    args = parser.parse_args()
    
    try:
        # Initialize cache folder
        cache_folder = Path(args.cache_folder) if args.cache_folder else None
        
        # Initialize managers and handlers
        cache_manager = (
            FirmCacheManager(cache_folder=cache_folder)
            if cache_folder
            else FirmCacheManager()
        )
        
        compliance_handler = (
            FirmComplianceHandler(cache_folder=cache_folder)
            if cache_folder
            else FirmComplianceHandler()
        )
        
        file_handler = FileHandler(base_path=cache_folder if cache_folder else Path.cwd())
        
        summary_generator = SummaryGenerator(
            file_handler=file_handler,
            compliance_handler=compliance_handler
        )
        
        result: Optional[Union[str, Dict[str, Any]]] = None
        
        # Execute requested operation
        if args.clear_cache:
            if args.clear_cache == "ALL":
                # Clear cache for all businesses
                result = {}
                for biz_path in cache_manager.cache_folder.iterdir():
                    if biz_path.is_dir():
                        biz_result = json.loads(cache_manager.clear_cache(biz_path.name))
                        result[biz_path.name] = biz_result
            else:
                result = cache_manager.clear_cache(args.clear_cache)
                
        elif args.clear_compliance:
            result = cache_manager.clear_compliance_cache(args.clear_compliance)
            
        elif args.clear_agent:
            business_ref, agent = args.clear_agent
            result = cache_manager.clear_agent_cache(business_ref, agent)
            
        elif args.list_cache:
            result = cache_manager.list_cache(args.list_cache)
            
        elif args.cleanup_stale:
            result = cache_manager.cleanup_stale_cache()
            
        elif args.get_latest_compliance:
            result = cache_manager.get_latest_compliance_report(
                args.get_latest_compliance
            )
            
        elif args.get_compliance_by_ref:
            business_ref, ref_id = args.get_compliance_by_ref
            result = cache_manager.get_compliance_report_by_ref(
                business_ref,
                ref_id
            )
            
        elif args.list_compliance_reports is not None:
            result = cache_manager.list_compliance_reports(
                business_ref=args.list_compliance_reports,
                page=args.page,
                page_size=args.page_size
            )
            
        elif args.generate_compliance_summary:
            firm_path = cache_manager.cache_folder / args.generate_compliance_summary
            result = summary_generator.generate_compliance_summary(
                firm_path=firm_path,
                business_ref=args.generate_compliance_summary,
                page=args.page,
                page_size=args.page_size
            )
            
        elif args.generate_all_summaries:
            result = summary_generator.generate_all_compliance_summaries(
                cache_folder=cache_manager.cache_folder,
                page=args.page,
                page_size=args.page_size
            )
            
        elif args.generate_taxonomy:
            result = summary_generator.generate_taxonomy_from_latest_reports()
            
        elif args.generate_risk_dashboard:
            result = summary_generator.generate_risk_dashboard()
            
        elif args.generate_data_quality:
            result = summary_generator.generate_data_quality_report()
            
        else:
            parser.print_help()
            return
        
        if result is not None:
            format_output(result)
            
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}", exc_info=True)
        print(json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main() 