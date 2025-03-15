"""Service for handling firm-specific business logic.

This module contains the core business logic for processing and analyzing firm-related data,
implementing search strategies, compliance reporting, and risk evaluation for business entities.
It integrates search functionality with compliance evaluation and report generation to provide
comprehensive business intelligence and due diligence reporting.
"""

import json
import logging
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Set, Callable, Optional
from enum import Enum
from datetime import datetime

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from evaluation.firm_evaluation_processor import (
    evaluate_registration_status,
    evaluate_regulatory_oversight,
    evaluate_disclosures,
    evaluate_financials,
    evaluate_legal,
    evaluate_qualifications,
    evaluate_data_integrity,
    Alert,
    AlertSeverity
)
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import (
    FirmEvaluationReportDirector,
    InvalidDataError,
    EvaluationProcessError
)

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('firm_business', logging.getLogger(__name__))

class SearchImplementationStatus:
    """Registry to track which search strategies are implemented."""
    
    _implemented_strategies: Set[str] = set()
    
    @classmethod
    def register_implementation(cls, strategy: str) -> None:
        """Register a strategy as implemented."""
        cls._implemented_strategies.add(strategy)
    
    @classmethod
    def is_implemented(cls, strategy: str) -> bool:
        """Check if a strategy is implemented."""
        return strategy in cls._implemented_strategies
    
    @classmethod
    def get_implemented_strategies(cls) -> Set[str]:
        """Get all implemented strategies."""
        return cls._implemented_strategies.copy()

def implemented_strategy(strategy_name: str):
    """Decorator to mark a search function as implemented for a specific strategy."""
    def decorator(func):
        SearchImplementationStatus.register_implementation(strategy_name)
        return func
    return decorator

class SearchStrategy(Enum):
    """Enumeration of available search strategies."""
    TAX_ID_AND_CRD = "tax_id_and_crd"
    TAX_ID_ONLY = "tax_id_only"
    CRD_ONLY = "crd_only"
    SEC_NUMBER_ONLY = "sec_number_only"
    NAME_AND_LOCATION = "name_and_location"
    NAME_ONLY = "name_only"
    DEFAULT = "default"

def determine_search_strategy(claim: Dict[str, Any]) -> SearchStrategy:
    """
    Analyze the claim to determine the most appropriate search strategy.
    
    Args:
        claim: Dictionary containing business attributes
        
    Returns:
        SearchStrategy: The most appropriate search strategy for the claim.
        If the optimal strategy is not implemented, falls back to the next best implemented strategy.
    """
    claim_summary = json.dumps(claim, indent=2)
    logger.info(f"Determining search strategy for claim: {claim_summary}")
    
    tax_id = claim.get('tax_id')
    org_crd = claim.get('organization_crd')
    sec_number = claim.get('sec_number')
    business_name = claim.get('business_name')
    business_location = claim.get('business_location')
    
    # Define strategy selection in order of preference
    if tax_id and org_crd and SearchImplementationStatus.is_implemented(SearchStrategy.TAX_ID_AND_CRD.value):
        logger.debug("Selected TAX_ID_AND_CRD strategy based on available tax_id and organization_crd")
        return SearchStrategy.TAX_ID_AND_CRD
        
    if tax_id and SearchImplementationStatus.is_implemented(SearchStrategy.TAX_ID_ONLY.value):
        logger.debug("Selected TAX_ID_ONLY strategy based on available tax_id")
        return SearchStrategy.TAX_ID_ONLY
        
    if org_crd and SearchImplementationStatus.is_implemented(SearchStrategy.CRD_ONLY.value):
        logger.debug("Selected CRD_ONLY strategy based on available organization_crd")
        return SearchStrategy.CRD_ONLY
        
    if sec_number and SearchImplementationStatus.is_implemented(SearchStrategy.SEC_NUMBER_ONLY.value):
        logger.debug("Selected SEC_NUMBER_ONLY strategy based on available sec_number")
        return SearchStrategy.SEC_NUMBER_ONLY
        
    if business_name and business_location and SearchImplementationStatus.is_implemented(SearchStrategy.NAME_AND_LOCATION.value):
        logger.debug("Selected NAME_AND_LOCATION strategy based on available business_name and location")
        return SearchStrategy.NAME_AND_LOCATION
        
    if business_name and SearchImplementationStatus.is_implemented(SearchStrategy.NAME_ONLY.value):
        logger.debug("Selected NAME_ONLY strategy based on available business_name")
        return SearchStrategy.NAME_ONLY
    
    # Log which strategies were considered but not implemented
    if tax_id and org_crd:
        logger.warning("TAX_ID_AND_CRD strategy would be optimal but is not implemented")
    elif tax_id:
        logger.warning("TAX_ID_ONLY strategy would be optimal but is not implemented")
    elif org_crd:
        logger.warning("CRD_ONLY strategy would be optimal but is not implemented")
    elif sec_number:
        logger.warning("SEC_NUMBER_ONLY strategy would be optimal but is not implemented")
    elif business_name and business_location:
        logger.warning("NAME_AND_LOCATION strategy would be optimal but is not implemented")
    elif business_name:
        logger.warning("NAME_ONLY strategy would be optimal but is not implemented")
    
    logger.warning("No usable or implemented search strategies found, falling back to DEFAULT strategy")
    return SearchStrategy.DEFAULT

def print_strategy_info(strategy: SearchStrategy, claim: Dict[str, Any]) -> None:
    """Print information about the selected strategy and claim data."""
    print("\nSelected Strategy:", strategy.value)
    print("\nClaim Data:")
    print(json.dumps(claim, indent=2))
    print("\nImplemented Strategies:")
    implemented = SearchImplementationStatus.get_implemented_strategies()
    for strategy_enum in SearchStrategy:
        status = "✓ Implemented" if strategy_enum.value in implemented else "✗ Not Implemented"
        print(f"{strategy_enum.value:20} {status}")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Firm Business CLI - Test search strategy determination"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive menu mode"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)"
    )
    
    # Register implemented strategies
    SearchImplementationStatus.register_implementation(SearchStrategy.TAX_ID_AND_CRD.value)
    SearchImplementationStatus.register_implementation(SearchStrategy.CRD_ONLY.value)
    SearchImplementationStatus.register_implementation(SearchStrategy.NAME_ONLY.value)
    SearchImplementationStatus.register_implementation(SearchStrategy.DEFAULT.value)
    
    return parser.parse_args()

def interactive_menu() -> None:
    """Run an interactive menu for testing search strategy determination."""
    while True:
        print("\n=== Search Strategy Testing Menu ===")
        print("1. Test with tax_id and CRD")
        print("2. Test with CRD only")
        print("3. Test with SEC number")
        print("4. Test with business name and location")
        print("5. Test with business name only")
        print("6. Test with empty claim")
        print("7. Show implemented strategies")
        print("8. Exit")
        
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == "1":
            claim = {
                "tax_id": input("Enter tax_id: ").strip(),
                "organization_crd": input("Enter CRD number: ").strip(),
                "business_name": input("Enter business name (optional): ").strip() or None
            }
            claim = {k: v for k, v in claim.items() if v is not None}
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "2":
            claim = {
                "organization_crd": input("Enter CRD number: ").strip(),
                "business_name": input("Enter business name (optional): ").strip() or None
            }
            claim = {k: v for k, v in claim.items() if v is not None}
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "3":
            claim = {
                "sec_number": input("Enter SEC number: ").strip(),
                "business_name": input("Enter business name (optional): ").strip() or None
            }
            claim = {k: v for k, v in claim.items() if v is not None}
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "4":
            claim = {
                "business_name": input("Enter business name: ").strip(),
                "business_location": input("Enter business location: ").strip()
            }
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "5":
            claim = {
                "business_name": input("Enter business name: ").strip()
            }
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "6":
            claim = {}
            strategy = determine_search_strategy(claim)
            print_strategy_info(strategy, claim)
            
        elif choice == "7":
            implemented = SearchImplementationStatus.get_implemented_strategies()
            print("\nImplemented Strategies:")
            for strategy_enum in SearchStrategy:
                status = "✓ Implemented" if strategy_enum.value in implemented else "✗ Not Implemented"
                print(f"{strategy_enum.value:20} {status}")
            
        elif choice == "8":
            print("\nExiting...")
            break
            
        else:
            print("\nInvalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Configure logging with user-specified level
    log_level = getattr(logging, args.log_level)
    loggers = setup_logging(debug=(log_level == logging.DEBUG))
    logger = loggers.get('firm_business', logging.getLogger(__name__))
    
    # Set log level for all loggers
    for logger_name in loggers:
        if isinstance(logger_name, str) and not logger_name.startswith('_'):
            loggers[logger_name].setLevel(log_level)
    
    if args.interactive:
        interactive_menu()
    else:
        print("Please use --interactive flag to test search strategies")
        return

@implemented_strategy(SearchStrategy.TAX_ID_AND_CRD.value)
def search_with_tax_id_and_org_crd(
    claim: Dict[str, Any],
    facade: Any,
    business_ref: str
) -> Dict[str, Any]:
    """Search using tax ID and CRD number."""
    tax_id = claim.get('tax_id')
    org_crd = claim.get('organization_crd')
    
    logger.info(f"Searching with tax_id and CRD", extra={
        "tax_id": tax_id,
        "org_crd": org_crd,
        "business_ref": business_ref
    })
    
    result = facade.search_firm_by_crd(business_ref, org_crd)
    if result:
        return {
            "compliance": True,
            "compliance_explanation": "Found by CRD",
            "source": "FINRA",
            "basic_result": result,
            "detailed_result": facade.get_firm_details(business_ref, org_crd),
            "timestamp": datetime.now().isoformat()
        }
    return {
        "compliance": False,
        "compliance_explanation": "Not found by CRD",
        "source": "FINRA",
        "timestamp": datetime.now().isoformat()
    }

@implemented_strategy(SearchStrategy.CRD_ONLY.value)
def search_with_crd_only(
    claim: Dict[str, Any],
    facade: Any,
    business_ref: str
) -> Dict[str, Any]:
    """Search using CRD number only."""
    org_crd = claim.get('organization_crd')
    
    logger.info(f"Searching with CRD only", extra={
        "org_crd": org_crd,
        "business_ref": business_ref
    })
    
    result = facade.search_firm_by_crd(business_ref, org_crd)
    if result:
        return {
            "compliance": True,
            "compliance_explanation": "Found by CRD",
            "source": "FINRA",
            "basic_result": result,
            "detailed_result": facade.get_firm_details(business_ref, org_crd),
            "timestamp": datetime.now().isoformat()
        }
    return {
        "compliance": False,
        "compliance_explanation": "Not found by CRD",
        "source": "FINRA",
        "timestamp": datetime.now().isoformat()
    }

@implemented_strategy(SearchStrategy.NAME_ONLY.value)
def search_with_name_only(
    claim: Dict[str, Any],
    facade: Any,
    business_ref: str
) -> Dict[str, Any]:
    """Search using business name only."""
    business_name = claim.get('business_name')
    
    logger.info(f"Searching with business name only", extra={
        "business_name": business_name,
        "business_ref": business_ref
    })
    
    results = facade.search_firm(business_ref, business_name)
    if results:
        # Use first match
        result = results[0]
        org_crd = result.get('organization_crd')
        if org_crd:
            return {
                "compliance": True,
                "compliance_explanation": "Found by name",
                "source": "FINRA",
                "basic_result": result,
                "detailed_result": facade.get_firm_details(business_ref, org_crd),
                "timestamp": datetime.now().isoformat()
            }
    return {
        "compliance": False,
        "compliance_explanation": "Not found by name",
        "source": "FINRA",
        "timestamp": datetime.now().isoformat()
    }

@implemented_strategy(SearchStrategy.DEFAULT.value)
def search_with_default(
    claim: Dict[str, Any],
    facade: Any,
    business_ref: str
) -> Dict[str, Any]:
    """Default search strategy when no other strategy is applicable."""
    business_name = claim.get('business_name')
    
    logger.info(f"Using default search strategy", extra={
        "business_name": business_name,
        "business_ref": business_ref
    })
    
    if business_name:
        return search_with_name_only(claim, facade, business_ref)
    
    return {
        "compliance": False,
        "compliance_explanation": "Insufficient search criteria",
        "source": "UNKNOWN",
        "timestamp": datetime.now().isoformat()
    }

def process_claim(
    claim: Dict[str, Any],
    facade: Any,  # BusinessServicesFacade instance
    business_ref: Optional[str] = None,
    skip_financials: bool = False,
    skip_legal: bool = False
) -> Dict[str, Any]:
    """Process a business claim by executing search, evaluation, and report generation.
    
    Args:
        claim: Dictionary containing business attributes
        facade: BusinessServicesFacade instance for data retrieval
        business_ref: Optional business reference ID
        skip_financials: Flag to skip financial evaluation
        skip_legal: Flag to skip legal evaluation
        
    Returns:
        Dictionary containing the complete compliance report
        
    Raises:
        InvalidDataError: If claim data is invalid
        EvaluationProcessError: If evaluation process fails
    """
    claim_summary = json.dumps(claim, indent=2)
    logger.info(f"Processing claim: {claim_summary}", extra={
        "skip_financials": skip_financials,
        "skip_legal": skip_legal,
        "timestamp": datetime.now().isoformat()
    })
    
    # Set business reference
    if business_ref is None:
        business_ref = claim.get("business_ref", "BIZ_DEFAULT")
    
    # At this point business_ref is guaranteed to be a string
    assert business_ref is not None
    business_ref_str: str = business_ref
    
    try:
        # Determine and execute search strategy
        strategy_type = determine_search_strategy(claim)
        logger.info(f"Selected search strategy: {strategy_type.value}")
        
        search_evaluation = {
            "compliance": False,
            "compliance_explanation": "Search not performed",
            "source": "UNKNOWN",
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Execute the appropriate search function based on strategy type
            if strategy_type == SearchStrategy.TAX_ID_AND_CRD:
                search_evaluation = search_with_tax_id_and_org_crd(claim, facade, business_ref_str)
            elif strategy_type == SearchStrategy.CRD_ONLY:
                search_evaluation = search_with_crd_only(claim, facade, business_ref_str)
            elif strategy_type == SearchStrategy.NAME_ONLY:
                search_evaluation = search_with_name_only(claim, facade, business_ref_str)
            else:
                search_evaluation = search_with_default(claim, facade, business_ref_str)
                
        except Exception as e:
            logger.error(f"Search strategy failed: {str(e)}", exc_info=True)
            search_evaluation.update({
                "compliance": False,
                "compliance_explanation": f"Search failed: {str(e)}",
                "error": str(e),
                "error_type": type(e).__name__
            })
        
        # Prepare extracted info for evaluation
        extracted_info = {
            "search_evaluation": search_evaluation,
            "business": {},
            "business_name": "",
            "disclosures": [],
            "accountant_exams": [],
            "locations": []
        }
        
        if search_evaluation.get("compliance", False):
            basic_result = search_evaluation.get("basic_result", {})
            detailed_result = search_evaluation.get("detailed_result", {})
            
            extracted_info.update({
                "business": basic_result,
                "business_name": basic_result.get("business_name", ""),
                "disclosures": detailed_result.get("disclosures", []),
                "accountant_exams": detailed_result.get("accountant_exams", []),
                "locations": detailed_result.get("locations", [])
            })
            
            # Add skip flags to extracted info
            if skip_financials:
                extracted_info["skip_financials"] = True
            if skip_legal:
                extracted_info["skip_legal"] = True
        
        # Initialize report builder and director
        builder = FirmEvaluationReportBuilder(claim.get("reference_id", "UNKNOWN"))
        director = FirmEvaluationReportDirector(builder)
        
        # Generate evaluation report
        try:
            report = director.construct_evaluation_report(claim, extracted_info)
            logger.info("Evaluation report generated successfully", extra={
                "business_ref": business_ref_str,
                "report_sections": list(report.keys()),
                "timestamp": datetime.now().isoformat()
            })
        except (InvalidDataError, EvaluationProcessError) as e:
            logger.error(f"Failed to generate evaluation report: {str(e)}", exc_info=True)
            raise
        
        # Save report
        try:
            facade.save_business_report(report, business_ref_str)
            logger.info("Business report saved successfully", extra={
                "business_ref": business_ref_str,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to save business report: {str(e)}", exc_info=True)
            raise EvaluationProcessError(f"Failed to save business report: {str(e)}")
        
        logger.info("Claim processing completed", extra={
            "business_ref": business_ref_str,
            "claim_summary": claim_summary,
            "timestamp": datetime.now().isoformat()
        })
        
        return report
        
    except Exception as e:
        logger.error(f"Unexpected error in process_claim: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()