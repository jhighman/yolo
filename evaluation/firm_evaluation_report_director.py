"""
firm_evaluation_report_director.py

This module defines the FirmEvaluationReportDirector class for orchestrating the construction
of comprehensive compliance reports for business entities. It coordinates evaluation steps,
handles skip/failure logic, and delegates report assembly to the FirmEvaluationReportBuilder.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
import sys
from pathlib import Path
from datetime import datetime
import time
import json

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging
from .firm_evaluation_report_builder import FirmEvaluationReportBuilder
from .firm_evaluation_processor import (
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

# Initialize logging
loggers = setup_logging(debug=True)
logger = loggers.get('firm_evaluation_report_director', logging.getLogger(__name__))

class FirmEvaluationError(Exception):
    """Base exception for firm evaluation errors."""
    pass

class InvalidDataError(FirmEvaluationError):
    """Exception raised when input data is invalid or missing required fields."""
    pass

class EvaluationProcessError(FirmEvaluationError):
    """Exception raised when an evaluation process fails."""
    pass

class FirmEvaluationReportDirector:
    """Orchestrates the construction of firm-specific compliance reports."""
    
    REQUIRED_CLAIM_FIELDS = ['business_name', 'business_ref']
    REQUIRED_INFO_FIELDS = ['search_evaluation']
    
    def __init__(self, builder: FirmEvaluationReportBuilder):
        """Initialize the director with a builder instance.
        
        Args:
            builder: A FirmEvaluationReportBuilder object for report construction
            
        Raises:
            TypeError: If builder is not a FirmEvaluationReportBuilder instance
        """
        if not isinstance(builder, FirmEvaluationReportBuilder):
            logger.error("Invalid builder type provided", extra={
                "builder_type": type(builder).__name__,
                "expected_type": "FirmEvaluationReportBuilder"
            })
            raise TypeError("Builder must be an instance of FirmEvaluationReportBuilder")
        self.builder = builder
        self.evaluation_start_time = None
        self.section_timings = {}
        
        logger.info("FirmEvaluationReportDirector initialized", extra={
            "builder_id": id(builder),
            "timestamp": datetime.now().isoformat()
        })

    def _log_timing(self, section: str, duration: float) -> None:
        """Log timing information for a section.
        
        Args:
            section: Name of the section being timed
            duration: Duration in seconds
        """
        self.section_timings[section] = duration
        logger.debug(f"Section timing", extra={
            "section": section,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat()
        })

    def _validate_input_data(self, claim: Dict[str, Any], extracted_info: Dict[str, Any]) -> None:
        """Validate input data for required fields and data types.
        
        Args:
            claim: Dictionary with claim data
            extracted_info: Dictionary with pre-retrieved business data
            
        Raises:
            InvalidDataError: If required fields are missing or invalid
        """
        logger.debug("Validating input data", extra={
            "claim_keys": list(claim.keys() if isinstance(claim, dict) else []),
            "extracted_info_keys": list(extracted_info.keys() if isinstance(extracted_info, dict) else [])
        })
        
        # Validate claim data
        if not isinstance(claim, dict):
            raise InvalidDataError("Claim must be a dictionary")
            
        missing_claim_fields = [field for field in self.REQUIRED_CLAIM_FIELDS if field not in claim]
        if missing_claim_fields:
            raise InvalidDataError(f"Missing required claim fields: {', '.join(missing_claim_fields)}")
            
        # Validate extracted info
        if not isinstance(extracted_info, dict):
            raise InvalidDataError("Extracted info must be a dictionary")
            
        missing_info_fields = [field for field in self.REQUIRED_INFO_FIELDS if field not in extracted_info]
        if missing_info_fields:
            raise InvalidDataError(f"Missing required extracted info fields: {', '.join(missing_info_fields)}")

    def _create_skip_evaluation(
        self,
        explanation: str,
        alert: Optional[Alert] = None,
        due_diligence: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a skipped evaluation result.
        
        Args:
            explanation: Reason for skipping
            alert: Optional alert to include
            due_diligence: Optional due diligence data
            
        Returns:
            Dictionary with compliance status and explanation
            
        Raises:
            ValueError: If explanation is empty or invalid
        """
        logger.debug("Creating skip evaluation", extra={
            "explanation": explanation,
            "has_alert": alert is not None,
            "has_due_diligence": due_diligence is not None,
            "timestamp": datetime.now().isoformat()
        })
        
        if not explanation or not isinstance(explanation, str):
            raise ValueError("Explanation must be a non-empty string")
            
        result = {
            "compliance": True,
            "explanation": explanation,
            "alerts": [alert.to_dict()] if alert else [],
            "skipped": True,
            "skip_timestamp": datetime.now().isoformat()
        }
        
        if due_diligence:
            if not isinstance(due_diligence, dict):
                raise ValueError("Due diligence data must be a dictionary")
            result["due_diligence"] = due_diligence
            
        return result

    def _determine_risk_level(self, alerts: List[Alert]) -> str:
        """Determine overall risk level based on alert severities.
        
        Args:
            alerts: List of Alert objects
            
        Returns:
            Risk level string ("High", "Medium", or "Low")
            
        Raises:
            TypeError: If alerts is not a list
        """
        logger.debug("Determining risk level", extra={
            "total_alerts": len(alerts) if isinstance(alerts, list) else 0,
            "alert_types": [a.alert_type for a in alerts if a is not None] if isinstance(alerts, list) else [],
            "timestamp": datetime.now().isoformat()
        })
        
        if not isinstance(alerts, list):
            raise TypeError("Alerts must be a list")
        
        # Filter out None values
        valid_alerts = [alert for alert in alerts if alert is not None]
        
        has_high = any(alert.severity == AlertSeverity.HIGH for alert in valid_alerts)
        has_medium = any(alert.severity == AlertSeverity.MEDIUM for alert in valid_alerts)
        
        if has_high:
            return "High"
        elif has_medium:
            return "Medium"
        return "Low"

    def _safe_evaluate(
        self,
        evaluator,
        *args,
        section_name: str
    ) -> Tuple[bool, str, List[Alert]]:
        """Safely execute an evaluation function with error handling.
        
        Args:
            evaluator: Evaluation function to call
            *args: Arguments to pass to the evaluator
            section_name: Name of the section being evaluated
            
        Returns:
            Tuple of (compliance, explanation, alerts)
            
        Raises:
            EvaluationProcessError: If evaluation fails
        """
        start_time = time.time()
        logger.info(f"Starting evaluation of {section_name}", extra={
            "section": section_name,
            "evaluator": evaluator.__name__ if hasattr(evaluator, "__name__") else str(evaluator),
            "args_count": len(args),
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            result = evaluator(*args)
            duration = time.time() - start_time
            self._log_timing(section_name, duration)
            
            compliant, explanation, alerts = result
            logger.info(f"Completed evaluation of {section_name}", extra={
                "section": section_name,
                "duration_seconds": duration,
                "compliant": compliant,
                "alert_count": len(alerts),
                "alert_types": [a.alert_type for a in alerts if a is not None],
                "alert_severities": [a.severity.value for a in alerts if a is not None],
                "timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self._log_timing(section_name, duration)
            
            error_msg = f"Error evaluating {section_name}: {str(e)}"
            logger.error(error_msg, extra={
                "section": section_name,
                "error_type": type(e).__name__,
                "error_details": str(e),
                "duration_seconds": duration,
                "timestamp": datetime.now().isoformat()
            }, exc_info=True)
            
            error_alert = Alert(
                alert_type="EvaluationError",
                severity=AlertSeverity.HIGH,
                metadata={
                    "section": section_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration,
                    "timestamp": datetime.now().isoformat()
                },
                description=error_msg
            )
            
            return False, error_msg, [error_alert]

    def construct_evaluation_report(
        self,
        claim: Dict[str, Any],
        extracted_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Construct a full evaluation report by performing evaluation steps.
        
        Args:
            claim: Dictionary with claim data
            extracted_info: Dictionary with pre-retrieved business data
            
        Returns:
            Ordered dictionary representing the completed report
            
        Raises:
            InvalidDataError: If input data is invalid
            EvaluationProcessError: If evaluation process fails
        """
        self.evaluation_start_time = time.time()
        
        try:
            # Validate input data
            self._validate_input_data(claim, extracted_info)
            
            business_name = claim.get('business_name', 'Unknown')
            business_ref = claim.get('business_ref')
            
            logger.info("Starting evaluation report construction", extra={
                "business_name": business_name,
                "business_ref": business_ref,
                "timestamp": datetime.now().isoformat(),
                "claim_fields": list(claim.keys()),
                "extracted_info_size": len(json.dumps(extracted_info))
            })
            
            # Set basic data with error handling
            try:
                self.builder.set_claim(claim)
                logger.debug("Claim data set successfully", extra={
                    "business_name": business_name,
                    "business_ref": business_ref
                })
            except Exception as e:
                logger.error("Failed to set claim data", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "business_name": business_name,
                    "business_ref": business_ref
                }, exc_info=True)
                raise EvaluationProcessError(f"Failed to set claim data: {str(e)}")
            
            # Get or create search evaluation
            search_evaluation = extracted_info.get("search_evaluation", {
                "source": "Unknown",
                "compliance": False,
                "compliance_explanation": "No search performed",
                "timestamp": datetime.now().isoformat()
            })
            
            logger.debug("Search evaluation data", extra={
                "search_source": search_evaluation.get("source"),
                "search_compliance": search_evaluation.get("compliance"),
                "business_name": business_name
            })
            
            try:
                self.builder.set_search_evaluation(search_evaluation)
            except Exception as e:
                logger.error("Failed to set search evaluation", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "business_name": business_name
                }, exc_info=True)
                raise EvaluationProcessError(f"Failed to set search evaluation: {str(e)}")
            
            # Check skip or failure conditions
            skip_reasons = search_evaluation.get("skip_reasons", [])
            search_failed = not search_evaluation.get("compliance", False)
            
            if skip_reasons or search_failed:
                logger.info("Skip or failure condition detected", extra={
                    "business_name": business_name,
                    "skip_reasons": skip_reasons,
                    "search_failed": search_failed,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Create appropriate alert
                if search_failed:
                    alert = Alert(
                        alert_type="BusinessNotFound",
                        severity=AlertSeverity.HIGH,
                        metadata={
                            "business_ref": business_ref,
                            "business_name": business_name,
                            "timestamp": datetime.now().isoformat()
                        },
                        description="Business not found in search"
                    )
                    explanation = "Business not found in search"
                else:
                    alert = Alert(
                        alert_type="RecordSkipped",
                        severity=AlertSeverity.LOW,
                        metadata={
                            "reasons": skip_reasons,
                            "business_ref": business_ref,
                            "timestamp": datetime.now().isoformat()
                        },
                        description=f"Record skipped: {', '.join(skip_reasons)}"
                    )
                    explanation = f"Record skipped: {', '.join(skip_reasons)}"
                
                # Set all evaluations to skipped state with error handling
                try:
                    self.builder.set_registration_status(
                        self._create_skip_evaluation(explanation, alert))
                    self.builder.set_regulatory_oversight(
                        self._create_skip_evaluation(explanation, None))
                    self.builder.set_disclosures(
                        self._create_skip_evaluation(f"No disclosures evaluated: {explanation}", None))
                    self.builder.set_financials(
                        self._create_skip_evaluation(explanation, None))
                    self.builder.set_legal(
                        self._create_skip_evaluation(explanation, None, 
                            extracted_info.get("legal", {}).get("due_diligence", {})))
                    self.builder.set_qualifications(
                        self._create_skip_evaluation(explanation, None))
                    self.builder.set_data_integrity(
                        self._create_skip_evaluation(explanation, None))
                except Exception as e:
                    raise EvaluationProcessError(f"Failed to set skipped evaluations: {str(e)}")
                
            else:
                logger.info("Proceeding with full evaluation", extra={
                    "business_name": business_name,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Perform full evaluation with error handling
                business_info = extracted_info
                
                # Registration status
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_registration_status,
                    business_info,
                    section_name="registration_status"
                )
                self.builder.set_registration_status({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Regulatory oversight
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_regulatory_oversight,
                    business_info,
                    business_name,
                    section_name="regulatory_oversight"
                )
                self.builder.set_regulatory_oversight({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Disclosures
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_disclosures,
                    extracted_info.get("disclosures", []),
                    business_name,
                    section_name="disclosures"
                )
                self.builder.set_disclosures({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Financials
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_financials,
                    business_info,
                    business_name,
                    section_name="financials"
                )
                self.builder.set_financials({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Legal
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_legal,
                    business_info,
                    business_name,
                    extracted_info.get("legal", {}).get("due_diligence"),
                    section_name="legal"
                )
                legal_eval = {
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                }
                if "due_diligence" in extracted_info.get("legal", {}):
                    legal_eval["due_diligence"] = extracted_info["legal"]["due_diligence"]
                self.builder.set_legal(legal_eval)
                
                # Qualifications
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_qualifications,
                    extracted_info.get("accountant_exams", []),
                    business_name,
                    section_name="qualifications"
                )
                self.builder.set_qualifications({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
                
                # Data integrity
                compliant, explanation, alerts = self._safe_evaluate(
                    evaluate_data_integrity,
                    business_info,
                    section_name="data_integrity"
                )
                self.builder.set_data_integrity({
                    "compliance": compliant,
                    "explanation": explanation,
                    "alerts": [alert.to_dict() for alert in alerts],
                    "timestamp": datetime.now().isoformat()
                })
            
            # Compute final evaluation
            try:
                report = self.builder.build()
                logger.debug("Report built successfully", extra={
                    "business_name": business_name,
                    "report_sections": list(report.keys())
                })
            except Exception as e:
                logger.error("Failed to build report", extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "business_name": business_name
                }, exc_info=True)
                raise EvaluationProcessError(f"Failed to build report: {str(e)}")
                
            all_alerts: List[Alert] = []
            overall_compliance = search_evaluation.get("compliance", False)
            
            # Collect alerts and check compliance with error handling
            for section in ["registration_status", "regulatory_oversight", "disclosures",
                          "financials", "legal", "qualifications", "data_integrity"]:
                try:
                    section_data = report[section]
                    overall_compliance = overall_compliance and section_data.get("compliance", True)
                    
                    section_alerts = section_data.get("alerts", [])
                    for alert_dict in section_alerts:
                        try:
                            alert = Alert(
                                alert_type=alert_dict["alert_type"],
                                severity=AlertSeverity[alert_dict["severity"]],
                                metadata=alert_dict["metadata"],
                                description=alert_dict["description"],
                                alert_category=alert_dict.get("alert_category")
                            )
                            if alert.severity != AlertSeverity.INFO:
                                all_alerts.append(alert)
                        except (KeyError, ValueError) as e:
                            logger.error(f"Invalid alert data in {section}: {str(e)}")
                except KeyError as e:
                    logger.error(f"Missing section in report: {section}")
                    continue
            
            # Determine risk level and create final evaluation
            try:
                risk_level = self._determine_risk_level(all_alerts)
            except (TypeError, ValueError) as e:
                logger.error(f"Error determining risk level: {str(e)}")
                risk_level = "High"  # Default to high risk on error
            
            if skip_reasons:
                compliance_explanation = f"Evaluation skipped: {', '.join(skip_reasons)}"
                recommendations = "Review skip reasons and resubmit if necessary"
            elif search_failed:
                compliance_explanation = "Business not found in search"
                recommendations = "Verify business information and resubmit"
            elif overall_compliance:
                compliance_explanation = "All compliance checks passed"
                recommendations = "No immediate action required"
            else:
                compliance_explanation = "One or more compliance checks failed"
                recommendations = "Review alerts and take corrective action"
            
            final_eval = {
                "overall_compliance": overall_compliance,
                "compliance_explanation": compliance_explanation,
                "overall_risk_level": risk_level,
                "recommendations": recommendations,
                "alerts": [alert.to_dict() for alert in all_alerts],
                "evaluation_timestamp": datetime.now().isoformat(),
                "total_alerts": len(all_alerts),
                "alert_summary": {
                    "high": len([a for a in all_alerts if a.severity == AlertSeverity.HIGH]),
                    "medium": len([a for a in all_alerts if a.severity == AlertSeverity.MEDIUM]),
                    "low": len([a for a in all_alerts if a.severity == AlertSeverity.LOW])
                }
            }
            
            try:
                self.builder.set_final_evaluation(final_eval)
            except Exception as e:
                raise EvaluationProcessError(f"Failed to set final evaluation: {str(e)}")
            
            total_duration = time.time() - self.evaluation_start_time
            
            logger.info("Evaluation completed", extra={
                "business_name": business_name,
                "total_duration_seconds": total_duration,
                "section_timings": self.section_timings,
                "total_alerts": len(all_alerts),
                "risk_level": risk_level,
                "overall_compliance": overall_compliance,
                "alert_summary": {
                    "high": len([a for a in all_alerts if a.severity == AlertSeverity.HIGH]),
                    "medium": len([a for a in all_alerts if a.severity == AlertSeverity.MEDIUM]),
                    "low": len([a for a in all_alerts if a.severity == AlertSeverity.LOW])
                },
                "timestamp": datetime.now().isoformat()
            })
            
            return report
            
        except InvalidDataError as e:
            logger.error("Invalid input data", extra={
                "error": str(e),
                "error_type": "InvalidDataError",
                "business_name": claim.get('business_name', 'Unknown'),
                "duration_seconds": time.time() - self.evaluation_start_time
            }, exc_info=True)
            raise
        except EvaluationProcessError as e:
            logger.error("Evaluation process error", extra={
                "error": str(e),
                "error_type": "EvaluationProcessError",
                "business_name": claim.get('business_name', 'Unknown'),
                "duration_seconds": time.time() - self.evaluation_start_time
            }, exc_info=True)
            raise
        except Exception as e:
            logger.error("Unexpected error", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "business_name": claim.get('business_name', 'Unknown'),
                "duration_seconds": time.time() - self.evaluation_start_time
            }, exc_info=True)
            raise EvaluationProcessError(f"Unexpected error: {str(e)}")

# TODO: Implement firm evaluation report director logic