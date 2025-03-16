"""
Batch processing of business entity compliance claims from CSV files.
Processes rows, validates data, generates reports, and manages skipped/error records.
"""

import csv
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional, Sequence
from collections import defaultdict
from enum import Enum
from batch.firm_main_config import INPUT_FOLDER, OUTPUT_FOLDER, ARCHIVE_FOLDER, canonical_fields
from batch.firm_main_file_utils import save_checkpoint
from services.firm_business import process_claim
from services.firm_services import FirmServicesFacade

logger = logging.getLogger('firm_main_csv_processing')

class SkipScenario(Enum):
    NO_BUSINESS_REF = "Missing business reference"
    NO_BUSINESS_NAME = "Missing business name"
    NO_IDENTIFIERS = "Missing all identifiers (organization_crd, business_name)"

class CSVProcessor:
    def __init__(self):
        self.current_csv = None
        self.current_line = 0
        self.skipped_records = defaultdict(list)
        self.error_records = defaultdict(list)

    def generate_reference_id(self, tax_id: Optional[str] = None) -> str:
        """Generate a reference ID based on tax ID or a random default."""
        if tax_id and tax_id.strip():
            return f"TAX-{tax_id}"
        return f"DEF-{random.randint(100000000000, 999999999999)}"

    def resolve_headers(self, fieldnames: Optional[Sequence[str]]) -> Dict[str, str]:
        """Map CSV headers to canonical field names."""
        resolved_headers = {}
        if not fieldnames:
            logger.warning("No fieldnames provided")
            return resolved_headers

        logger.info(f"Raw fieldnames from CSV: {fieldnames}")
        for header in fieldnames:
            if not header.strip():
                logger.warning("Empty header name encountered")
                continue
            header_lower = header.lower().strip()
            logger.debug(f"Processing header: '{header}' (lowercase: '{header_lower}')")
            for canonical, variants in canonical_fields.items():
                variants_lower = [v.lower().strip() for v in variants]
                logger.debug(f"Checking against canonical '{canonical}' variants: {variants_lower}")
                if header_lower in variants_lower:
                    resolved_headers[header] = canonical
                    logger.debug(f"Mapped header '{header}' to '{canonical}'")
                    break
            else:
                logger.warning(f"Unmapped CSV column: '{header}' will be included as-is")
                resolved_headers[header] = header
        logger.debug(f"Resolved headers: {json.dumps(resolved_headers, indent=2)}")
        unmapped_canonicals = set(canonical_fields.keys()) - set(resolved_headers.values())
        if unmapped_canonicals:
            logger.debug(f"Canonical fields not found in CSV headers: {unmapped_canonicals}")
        return resolved_headers

    def validate_row(self, claim: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate a business claim row for required fields."""
        issues = []
        business_ref = claim.get('business_ref', '').strip()
        if not business_ref:
            issues.append(SkipScenario.NO_BUSINESS_REF.value)
        business_name = claim.get('business_name', '').strip()
        if not business_name:
            issues.append(SkipScenario.NO_BUSINESS_NAME.value)
        org_crd = claim.get('organization_crd', '').strip()
        if not (org_crd or business_name):
            issues.append(SkipScenario.NO_IDENTIFIERS.value)
        return (len(issues) == 0, issues)

    def process_csv(self, csv_file_path: str, start_line: int, facade: FirmServicesFacade, config: Dict[str, bool], wait_time: float):
        """Process a CSV file starting from the specified line."""
        self.current_csv = os.path.basename(csv_file_path)
        self.current_line = 0
        logger.info(f"Starting to process {csv_file_path} from line {start_line}")

        try:
            with open(csv_file_path, 'r', newline='') as f:
                reader = csv.DictReader(f)
                resolved_headers = self.resolve_headers(reader.fieldnames)
                logger.debug(f"Resolved headers (post-processing): {resolved_headers}")

                for i, row in enumerate(reader, start=2):
                    if i <= start_line:
                        logger.debug(f"Skipping line {i} (before start_line {start_line})")
                        continue
                    logger.info(f"Processing {self.current_csv}, line {i}, row: {dict(row)}")
                    self.current_line = i
                    try:
                        self.process_row(row, resolved_headers, facade, config, wait_time)
                    except Exception as e:
                        logger.error(f"Error processing {self.current_csv}, line {i}: {str(e)}", exc_info=True)
                        self.error_records[self.current_csv].append({"row_data": dict(row), "error": str(e)})
                    save_checkpoint(self.current_csv, self.current_line)
                    time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error reading {csv_file_path}: {str(e)}", exc_info=True)
            self.error_records[self.current_csv].append({"row_data": {}, "error": f"File read error: {str(e)}"})
        finally:
            self.write_error_records()
            self.write_skipped_records()

    def process_row(self, row: Dict[str, str], resolved_headers: Dict[str, str], facade: FirmServicesFacade, config: Dict[str, bool], wait_time: float):
        """Process a single CSV row and generate a compliance report."""
        reference_id_header = next((k for k, v in resolved_headers.items() if v == 'reference_id'), 'reference_id')
        reference_id = row.get(reference_id_header, '').strip() or self.generate_reference_id(row.get(resolved_headers.get('tax_id', 'tax_id'), ''))

        try:
            raw_row = {header: row.get(header, '').strip() for header in row}
            logger.info(f"Raw CSV row for reference_id='{reference_id}': {json.dumps(raw_row, indent=2)}")

            claim = {}
            for header, canonical in resolved_headers.items():
                value = raw_row.get(header, '')
                claim[canonical] = value
                logger.debug(f"Mapping field - canonical: '{canonical}', header: '{header}', value: '{value}'")

            business_ref_header = next((k for k, v in resolved_headers.items() if v == 'business_ref'), 'business_ref')
            business_ref = raw_row.get(business_ref_header, '').strip()
            claim['business_ref'] = business_ref
            logger.info(f"Business ref header: '{business_ref_header}', value: '{business_ref}'")

            is_valid, issues = self.validate_row(claim)
            logger.info(f"Validation for reference_id='{reference_id}': valid={is_valid}, issues={issues}")

            if not is_valid:
                for issue in issues:
                    logger.warning(f"Row skipped - {issue} for reference_id='{reference_id}'")
                    self.skipped_records[self.current_csv].append({"row_data": raw_row})
                report = {
                    "reference_id": reference_id,
                    "business_ref": business_ref,
                    "claim": claim,
                    "search_evaluation": {
                        "compliance": False,
                        "compliance_explanation": f"Insufficient data: {', '.join(issues)}"
                    },
                    "final_evaluation": {
                        "overall_compliance": False,
                        "compliance_explanation": "Skipped due to insufficient data",
                        "alerts": [{"description": issue} for issue in issues]
                    }
                }
                process_claim(
                    claim,
                    facade,
                    business_ref,
                    skip_financials=config.get('skip_financials', True),
                    skip_legal=config.get('skip_legal', True)
                )
                self._save_report(report, business_ref, reference_id)
            else:
                unmapped_fields = set(row.keys()) - set(resolved_headers.keys())
                if unmapped_fields:
                    logger.warning(f"Unmapped fields in row for reference_id='{reference_id}': {unmapped_fields}")
                
                logger.info(f"Canonical claim for reference_id='{reference_id}': {json.dumps(claim, indent=2)}")

                report = process_claim(
                    claim,
                    facade,
                    business_ref,
                    skip_financials=config.get('skip_financials', True),
                    skip_legal=config.get('skip_legal', True)
                )
                if report is None:
                    logger.error(f"process_claim returned None for reference_id='{reference_id}'")
                    report = {
                        "reference_id": reference_id,
                        "business_ref": business_ref,
                        "claim": claim,
                        "search_evaluation": {
                            "compliance": False,
                            "compliance_explanation": "Processing failed: process_claim returned None"
                        },
                        "final_evaluation": {
                            "overall_compliance": False,
                            "compliance_explanation": "Processing failed",
                            "alerts": [{"description": "process_claim returned None"}]
                        }
                    }
                    facade.save_compliance_report(report, business_ref)

                self._save_report(report, business_ref, reference_id)

        except Exception as e:
            logger.error(f"Unexpected error processing row for reference_id='{reference_id}': {str(e)}", exc_info=True)
            self.error_records[self.current_csv].append({"row_data": raw_row if 'raw_row' in locals() else dict(row), "error": str(e)})

    def _save_report(self, report: Dict[str, Any], business_ref: str, reference_id: str):
        """Save the compliance report to the output folder."""
        report_path = os.path.join(OUTPUT_FOLDER, f"{reference_id}.json")
        logger.info(f"Saving report to {report_path} (output folder)")
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            compliance = report.get('final_evaluation', {}).get('overall_compliance', False)
            logger.info(f"Processed {reference_id}, overall_compliance: {compliance}, saved to output/")
        except Exception as e:
            logger.error(f"Error saving report to {report_path}: {str(e)}", exc_info=True)

        logger.info(f"Report for reference_id='{reference_id}' also saved to cache/{business_ref}/ by process_claim")

    def _write_records(self, records: defaultdict, output_file: str, record_type: str):
        """Write skipped or error records to a CSV file in the archive folder."""
        date_str = datetime.now().strftime("%m-%d-%Y")
        archive_subfolder = os.path.join(ARCHIVE_FOLDER, date_str)
        csv_path = os.path.join(archive_subfolder, output_file)
        try:
            os.makedirs(archive_subfolder, exist_ok=True)
            with open(csv_path, 'a', newline='') as f:
                file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
                
                total_records = 0
                for csv_file, record_list in records.items():
                    for record in record_list:
                        row_data = record['row_data']
                        if not file_exists:
                            fieldnames = list(row_data.keys())
                            if "error" in record:
                                fieldnames.append("error")
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            file_exists = True
                        else:
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writerow({**row_data, **({"error": record["error"]} if "error" in record else {})})
                        total_records += 1
                
                logger.info(f"Appended {total_records} {record_type} records to {csv_path}")
        except Exception as e:
            logger.error(f"Error writing {record_type} records to {csv_path}: {str(e)}", exc_info=True)
        finally:
            records.clear()

    def write_skipped_records(self):
        """Write skipped records to archive/skipped.csv."""
        self._write_records(self.skipped_records, "skipped.csv", "skipped")

    def write_error_records(self):
        """Write error records to archive/errors.csv."""
        self._write_records(self.error_records, "errors.csv", "error")

if __name__ == "__main__":
    facade = FirmServicesFacade()
    config = {"skip_financials": True, "skip_legal": True}
    processor = CSVProcessor()
    processor.process_csv(
        os.path.join(INPUT_FOLDER, "sample.csv"),
        start_line=0,
        facade=facade,
        config=config,
        wait_time=0.1
    )