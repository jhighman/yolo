# YOLO Financial Regulatory Compliance System - Development Guide

## Overview

This guide will help you get started with development and testing of the YOLO Financial Regulatory Compliance System. The system processes firm compliance claims by retrieving and analyzing data from FINRA and SEC sources, generating compliance reports, and managing cached data.

## System Architecture

The system consists of several key components:

1. **Services Layer**
   - `FirmServicesFacade`: Core interface for accessing FINRA and SEC data
   - `FirmMarshaller`: Normalizes data from different sources
   - `FirmBusiness`: Implements search strategies and claim processing

2. **Agents Layer**
   - `FINRA_FirmBrokerCheck_Agent`: Retrieves data from FINRA BrokerCheck
   - `SEC_FirmIAPD_Agent`: Retrieves data from SEC IAPD
   - `FirmComplianceReport_Agent`: Generates compliance reports

3. **Evaluation Layer**
   - `FirmEvaluationProcessor`: Evaluates compliance across various dimensions
   - `FirmEvaluationReportBuilder`: Builds structured compliance reports
   - `FirmEvaluationReportDirector`: Orchestrates the report generation process

4. **Cache Management**
   - `CacheManager`: Handles caching of API responses and reports
   - `FirmComplianceHandler`: Manages compliance report storage and retrieval

5. **User Interfaces**
   - `API`: FastAPI-based REST API for programmatic access
   - `UI`: Gradio-based web interface for human interaction
   - `CLI`: Command-line tools for various operations

## Setup Development Environment

1. **Clone the repository**

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create necessary directories**
   The system uses several directories for data storage:
   - `input/`: For input files (including batch.csv)
   - `output/`: For generated reports
   - `cache/`: For cached data
   - `logs/`: For log files

## Running the System

### API Server

The API provides endpoints for processing claims and managing cache:

```bash
# Start the API server
uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info
```

Key endpoints:
- `/process-claim-basic`: Process a compliance claim
- `/cache/clear/{business_ref}`: Clear cache for a business
- `/compliance/latest/{business_ref}`: Get latest compliance report

### Web UI

The UI provides a user-friendly interface for interacting with the API:

```bash
# Start the UI (after starting the API server)
python ui.py
```

Access the UI in your browser at http://localhost:7860

### Command-Line Tools

Several CLI tools are available for different operations:

```bash
# Firm Services CLI - Search and retrieve firm information
python services/firm_services.py --subject-id <id> search "Firm Name"
python services/firm_services.py --subject-id <id> details "123456"

# Firm Business CLI - Test search strategy determination
python services/firm_business.py --interactive

# Cache Manager CLI - Manage cache and reports
python cache_manager/cli.py --list-cache
```

## Development Tasks

### 1. Implement Batch CSV Processing

The system currently lacks batch processing functionality. You need to implement a way to process multiple firms from a CSV file.

#### Implementation Plan:

1. **Create a batch processor module**
   - Create a new file `batch_processor.py` in the project root
   - Implement CSV parsing and validation
   - Add functionality to process each row through the existing claim processing pipeline

2. **Sample implementation structure:**
   ```python
   import csv
   from typing import List, Dict, Any
   from services.firm_business import process_claim
   from services.firm_services import FirmServicesFacade

   def process_batch_csv(csv_path: str, subject_id: str, skip_financials: bool = False, skip_legal: bool = False) -> List[Dict[str, Any]]:
       """Process multiple firms from a CSV file.
       
       Args:
           csv_path: Path to the CSV file
           subject_id: Subject ID for the request
           skip_financials: Flag to skip financial evaluation
           skip_legal: Flag to skip legal evaluation
           
       Returns:
           List of processing results
       """
       results = []
       facade = FirmServicesFacade()
       
       with open(csv_path, 'r') as f:
           reader = csv.DictReader(f)
           for row in reader:
               # Validate required fields
               if not all(k in row for k in ['reference_id', 'business_ref', 'business_name', 'tax_id']):
                   results.append({
                       'status': 'error',
                       'message': f'Missing required fields for row: {row}',
                       'row': row
                   })
                   continue
               
               try:
                   # Process the claim
                   report = process_claim(
                       claim=row,
                       facade=facade,
                       business_ref=row['business_ref'],
                       skip_financials=skip_financials,
                       skip_legal=skip_legal
                   )
                   
                   results.append({
                       'status': 'success',
                       'reference_id': row['reference_id'],
                       'business_ref': row['business_ref'],
                       'report': report
                   })
               except Exception as e:
                   results.append({
                       'status': 'error',
                       'message': str(e),
                       'reference_id': row.get('reference_id', 'unknown'),
                       'business_ref': row.get('business_ref', 'unknown'),
                       'row': row
                   })
       
       return results
   ```

3. **Add CLI interface for batch processing**
   ```python
   # In batch_processor.py
   
   def main():
       """Command-line interface for batch processing."""
       parser = argparse.ArgumentParser(
           description="Batch Processor - Process multiple firms from a CSV file"
       )
       
       parser.add_argument(
           "csv_file",
           help="Path to the CSV file containing firm data"
       )
       
       parser.add_argument(
           "--subject-id",
           required=True,
           help="ID of the subject/client making the request"
       )
       
       parser.add_argument(
           "--skip-financials",
           action="store_true",
           help="Skip financial evaluation"
       )
       
       parser.add_argument(
           "--skip-legal",
           action="store_true",
           help="Skip legal evaluation"
       )
       
       parser.add_argument(
           "--output",
           help="Output file for results (default: stdout)"
       )
       
       args = parser.parse_args()
       
       results = process_batch_csv(
           args.csv_file,
           args.subject_id,
           args.skip_financials,
           args.skip_legal
       )
       
       if args.output:
           with open(args.output, 'w') as f:
               json.dump(results, f, indent=2)
           print(f"Results written to {args.output}")
       else:
           print(json.dumps(results, indent=2))
   
   if __name__ == "__main__":
       main()
   ```

4. **Expected CSV format**
   ```
   reference_id,business_ref,business_name,tax_id,organization_crd
   REF001,BIZ001,Acme Financial,12-3456789,123456
   REF002,BIZ002,Baker Investments,23-4567890,234567
   ```

### 2. Implement API Endpoint for Batch Processing

Add a new endpoint to the API for batch processing:

```python
# In api.py

from pydantic import BaseModel
from typing import List

class BatchRequest(BaseModel):
    csv_content: str
    skip_disciplinary: bool = True
    skip_regulatory: bool = True

@app.post("/process-batch")
async def process_batch(request: BatchRequest):
    """Process a batch of claims from CSV content."""
    # Write CSV content to a temporary file
    temp_file = Path("temp_batch.csv")
    temp_file.write_text(request.csv_content)
    
    try:
        # Process the batch
        from batch_processor import process_batch_csv
        results = process_batch_csv(
            str(temp_file),
            "API_USER",
            request.skip_disciplinary,
            request.skip_regulatory
        )
        return results
    finally:
        # Clean up temporary file
        if temp_file.exists():
            temp_file.unlink()
```

### 3. Implement Progress Tracking

To track what's working and what's not working, implement a tracking system:

1. **Create a tracking module**
   - Create a new file `tracking.py` in the project root
   - Implement functionality to track processing status and results

2. **Sample implementation:**
   ```python
   import json
   from datetime import datetime
   from pathlib import Path
   from typing import Dict, Any, List, Optional

   class ProcessingTracker:
       """Tracks the status and results of processing operations."""
       
       def __init__(self, tracking_file: str = "tracking.json"):
           """Initialize the tracker.
           
           Args:
               tracking_file: Path to the tracking file
           """
           self.tracking_file = Path(tracking_file)
           self.tracking_data = self._load_tracking_data()
           
       def _load_tracking_data(self) -> Dict[str, Any]:
           """Load tracking data from file."""
           if self.tracking_file.exists():
               try:
                   return json.loads(self.tracking_file.read_text())
               except json.JSONDecodeError:
                   return {"batches": [], "individual_claims": []}
           return {"batches": [], "individual_claims": []}
           
       def _save_tracking_data(self) -> None:
           """Save tracking data to file."""
           self.tracking_file.write_text(json.dumps(self.tracking_data, indent=2))
           
       def track_batch(self, batch_id: str, csv_path: str, results: List[Dict[str, Any]]) -> None:
           """Track a batch processing operation.
           
           Args:
               batch_id: Unique identifier for the batch
               csv_path: Path to the CSV file
               results: Processing results
           """
           success_count = sum(1 for r in results if r.get("status") == "success")
           error_count = sum(1 for r in results if r.get("status") == "error")
           
           batch_entry = {
               "batch_id": batch_id,
               "csv_path": csv_path,
               "timestamp": datetime.now().isoformat(),
               "total_claims": len(results),
               "success_count": success_count,
               "error_count": error_count,
               "status": "completed",
               "details": results
           }
           
           self.tracking_data["batches"].append(batch_entry)
           self._save_tracking_data()
           
       def track_claim(self, reference_id: str, business_ref: str, status: str, result: Optional[Dict[str, Any]] = None) -> None:
           """Track an individual claim processing operation.
           
           Args:
               reference_id: Reference ID for the claim
               business_ref: Business reference
               status: Processing status
               result: Processing result
           """
           claim_entry = {
               "reference_id": reference_id,
               "business_ref": business_ref,
               "timestamp": datetime.now().isoformat(),
               "status": status,
               "result": result
           }
           
           self.tracking_data["individual_claims"].append(claim_entry)
           self._save_tracking_data()
           
       def get_batch_summary(self) -> List[Dict[str, Any]]:
           """Get a summary of all batch operations."""
           return [
               {
                   "batch_id": batch["batch_id"],
                   "timestamp": batch["timestamp"],
                   "total_claims": batch["total_claims"],
                   "success_count": batch["success_count"],
                   "error_count": batch["error_count"],
                   "status": batch["status"]
               }
               for batch in self.tracking_data["batches"]
           ]
           
       def get_claim_summary(self) -> List[Dict[str, Any]]:
           """Get a summary of all individual claim operations."""
           return [
               {
                   "reference_id": claim["reference_id"],
                   "business_ref": claim["business_ref"],
                   "timestamp": claim["timestamp"],
                   "status": claim["status"]
               }
               for claim in self.tracking_data["individual_claims"]
           ]
   ```

3. **Integrate tracking with batch processor**
   ```python
   # In batch_processor.py
   
   from tracking import ProcessingTracker
   
   def process_batch_csv(csv_path: str, subject_id: str, skip_financials: bool = False, skip_legal: bool = False, batch_id: Optional[str] = None) -> List[Dict[str, Any]]:
       """Process multiple firms from a CSV file with tracking."""
       # Generate batch ID if not provided
       if batch_id is None:
           batch_id = f"BATCH_{datetime.now().strftime('%Y%m%d%H%M%S')}"
           
       # Initialize tracker
       tracker = ProcessingTracker()
       
       # Process batch as before
       results = []
       facade = FirmServicesFacade()
       
       # ... processing code ...
       
       # Track the batch
       tracker.track_batch(batch_id, csv_path, results)
       
       return results
   ```

4. **Add API endpoints for tracking**
   ```python
   # In api.py
   
   from tracking import ProcessingTracker
   
   @app.get("/tracking/batches")
   async def get_batch_tracking():
       """Get tracking information for batch operations."""
       tracker = ProcessingTracker()
       return tracker.get_batch_summary()
       
   @app.get("/tracking/claims")
   async def get_claim_tracking():
       """Get tracking information for individual claim operations."""
       tracker = ProcessingTracker()
       return tracker.get_claim_summary()
       
   @app.get("/tracking/batch/{batch_id}")
   async def get_batch_details(batch_id: str):
       """Get detailed tracking information for a specific batch."""
       tracker = ProcessingTracker()
       for batch in tracker.tracking_data["batches"]:
           if batch["batch_id"] == batch_id:
               return batch
       raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
   ```

## Testing

### Unit Testing

The project includes a comprehensive test suite in the `tests/` directory. Run tests using pytest:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_firm_services.py

# Run with coverage
pytest --cov=.
```

### Manual Testing

1. **API Testing**
   - Use tools like curl, Postman, or the built-in Swagger UI at http://localhost:8000/docs
   - Test individual endpoints with sample data

2. **UI Testing**
   - Access the UI at http://localhost:7860
   - Test form submission and result display

3. **Batch Processing Testing**
   - Create a sample CSV file in the `input/` directory
   - Run the batch processor with the sample file
   - Verify results in the tracking system

## Tracking Implementation

To track what's working and what's not working, use the following approach:

1. **Run batch processing**
   ```bash
   python batch_processor.py input/batch.csv --subject-id TEST_USER --output output/results.json
   ```

2. **Check tracking information**
   ```bash
   python -c "import json; print(json.dumps(json.load(open('tracking.json')), indent=2))"
   ```

3. **View tracking through API**
   - Access http://localhost:8000/tracking/batches for batch summary
   - Access http://localhost:8000/tracking/claims for individual claims

## Troubleshooting

### Common Issues

1. **Missing Data**
   - Ensure the CSV file has all required fields
   - Check that the FINRA and SEC APIs are accessible

2. **Cache Issues**
   - Clear cache if you encounter stale data:
     ```bash
     python cache_manager/cli.py --clear-cache ALL
     ```

3. **Logging**
   - Check log files in the `logs/` directory for detailed error information
   - Increase log level for more detailed output:
     ```bash
     python services/firm_services.py --log-level DEBUG ...
     ```

## Next Steps

1. Implement the batch processing functionality as outlined above
2. Add tracking system to monitor processing status
3. Enhance the API and UI to support batch operations
4. Add comprehensive error handling and reporting
5. Implement additional search strategies (TAX_ID_ONLY, SEC_NUMBER_ONLY, NAME_AND_LOCATION)