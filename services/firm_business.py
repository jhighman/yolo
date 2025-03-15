"""Service for handling firm-specific business logic.

This module contains the core business logic for processing and analyzing firm-related data,
implementing search strategies and compliance reporting for business entities.
"""

import json
import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from enum import Enum
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from services.firm_services import FirmServicesFacade
from evaluation.firm_evaluation_report_builder import FirmEvaluationReportBuilder
from evaluation.firm_evaluation_report_director import FirmEvaluationReportDirector

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('firm_business', logging.getLogger(__name__))

class SearchStrategy(Enum):
    """Enumeration of available search strategies."""
    TAX_ID_AND_CRD = "tax_id_and_crd"
    TAX_ID_ONLY = "tax_id_only"
    CRD_ONLY = "crd_only"
    NAME_AND_LOCATION = "name_and_location"
    NAME_ONLY = "name_only"
    DEFAULT = "default"

@dataclass
class SearchResult:
    """Data class for search results."""
    source: str
    basic_result: Optional[Dict[str, Any]]
    detailed_result: Optional[Dict[str, Any]]
    search_strategy: SearchStrategy
    compliance: bool
    compliance_explanation: str
    error: Optional[str] = None

def determine_search_strategy(claim: Dict[str, Any]) -> SearchStrategy:
    """
    Analyze the claim to determine the most appropriate search strategy.
    
    Args:
        claim: Dictionary containing business attributes
        
    Returns:
        SearchStrategy: The most appropriate search strategy for the claim
    """
    claim_summary = json.dumps(claim, indent=2)
    logger.info(f"Determining search strategy for claim: {claim_summary}")
    
    tax_id = claim.get('tax_id')
    org_crd = claim.get('organization_crd')
    business_name = claim.get('business_name')
    business_location = claim.get('business_location')
    
    if tax_id and org_crd:
        logger.debug("Selected TAX_ID_AND_CRD strategy based on available tax_id and organization_crd")
        return SearchStrategy.TAX_ID_AND_CRD
    elif tax_id:
        logger.debug("Selected TAX_ID_ONLY strategy based on available tax_id")
        return SearchStrategy.TAX_ID_ONLY
    elif org_crd:
        logger.debug("Selected CRD_ONLY strategy based on available organization_crd")
        return SearchStrategy.CRD_ONLY
    elif business_name and business_location:
        logger.debug("Selected NAME_AND_LOCATION strategy based on available business_name and location")
        return SearchStrategy.NAME_AND_LOCATION
    elif business_name:
        logger.debug("Selected NAME_ONLY strategy based on available business_name")
        return SearchStrategy.NAME_ONLY
    else:
        logger.warning("No usable search attributes found, falling back to DEFAULT strategy")
        return SearchStrategy.DEFAULT

def search_with_tax_id_and_crd(
    claim: Dict[str, Any],
    facade: FirmServicesFacade,
    business_ref: str
) -> SearchResult:
    """Execute search using tax ID and CRD number."""
    try:
        logger.info(f"Searching with tax_id and CRD for business_ref: {business_ref}")
        
        # Search by CRD first since that's our primary identifier
        basic_result = facade.search_firm_by_crd(
            subject_id=business_ref,
            crd_number=claim['organization_crd']
        )
        
        if not basic_result:
            logger.warning(f"No results found for CRD {claim['organization_crd']}")
            return SearchResult(
                source="FINRA/SEC",
                basic_result=None,
                detailed_result=None,
                search_strategy=SearchStrategy.TAX_ID_AND_CRD,
                compliance=False,
                compliance_explanation="No results found for provided CRD number"
            )
            
        # Get detailed information
        detailed_result = facade.get_firm_details(
            subject_id=business_ref,
            crd_number=claim['organization_crd']
        )
        
        return SearchResult(
            source="FINRA/SEC",
            basic_result=basic_result,
            detailed_result=detailed_result,
            search_strategy=SearchStrategy.TAX_ID_AND_CRD,
            compliance=True,
            compliance_explanation="Successfully retrieved firm details using CRD number"
        )
        
    except Exception as e:
        error_msg = f"Error in tax_id_and_crd search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SearchResult(
            source="FINRA/SEC",
            basic_result=None,
            detailed_result=None,
            search_strategy=SearchStrategy.TAX_ID_AND_CRD,
            compliance=False,
            compliance_explanation="Error occurred during search",
            error=error_msg
        )

def search_with_crd_only(
    claim: Dict[str, Any],
    facade: FirmServicesFacade,
    business_ref: str
) -> SearchResult:
    """Execute search using CRD number only."""
    try:
        logger.info(f"Searching with CRD only for business_ref: {business_ref}")
        
        basic_result = facade.search_firm_by_crd(
            subject_id=business_ref,
            crd_number=claim['organization_crd']
        )
        
        if not basic_result:
            logger.warning(f"No results found for CRD {claim['organization_crd']}")
            return SearchResult(
                source="FINRA/SEC",
                basic_result=None,
                detailed_result=None,
                search_strategy=SearchStrategy.CRD_ONLY,
                compliance=False,
                compliance_explanation="No results found for provided CRD number"
            )
            
        detailed_result = facade.get_firm_details(
            subject_id=business_ref,
            crd_number=claim['organization_crd']
        )
        
        return SearchResult(
            source="FINRA/SEC",
            basic_result=basic_result,
            detailed_result=detailed_result,
            search_strategy=SearchStrategy.CRD_ONLY,
            compliance=True,
            compliance_explanation="Successfully retrieved firm details using CRD number"
        )
        
    except Exception as e:
        error_msg = f"Error in crd_only search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SearchResult(
            source="FINRA/SEC",
            basic_result=None,
            detailed_result=None,
            search_strategy=SearchStrategy.CRD_ONLY,
            compliance=False,
            compliance_explanation="Error occurred during search",
            error=error_msg
        )

def search_with_name_only(
    claim: Dict[str, Any],
    facade: FirmServicesFacade,
    business_ref: str
) -> SearchResult:
    """Execute search using business name only."""
    try:
        logger.info(f"Searching with business name only for business_ref: {business_ref}")
        
        search_results = facade.search_firm(
            subject_id=business_ref,
            firm_name=claim['business_name']
        )
        
        if not search_results:
            logger.warning(f"No results found for business name {claim['business_name']}")
            return SearchResult(
                source="FINRA/SEC",
                basic_result=None,
                detailed_result=None,
                search_strategy=SearchStrategy.NAME_ONLY,
                compliance=False,
                compliance_explanation="No results found for provided business name"
            )
            
        # If we found multiple results, use the first one but note it in the explanation
        basic_result = search_results[0]
        compliance_explanation = "Successfully retrieved firm details"
        
        if len(search_results) > 1:
            logger.warning(f"Multiple results found for {claim['business_name']}, using first match")
            compliance_explanation = f"Found {len(search_results)} matches, using first result"
            
        # Get detailed information using the CRD from the basic result
        detailed_result = None
        if crd_number := basic_result.get('crd_number'):
            detailed_result = facade.get_firm_details(
                subject_id=business_ref,
                crd_number=crd_number
            )
        
        return SearchResult(
            source="FINRA/SEC",
            basic_result=basic_result,
            detailed_result=detailed_result,
            search_strategy=SearchStrategy.NAME_ONLY,
            compliance=True,
            compliance_explanation=compliance_explanation
        )
        
    except Exception as e:
        error_msg = f"Error in name_only search: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return SearchResult(
            source="FINRA/SEC",
            basic_result=None,
            detailed_result=None,
            search_strategy=SearchStrategy.NAME_ONLY,
            compliance=False,
            compliance_explanation="Error occurred during search",
            error=error_msg
        )

def search_default(
    claim: Dict[str, Any],
    facade: FirmServicesFacade,
    business_ref: str
) -> SearchResult:
    """Default search strategy when no usable search criteria are available."""
    logger.warning(f"Using default search strategy for business_ref: {business_ref}")
    return SearchResult(
        source="Unknown",
        basic_result=None,
        detailed_result=None,
        search_strategy=SearchStrategy.DEFAULT,
        compliance=False,
        compliance_explanation="Insufficient data provided for search"
    )

def process_claim(
    claim: Dict[str, Any],
    facade: FirmServicesFacade,
    business_ref: Optional[str] = None,
    skip_financials: bool = False,
    skip_legal: bool = False
) -> Dict[str, Any]:
    """
    Process a business claim by determining search strategy and generating a compliance report.
    
    Args:
        claim: Dictionary containing business attributes
        facade: Instance of FirmServicesFacade
        business_ref: Optional business reference ID
        skip_financials: Whether to skip financial due diligence
        skip_legal: Whether to skip legal due diligence
        
    Returns:
        Dictionary containing the compliance report
    """
    claim_summary = json.dumps(claim, indent=2)
    logger.info(f"Processing claim with parameters: {claim_summary}")
    
    # Use business_ref from claim or default
    business_ref = business_ref or claim.get('business_ref', 'BIZ_DEFAULT')
    
    try:
        # Determine and execute search strategy
        strategy = determine_search_strategy(claim)
        search_result = None
        
        if strategy == SearchStrategy.TAX_ID_AND_CRD:
            search_result = search_with_tax_id_and_crd(claim, facade, business_ref)
        elif strategy == SearchStrategy.CRD_ONLY:
            search_result = search_with_crd_only(claim, facade, business_ref)
        elif strategy == SearchStrategy.NAME_ONLY:
            search_result = search_with_name_only(claim, facade, business_ref)
        else:
            search_result = search_default(claim, facade, business_ref)
            
        # Prepare extracted information
        extracted_info = {
            "search_evaluation": {
                "source": search_result.source,
                "compliance": search_result.compliance,
                "compliance_explanation": search_result.compliance_explanation,
                "error": search_result.error
            },
            "business": search_result.detailed_result or search_result.basic_result or {},
            "business_name": claim.get('business_name', ''),
            "locations": [],
            "financials_evaluation": {"status": "Skipped"},
            "legal_evaluation": {"status": "Skipped"}
        }
        
        # Build and return the report
        builder = FirmEvaluationReportBuilder(claim.get('reference_id', 'UNKNOWN'))
        director = FirmEvaluationReportDirector()
        
        report = director.construct_evaluation_report(claim, extracted_info)
        
        try:
            # Save the report
            facade.save_business_report(report, business_ref)
            logger.info(f"Successfully saved report for business_ref: {business_ref}")
        except Exception as e:
            logger.error(f"Failed to save report for business_ref {business_ref}: {str(e)}")
        
        return report
        
    except Exception as e:
        error_msg = f"Error processing claim: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "error": error_msg,
            "compliance": False,
            "compliance_explanation": "Error occurred during claim processing"
        }