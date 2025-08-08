#!/usr/bin/env python3
"""
Compliance Summary Generator

This script finds all compliance reports in the cache directory, parses them,
and generates a summary report with CRD, name, compliance status, and alert counts.
It also generates a structured PDF report with detailed information about non-compliant reports.
"""

import os
import json
import glob
import pandas as pd
from typing import Dict, List, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def find_compliance_reports(cache_dir: str = "cache") -> List[str]:
    """
    Find all compliance reports in the cache directory.
    
    Args:
        cache_dir: The cache directory to search in (default: "cache")
        
    Returns:
        A list of file paths to compliance reports
    """
    # Get all subdirectories in the cache directory
    if not os.path.exists(cache_dir):
        print(f"Cache directory '{cache_dir}' not found.")
        return []
    
    subdirs = [os.path.join(cache_dir, d) for d in os.listdir(cache_dir) 
               if os.path.isdir(os.path.join(cache_dir, d))]
    
    # Look for FirmComplianceReport files in each subdirectory
    report_files = []
    for subdir in subdirs:
        pattern = os.path.join(subdir, "FirmComplianceReport_*.json")
        files = glob.glob(pattern)
        report_files.extend(files)
    
    return report_files

def extract_crd_from_path(file_path: str) -> Optional[str]:
    """
    Extract CRD number from the file path if possible.
    
    Args:
        file_path: Path to the compliance report file
        
    Returns:
        CRD number if found, None otherwise
    """
    # Extract from directory name (BIZ_XXXX or EN-XXXXX)
    dir_name = os.path.basename(os.path.dirname(file_path))
    if dir_name.startswith("BIZ_"):
        return dir_name[4:]  # Remove "BIZ_" prefix
    elif dir_name.startswith("EN-"):
        return dir_name[3:]  # Remove "EN-" prefix
    
    # Extract from filename (FirmComplianceReport_XXXX_v1_...)
    file_name = os.path.basename(file_path)
    if file_name.startswith("FirmComplianceReport_"):
        parts = file_name.split("_")
        if len(parts) > 1:
            ref_id = parts[1]
            if ref_id.startswith("test-ref-"):
                return ref_id[9:]  # Remove "test-ref-" prefix
            elif ref_id.startswith("EN-"):
                return ref_id[3:]  # Remove "EN-" prefix
            return ref_id
    
    return None

def extract_detailed_alerts(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract detailed alert information from a compliance report.
    
    Args:
        data: The compliance report data
        
    Returns:
        A list of dictionaries containing detailed alert information
    """
    alerts = []
    
    if 'final_evaluation' in data and 'alerts' in data['final_evaluation']:
        for alert in data['final_evaluation']['alerts']:
            alert_info = {
                'severity': alert.get('severity', 'UNKNOWN'),
                'category': alert.get('alert_category', 'UNKNOWN'),
                'type': alert.get('alert_type', 'UNKNOWN'),
                'description': alert.get('description', 'No description provided'),
                'source': alert.get('source', 'UNKNOWN'),
                'event_date': alert.get('eventDate', 'UNKNOWN')
            }
            alerts.append(alert_info)
    
    return alerts

def parse_compliance_report(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Parse a compliance report file and extract the required information.
    
    Args:
        file_path: Path to the compliance report file
        
    Returns:
        A dictionary containing the extracted information or None if parsing fails
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract CRD
        crd = None
        
        # Try to get from entity.crd_number
        if 'entity' in data and 'crd_number' in data['entity']:
            crd = data['entity']['crd_number']
        
        # Try to get from claim.crdNumber
        if not crd and 'claim' in data and 'crdNumber' in data['claim']:
            crd = data['claim']['crdNumber']
        
        # Try to get from claim.organization_crd
        if not crd and 'claim' in data and 'organization_crd' in data['claim']:
            crd = data['claim']['organization_crd']
            
        # If still not found, try to extract from file path
        if not crd:
            crd = extract_crd_from_path(file_path)
            
        # Extract name
        name = None
        
        # Try to get from entity.firm_name
        if 'entity' in data and 'firm_name' in data['entity']:
            name = data['entity']['firm_name']
        
        # Try to get from claim.entityName
        if not name and 'claim' in data and 'entityName' in data['claim']:
            name = data['claim']['entityName']
            
        # Try to get from claim.business_name
        if not name and 'claim' in data and 'business_name' in data['claim']:
            name = data['claim']['business_name']
            
        # Extract compliance flag
        compliance_flag = data.get('final_evaluation', {}).get('overall_compliance', False)
        
        # Count alerts
        alerts = data.get('final_evaluation', {}).get('alerts', [])
        alert_count = len(alerts)
        
        # Get reference ID
        reference_id = data.get('reference_id', '')
        
        # Extract detailed alerts if non-compliant
        detailed_alerts = []
        if not compliance_flag:
            detailed_alerts = extract_detailed_alerts(data)
        
        return {
            'crd': crd,
            'name': name,
            'reference_id': reference_id,
            'compliance_flag': compliance_flag,
            'alert_count': alert_count,
            'file_path': file_path,
            'detailed_alerts': detailed_alerts
        }
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
        return None

def generate_summary_report(reports_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Generate a summary report from the parsed compliance reports.
    
    Args:
        reports_data: List of dictionaries containing parsed report data
        
    Returns:
        A pandas DataFrame containing the summary report
    """
    # Create DataFrame
    df = pd.DataFrame(reports_data)
    
    # Sort by CRD
    if 'crd' in df.columns:
        df = df.sort_values('crd')
    
    return df

def save_report_to_csv(df: pd.DataFrame, output_path: str = "compliance_summary_report.csv") -> str:
    """
    Save the summary report to a CSV file.
    
    Args:
        df: DataFrame containing the summary report
        output_path: Path to save the CSV file
        
    Returns:
        The path to the saved CSV file
    """
    # Drop the detailed_alerts column for CSV export
    if 'detailed_alerts' in df.columns:
        df_export = df.drop(columns=['detailed_alerts'])
    else:
        df_export = df
        
    df_export.to_csv(output_path, index=False)
    return output_path

def save_report_to_json(df: pd.DataFrame, output_path: str = "compliance_summary_report.json") -> str:
    """
    Save the summary report to a JSON file.
    
    Args:
        df: DataFrame containing the summary report
        output_path: Path to save the JSON file
        
    Returns:
        The path to the saved JSON file
    """
    # Convert DataFrame to list of dictionaries
    records = df.to_dict(orient='records')
    
    # Save to JSON file
    with open(output_path, 'w') as f:
        json.dump(records, f, indent=2)
    
    return output_path

def generate_pdf_report(df: pd.DataFrame, output_path: str = "compliance_detailed_report.pdf") -> str:
    """
    Generate a structured PDF report with summary statistics and detailed non-compliance information.
    
    Args:
        df: DataFrame containing the summary report
        output_path: Path to save the PDF file
        
    Returns:
        The path to the saved PDF file
    """
    # Create a PDF document
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Create a custom style for alert descriptions
    alert_style = ParagraphStyle(
        'AlertStyle',
        parent=styles['Normal'],
        leftIndent=20,
        spaceAfter=6
    )
    
    # Add title
    elements.append(Paragraph("Compliance Summary Report", title_style))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add summary statistics
    elements.append(Paragraph("Summary Statistics", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    total_reports = len(df)
    compliant_reports = df['compliance_flag'].sum() if 'compliance_flag' in df.columns else 0
    non_compliant_reports = total_reports - compliant_reports
    total_alerts = df['alert_count'].sum() if 'alert_count' in df.columns else 0
    
    summary_data = [
        ["Total Reports:", str(total_reports)],
        ["Compliant Reports:", str(compliant_reports)],
        ["Non-Compliant Reports:", str(non_compliant_reports)],
        ["Total Alerts:", str(total_alerts)],
        ["Average Alerts per Report:", f"{total_alerts / total_reports:.2f}" if total_reports > 0 else "0.00"]
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.25*inch))
    
    # Add non-compliant reports section
    elements.append(Paragraph("Non-Compliant Reports", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Filter non-compliant reports
    non_compliant_df = df[~df['compliance_flag']]
    
    if len(non_compliant_df) == 0:
        elements.append(Paragraph("No non-compliant reports found.", normal_style))
    else:
        # Sort by alert count (descending) and then by CRD
        non_compliant_df = non_compliant_df.sort_values(['alert_count', 'crd'], ascending=[False, True])
        
        # Add each non-compliant report with its alerts
        for idx, row in non_compliant_df.iterrows():
            report_title = f"CRD: {row['crd']} - {row['name']} ({row['alert_count']} alerts)"
            elements.append(Paragraph(report_title, styles['Heading3']))
            elements.append(Spacer(1, 0.05*inch))
            
            # Add reference ID and file path
            elements.append(Paragraph(f"Reference ID: {row['reference_id']}", normal_style))
            elements.append(Paragraph(f"File: {row['file_path']}", normal_style))
            elements.append(Spacer(1, 0.05*inch))
            
            # Add alerts table
            if 'detailed_alerts' in row and row['detailed_alerts']:
                elements.append(Paragraph("Alerts:", normal_style))
                
                alert_data = [["Severity", "Category", "Type", "Description"]]
                for alert in row['detailed_alerts']:
                    alert_data.append([
                        alert.get('severity', 'UNKNOWN'),
                        alert.get('category', 'UNKNOWN'),
                        alert.get('type', 'UNKNOWN'),
                        alert.get('description', 'No description provided')
                    ])
                
                alert_table = Table(alert_data, colWidths=[0.75*inch, 1*inch, 1.25*inch, 3.5*inch])
                alert_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                
                elements.append(alert_table)
            else:
                elements.append(Paragraph("No detailed alert information available.", normal_style))
            
            elements.append(Spacer(1, 0.2*inch))
    
    # Build the PDF
    doc.build(elements)
    
    return output_path

def print_summary_stats(df: pd.DataFrame) -> None:
    """
    Print summary statistics about the compliance reports.
    
    Args:
        df: DataFrame containing the summary report
    """
    total_reports = len(df)
    compliant_reports = df['compliance_flag'].sum() if 'compliance_flag' in df.columns else 0
    non_compliant_reports = total_reports - compliant_reports
    total_alerts = df['alert_count'].sum() if 'alert_count' in df.columns else 0
    
    print(f"\nSummary Statistics:")
    print(f"Total Reports: {total_reports}")
    print(f"Compliant Reports: {compliant_reports}")
    print(f"Non-Compliant Reports: {non_compliant_reports}")
    print(f"Total Alerts: {total_alerts}")
    
    if total_reports > 0:
        print(f"Average Alerts per Report: {total_alerts / total_reports:.2f}")

def main():
    """Main function to run the compliance summary generator."""
    print("Compliance Summary Generator")
    print("===========================")
    
    # Find all compliance reports
    print("Finding compliance reports in cache directory...")
    report_files = find_compliance_reports()
    print(f"Found {len(report_files)} compliance report files.")
    
    # Parse compliance reports
    print("Parsing compliance reports...")
    reports_data = []
    for file_path in report_files:
        report_data = parse_compliance_report(file_path)
        if report_data:
            reports_data.append(report_data)
    
    print(f"Successfully parsed {len(reports_data)} compliance reports.")
    
    # Generate summary report
    print("Generating summary report...")
    df = generate_summary_report(reports_data)
    
    # Print summary statistics
    print_summary_stats(df)
    
    # Save reports
    csv_path = save_report_to_csv(df)
    json_path = save_report_to_json(df)
    
    # Generate PDF report
    print("Generating detailed PDF report...")
    pdf_path = generate_pdf_report(df)
    
    print(f"\nSummary report saved to:")
    print(f"- CSV: {csv_path}")
    print(f"- JSON: {json_path}")
    print(f"- PDF: {pdf_path}")
    
    # Display the report
    print("\nCompliance Summary Report:")
    if len(df) > 50:
        print(df.head(50).to_string(index=False))
        print(f"\n... and {len(df) - 50} more rows")
    else:
        print(df.to_string(index=False))

if __name__ == "__main__":
    main()