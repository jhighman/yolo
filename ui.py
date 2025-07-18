"""
==============================================
📌 FIRM COMPLIANCE API UI OVERVIEW
==============================================
🗂 PURPOSE
This script provides a Gradio-based UI for interacting with the Firm Compliance Claim Processing API.
It allows users to submit business compliance claims, manage cache, and view compliance reports through a web interface,
with formatted HTML rendering of claim processing reports and an optional raw JSON view.

🔧 USAGE
Run with `python ui.py` after starting the FastAPI server (`python api.py`).
Access the UI in your browser at the provided URL (e.g., http://localhost:7860).

📝 NOTES
- Assumes the FastAPI server is running at http://localhost:8000.
- Uses `requests` for API calls and renders claim reports as HTML or pretty-printed JSON.
- Validates that at least one of organization_crd or business_name is provided alongside mandatory fields.
"""

import gradio as gr
import requests
import json
from typing import Dict, Any, Tuple, Optional, Union
import logging

# Setup basic logging (no logger_config assumed)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("ui")

# API base URL (adjust if your FastAPI server runs on a different host/port)
API_BASE_URL = "http://localhost:9000"  # Changed from 8000 to 9000

def api_call(method: str, endpoint: str, data: Optional[Union[Dict[str, Any], Dict[str, Union[int, str]]]] = None) -> str:
    """
    Make an API call and return the response as a string.

    Args:
        method (str): HTTP method ("get", "post").
        endpoint (str): API endpoint path (e.g., "/process-claim-basic").
        data (Optional[Union[Dict[str, Any], Dict[str, Union[int, str]]]], optional): Data for request (query params or JSON body).

    Returns:
        str: JSON response string in standard API format: {"status": str, "message": str, "data": Any}
    """
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "get":
            response = requests.get(url, params=data)
        elif method == "post":
            response = requests.post(url, json=data)
        else:
            return json.dumps({
                "status": "error",
                "message": "Invalid request method",
                "data": {
                    "error_type": "InvalidMethod",
                    "details": f"Method '{method}' is not supported. Use 'get' or 'post'.",
                    "endpoint": endpoint
                }
            })
        
        # Try to parse response as JSON first
        try:
            response.raise_for_status()
            if not response.text.strip():
                return json.dumps({
                    "status": "error",
                    "message": "Server returned an empty response",
                    "data": {
                        "error_type": "EmptyResponse",
                        "details": "The server response was empty or contained only whitespace",
                        "endpoint": endpoint,
                        "http_status": response.status_code
                    }
                })
            
            # Try to parse as JSON to ensure it's valid
            response_data = json.loads(response.text)
            # If it's already in our format, return as is
            if isinstance(response_data, dict) and all(k in response_data for k in ["status", "message"]):
                return response.text
            # Otherwise, wrap it in our format
            return json.dumps({
                "status": "success",
                "message": "Request completed successfully",
                "data": response_data
            })
            
        except json.JSONDecodeError:
            return json.dumps({
                "status": "error",
                "message": "Server returned invalid JSON",
                "data": {
                    "error_type": "InvalidJSON",
                    "details": "The server response could not be parsed as JSON",
                    "raw_response": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                    "endpoint": endpoint,
                    "http_status": response.status_code
                }
            })
            
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": "Could not connect to the server",
            "data": {
                "error_type": "ConnectionError",
                "details": str(e),
                "endpoint": endpoint,
                "server_url": API_BASE_URL
            }
        })
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Server returned HTTP {e.response.status_code}",
            "data": {
                "error_type": "HTTPError",
                "details": str(e),
                "endpoint": endpoint,
                "http_status": e.response.status_code,
                "response_text": e.response.text[:200] + "..." if len(e.response.text) > 200 else e.response.text
            }
        })
    except requests.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": "Request failed",
            "data": {
                "error_type": type(e).__name__,
                "details": str(e),
                "endpoint": endpoint
            }
        })
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": "An unexpected error occurred",
            "data": {
                "error_type": type(e).__name__,
                "details": str(e),
                "endpoint": endpoint
            }
        })

def render_claim_report(report_json: str) -> Tuple[str, str]:
    """
    Render a claim processing report as formatted HTML and return both HTML and pretty-printed JSON.

    Args:
        report_json (str): JSON string of the report from the API.

    Returns:
        Tuple[str, str]: (HTML string for display, pretty-printed JSON string)
    """
    try:
        report = json.loads(report_json)
        
        # Check if this is an error response
        if isinstance(report, dict) and report.get("status") == "error":
            error_html = f"""<div style='color: red; padding: 10px; border: 1px solid red; margin: 10px;'>
                <h3>Error</h3>
                <p><strong>Message:</strong> {report.get('message', 'Unknown error')}</p>
                <p><strong>Type:</strong> {report.get('error_type', 'Unknown')}</p>
                {f"<p><strong>Endpoint:</strong> {report.get('endpoint')}</p>" if report.get('endpoint') else ""}
                </div>"""
            return error_html, json.dumps(report, indent=2)
            
        json_output = json.dumps(report, indent=2)
    except json.JSONDecodeError:
        error_msg = f"<div style='color: red;'>Invalid report format: {report_json}</div>"
        return error_msg, report_json

    html = "<div style='font-family: Arial, sans-serif;'>"
    
    # Header
    html += f"<h2>Compliance Report (Reference ID: {report.get('reference_id', 'N/A')})</h2>"

    # Claim Section
    claim = report.get("claim", {})
    html += "<h3>Business Details</h3><ul>"
    html += f"<li><strong>Business Ref:</strong> {claim.get('business_ref', 'N/A')}</li>"
    html += f"<li><strong>Business Name:</strong> {claim.get('business_name', 'N/A')}</li>"
    html += f"<li><strong>Tax ID:</strong> {claim.get('tax_id', 'N/A')}</li>"
    html += f"<li><strong>Organization CRD:</strong> {claim.get('organization_crd', 'N/A')}</li>"
    html += "</ul>"

    # Final Evaluation Section
    final_eval = report.get("final_evaluation", {})
    html += "<h3>Final Evaluation</h3><ul>"
    html += f"<li><strong>Overall Compliance:</strong> <span style='color: {'green' if final_eval.get('overall_compliance', False) else 'red'}'>{final_eval.get('overall_compliance', 'N/A')}</span></li>"
    html += f"<li><strong>Risk Level:</strong> {final_eval.get('overall_risk_level', 'N/A')}</li>"
    html += f"<li><strong>Explanation:</strong> {final_eval.get('compliance_explanation', 'N/A')}</li>"
    alerts = final_eval.get("alerts", [])
    if alerts:
        html += "<li><strong>Alerts:</strong><ul>"
        for alert in alerts:
            html += f"<li>{alert.get('description', 'Unnamed alert')} (Severity: {alert.get('severity', 'N/A')})</li>"
        html += "</ul></li>"
    html += "</ul>"

    # Evaluation Sections
    sections = [
        ("Search Evaluation", "search_evaluation"),
        ("Registration Status", "registration_status"),
        ("Regulatory Oversight", "regulatory_oversight"),
        ("Disclosures", "disclosures"),
        ("Financials", "financials"),
        ("Legal", "legal"),
        ("Qualifications", "qualifications"),
        ("Data Integrity", "data_integrity")
    ]
    for title, key in sections:
        section = report.get(key, {})
        html += f"<h4>{title}</h4><ul>"
        html += f"<li><strong>Compliance:</strong> <span style='color: {'green' if section.get('compliance', False) else 'red'}'>{section.get('compliance', 'N/A')}</span></li>"
        html += f"<li><strong>Explanation:</strong> {section.get('compliance_explanation', 'N/A')}</li>"
        section_alerts = section.get("alerts", [])
        if section_alerts:
            html += "<li><strong>Alerts:</strong><ul>"
            for alert in section_alerts:
                html += f"<li>{alert.get('description', 'Unnamed alert')} (Severity: {alert.get('severity', 'N/A')})</li>"
            html += "</ul></li>"
        html += "</ul>"

    html += "</div>"
    return html, json_output

# Claim Processing Functions
def process_claim(reference_id: str, business_ref: str, business_name: str, tax_id: str, 
                  organization_crd: str, webhook_url: str) -> Tuple[str, str]:
    """
    Submit a claim to the API in basic mode and return rendered report and raw JSON.

    Args:
        reference_id (str): Mandatory reference ID.
        business_ref (str): Mandatory business reference.
        business_name (str): Optional business name (at least one identifier required).
        tax_id (str): Optional tax ID (at least one identifier required).
        organization_crd (str): Optional organization CRD (at least one identifier required).
        webhook_url (str): Optional webhook URL.

    Returns:
        Tuple[str, str]: (Rendered HTML report or validation error, pretty-printed JSON)
    """
    # Validate mandatory administrative fields
    missing_admin_fields = []
    if not reference_id or not reference_id.strip():
        missing_admin_fields.append("Reference ID")
    if not business_ref or not business_ref.strip():
        missing_admin_fields.append("Business Ref")

    if missing_admin_fields:
        error_response = {
            "status": "error",
            "message": "Required administrative fields are missing",
            "data": {
                "error_type": "ValidationError",
                "missing_fields": missing_admin_fields,
                "details": f"The following required administrative fields are missing or empty: {', '.join(missing_admin_fields)}",
                "field_requirements": {
                    "reference_id": "Required: Unique identifier for this claim",
                    "business_ref": "Required: Business reference identifier"
                }
            }
        }
        return render_claim_report(json.dumps(error_response))

    # Validate that at least one identifier is provided
    identifiers = {
        "Business Name": business_name.strip() if business_name else "",
        "Tax ID": tax_id.strip() if tax_id else "",
        "Organization CRD": organization_crd.strip() if organization_crd else ""
    }

    if not any(identifiers.values()):
        error_response = {
            "status": "error",
            "message": "No business identifier provided",
            "data": {
                "error_type": "ValidationError",
                "details": "At least one business identifier must be provided",
                "field_requirements": {
                    "business_name": "Optional: Legal name of the business (at least one identifier required)",
                    "tax_id": "Optional: Tax identification number (at least one identifier required)",
                    "organization_crd": "Optional: CRD number (at least one identifier required)"
                },
                "provided_identifiers": identifiers
            }
        }
        return render_claim_report(json.dumps(error_response))

    # Prepare data for API call, only including non-empty values
    data = {
        "reference_id": reference_id.strip(),
        "business_ref": business_ref.strip()
    }

    # Add optional fields only if they have values
    if business_name and business_name.strip():
        data["business_name"] = business_name.strip()
    if tax_id and tax_id.strip():
        data["tax_id"] = tax_id.strip()
    if organization_crd and organization_crd.strip():
        data["organization_crd"] = organization_crd.strip()
    if webhook_url and webhook_url.strip():
        data["webhook_url"] = webhook_url.strip()
    
    endpoint = "/process-claim-basic"  # Only basic mode is supported
    raw_response = api_call("post", endpoint, data)
    return render_claim_report(raw_response)

# Cache Management Functions
def clear_cache(business_ref: str) -> str:
    if not business_ref:
        return "Error: Business Ref is required"
    return api_call("post", f"/cache/clear/{business_ref}")

def clear_all_cache() -> str:
    return api_call("post", "/cache/clear-all")

def clear_agent_cache(business_ref: str, agent_name: str) -> str:
    if not business_ref or not agent_name:
        return "Error: Business Ref and Agent Name are required"
    return api_call("post", f"/cache/clear-agent/{business_ref}/{agent_name}")

def list_cache(business_ref: str, page: int, page_size: int) -> str:
    """
    List cache contents with pagination.

    Args:
        business_ref (str): Optional business reference for filtering.
        page (int): Page number.
        page_size (int): Items per page.

    Returns:
        str: JSON response from the API.
    """
    params: Dict[str, Union[int, str]] = {
        "page": page,
        "page_size": page_size
    }
    if business_ref:
        params["business_ref"] = business_ref
    return api_call("get", "/cache/list", params)

def cleanup_stale_cache() -> str:
    return api_call("post", "/cache/cleanup-stale")

# Compliance Report Retrieval Functions
def get_latest_compliance(business_ref: str) -> str:
    if not business_ref:
        return "Error: Business Ref is required"
    return api_call("get", f"/compliance/latest/{business_ref}")

def get_compliance_by_ref(business_ref: str, reference_id: str) -> str:
    if not business_ref or not reference_id:
        return "Error: Business Ref and Reference ID are required"
    return api_call("get", f"/compliance/by-ref/{business_ref}/{reference_id}")

def list_compliance_reports(business_ref: str, page: int, page_size: int) -> str:
    """
    List compliance reports with pagination.

    Args:
        business_ref (str): Optional business reference for filtering.
        page (int): Page number.
        page_size (int): Items per page.

    Returns:
        str: JSON response from the API.
    """
    params: Dict[str, Union[int, str]] = {
        "page": page,
        "page_size": page_size
    }
    if business_ref:
        params["business_ref"] = business_ref
    return api_call("get", "/compliance/list", params)

# Gradio UI Layout
demo = gr.Blocks(title="Firm Compliance API Interface")
with demo:
    gr.Markdown("# Firm Compliance Claim Processing & Cache Management UI")

    # Claim Processing Section
    with gr.Row():
        with gr.Column():
            gr.Markdown("""## Submit Business Compliance Claim
            
            **Required Fields:**
            - Reference ID
            - Business Ref
            
            **Identifiers (at least one required):**
            - Business Name
            - Tax ID
            - Organization CRD
            """)
            reference_id = gr.Textbox(label="Reference ID *", placeholder="e.g., B123")
            business_ref = gr.Textbox(label="Business Ref *", placeholder="e.g., BIZ123")
            business_name = gr.Textbox(label="Business Name", placeholder="e.g., Acme Corp")
            tax_id = gr.Textbox(label="Tax ID", placeholder="e.g., 12-3456789")
            organization_crd = gr.Textbox(label="Organization CRD", placeholder="e.g., 123456")
            webhook_url = gr.Textbox(label="Webhook URL (optional)", placeholder="e.g., https://your-webhook.com/endpoint")
            submit_btn = gr.Button("Submit Claim")

        with gr.Column():
            gr.Markdown("## Claim Processing Results")
            html_output = gr.HTML("Submit a claim to see results")
            json_output = gr.JSON(None)

    # Cache Management Section
    gr.Markdown("## Cache Management")
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Clear Cache")
            cache_business_ref = gr.Textbox(label="Business Ref", placeholder="e.g., BIZ123")
            cache_agent_name = gr.Textbox(label="Agent Name", placeholder="e.g., SEC_Agent")
            clear_cache_btn = gr.Button("Clear Cache")
            clear_agent_cache_btn = gr.Button("Clear Agent Cache")
            clear_all_cache_btn = gr.Button("Clear All Cache")
            cleanup_stale_btn = gr.Button("Cleanup Stale Cache")

        with gr.Column():
            gr.Markdown("### List Cache")
            list_cache_business_ref = gr.Textbox(label="Business Ref (optional)", placeholder="e.g., BIZ123")
            list_cache_page = gr.Number(label="Page", value=1, minimum=1)
            list_cache_page_size = gr.Number(label="Page Size", value=10, minimum=1, maximum=100)
            list_cache_btn = gr.Button("List Cache")
            cache_output = gr.JSON(None)

    # Compliance Report Section
    gr.Markdown("## Compliance Reports")
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Retrieve Reports")
            report_business_ref = gr.Textbox(label="Business Ref", placeholder="e.g., BIZ123")
            report_reference_id = gr.Textbox(label="Reference ID", placeholder="e.g., B123")
            get_latest_btn = gr.Button("Get Latest Report")
            get_by_ref_btn = gr.Button("Get Report by Ref")

        with gr.Column():
            gr.Markdown("### List Reports")
            list_reports_business_ref = gr.Textbox(label="Business Ref (optional)", placeholder="e.g., BIZ123")
            list_reports_page = gr.Number(label="Page", value=1, minimum=1)
            list_reports_page_size = gr.Number(label="Page Size", value=10, minimum=1, maximum=100)
            list_reports_btn = gr.Button("List Reports")
            reports_output = gr.JSON(None)

    # Event handlers
    submit_btn.click(
        process_claim,
        inputs=[reference_id, business_ref, business_name, tax_id, organization_crd, webhook_url],
        outputs=[html_output, json_output]
    )

    clear_cache_btn.click(
        clear_cache,
        inputs=[cache_business_ref],
        outputs=cache_output
    )

    clear_agent_cache_btn.click(
        clear_agent_cache,
        inputs=[cache_business_ref, cache_agent_name],
        outputs=cache_output
    )

    clear_all_cache_btn.click(
        clear_all_cache,
        outputs=cache_output
    )

    cleanup_stale_btn.click(
        cleanup_stale_cache,
        outputs=cache_output
    )

    list_cache_btn.click(
        list_cache,
        inputs=[list_cache_business_ref, list_cache_page, list_cache_page_size],
        outputs=cache_output
    )

    get_latest_btn.click(
        get_latest_compliance,
        inputs=[report_business_ref],
        outputs=reports_output
    )

    get_by_ref_btn.click(
        get_compliance_by_ref,
        inputs=[report_business_ref, report_reference_id],
        outputs=reports_output
    )

    list_reports_btn.click(
        list_compliance_reports,
        inputs=[list_reports_business_ref, list_reports_page, list_reports_page_size],
        outputs=reports_output
    )

if __name__ == "__main__":
    demo.launch(
        share=True,  # Creates a public link accessible from anywhere
        server_port=9001  # Changed from default 7860 to 9001
    )