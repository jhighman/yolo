# 🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟🌟
#          ____ _   _ ____  _____   ✨
#         / ___| | | |  _ \| ____|  🌟
#        | |   | |_| | |_) |  _|    🌟
#        | |___|  _  |  __/| |___   🌟
#         \____|_| |_|_|   |_____|  ✨
#          A Beautiful Cache Management Solution 🌟

## Overview

The `cache_manager` package provides a robust solution for handling cached data related to business regulatory and compliance reporting. It streamlines the management of business regulatory and compliance data with a structured cache system and intuitive tools, making it ideal for compliance teams, developers, and system administrators.

### Key Features

- 🔧 Modular design with focused modules (e.g., `cache_operations`, `firm_compliance_handler`)
- 🧹 Comprehensive cache management (clearing, listing, cleanup)
- 📊 Compliance report handling with versioning and pagination
- 🔄 JSON-formatted outputs for seamless integration
- 💻 User-friendly CLI interface
- 🕒 Automatic cleanup of stale cache older than 90 days

## Cache Folder Structure

```
cache/
└── BIZ_001/
    ├── SEC_Search_Agent/
    │   ├── SEC_Search_Agent_BIZ_001_20250315.json
    │   ├── manifest.txt
    ├── FINRA_Search_Agent/
    ├── FirmComplianceReport_B123_v1_20250315.json
    ├── request_log.txt
```

- Agent folders (e.g., `SEC_Search_Agent`) store agent-specific data
- Compliance reports (e.g., `FirmComplianceReport_B123_v1_20250315.json`) are stored directly under business_ref folders with versioning

## Getting Started

### Prerequisites

- Python 3.7+
- No external dependencies beyond the standard library

### Installation

1. Clone or download the repository:
```bash
git clone https://github.com/yourusername/cache_manager.git
cd cache_manager
```

2. Optional package installation:
```bash
pip install .
```

### Quick Usage

```bash
python -m cache_manager.cli --list-cache BIZ_001
```

## Modules and Usage

### cache_operations.CacheManager

Purpose: Manages general cache operations (clearing, listing, cleanup).

#### Example (Clear Cache):
```python
from cache_manager.cache_operations import CacheManager
manager = CacheManager()
print(manager.clear_cache("BIZ_001"))
```

Output:
```json
{
  "business_ref": "BIZ_001",
  "cleared_agents": ["SEC_Search_Agent"],
  "status": "success",
  "message": "Cleared cache for 1 agents"
}
```

#### Example (List All Cache):
```python
print(manager.list_cache())
```

Output:
```json
{
  "status": "success",
  "message": "Listed all businesses with cache",
  "cache": {
    "businesses": ["BIZ_001", "FIRM-XYZ"]
  }
}
```

### firm_compliance_handler.FirmComplianceHandler

Purpose: Handles compliance report retrieval and listing.

#### Example (Get Latest Compliance Report):
```python
from cache_manager.firm_compliance_handler import FirmComplianceHandler
handler = FirmComplianceHandler()
print(handler.get_latest_compliance_report("BIZ_001"))
```

Output:
```json
{
  "business_ref": "BIZ_001",
  "status": "success",
  "message": "Retrieved latest compliance report: FirmComplianceReport_B123_v1_20250315.json",
  "report": {
    "reference_id": "B123",
    "final_evaluation": {"overall_compliance": true, "alerts": []}
  }
}
```

#### Example (List Compliance Reports):
```python
print(handler.list_compliance_reports("BIZ_001", page=1, page_size=5))
```

Output:
```json
{
  "business_ref": "BIZ_001",
  "status": "success",
  "message": "Listed 1 compliance reports for BIZ_001",
  "reports": [
    {
      "reference_id": "B123",
      "file_name": "FirmComplianceReport_B123_v1_20250315.json",
      "last_modified": "2025-03-15 10:00:00"
    }
  ],
  "pagination": {
    "total_items": 1,
    "total_pages": 1,
    "current_page": 1,
    "page_size": 5
  }
}
```

## Command-Line Interface (CLI)

Access the CLI via `python -m cache_manager.cli --help`

### Usage Examples:

```bash
# Clear cache
python -m cache_manager.cli --clear-cache BIZ_001

# List compliance reports
python -m cache_manager.cli --list-compliance-reports --page 1 --page-size 10

# Get latest report
python -m cache_manager.cli --get-latest-compliance BIZ_001

# Clean up stale cache
python -m cache_manager.cli --cleanup-stale

# Custom cache folder
python -m cache_manager.cli --cache-folder /custom/path --list-cache ALL
```

## Full Feature List

### cache_operations.CacheManager
- `clear_cache(business_ref)`: Clears all agent caches except compliance reports
- `clear_agent_cache(business_ref, agent_name)`: Clears a specific agent's cache
- `list_cache(business_ref=None)`: Lists cache for all or one business
- `cleanup_stale_cache()`: Removes files older than 90 days (excluding compliance reports)

### firm_compliance_handler.FirmComplianceHandler
- `get_latest_compliance_report(business_ref)`: Retrieves the latest report with versioning
- `get_compliance_report_by_ref(business_ref, reference_id)`: Retrieves a report by reference ID
- `list_compliance_reports(business_ref=None, page=1, page_size=10)`: Lists reports with pagination

## Troubleshooting

### Common Issues and Fixes

1. **No Cache Found**
   - Check cache_folder existence and permissions:
     ```bash
     ls -ld <cache_folder>
     # or in Python
     os.access(path, os.R_OK)
     ```

2. **Empty Report Listings**
   - Verify files match `FirmComplianceReport_*_v*.json` pattern:
     ```bash
     ls -l cache/BIZ_001/
     ```

3. **Permission Errors**
   - Adjust permissions:
     ```bash
     chmod -R u+rw <cache_folder>
     ```

4. **Stale Cache Not Removed**
   - Confirm `CACHE_TTL_DAYS` (default: 90) and file timestamps

### Debugging Tips

1. Set `LOG_LEVEL = "INFO"` or `"DEBUG"` in `config.py` for detailed logs
2. Monitor logs: `tail -f cache_manager.log` (if redirected)

---
For more information or support, please refer to the documentation or open an issue on GitHub. 