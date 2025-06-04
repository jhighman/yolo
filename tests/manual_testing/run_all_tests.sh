#!/bin/bash
# Script to run all API tests

# Set colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if API server is running
echo -e "${YELLOW}Checking if API server is running...${NC}"
if ! curl -s "http://localhost:8000/processing-modes" > /dev/null; then
  echo -e "${RED}API server is not running. Please start it with:${NC}"
  echo "uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info"
  exit 1
fi
echo -e "${GREEN}API server is running.${NC}"

# Function to run a test and check the result
run_test() {
  local test_name="$1"
  local curl_command="$2"
  local expected_status="$3"
  
  echo -e "\n${YELLOW}Running test: ${test_name}${NC}"
  echo "Command: $curl_command"
  
  # Run the curl command and capture output and status code
  output=$(eval "$curl_command" 2>&1)
  status=$?
  
  # Check if curl command was successful
  if [ $status -ne 0 ]; then
    echo -e "${RED}Test failed: curl command returned error code $status${NC}"
    echo "Output: $output"
    return 1
  fi
  
  # Check if response contains expected status code
  if echo "$output" | grep -q "\"status\":\"$expected_status\"" || echo "$output" | grep -q "HTTP/$expected_status"; then
    echo -e "${GREEN}Test passed!${NC}"
  else
    echo -e "${RED}Test failed: Response did not contain expected status '$expected_status'${NC}"
    echo "Output: $output"
    return 1
  fi
  
  return 0
}

# Test 1: Get processing modes
echo -e "\n${YELLOW}Test 1: Get processing modes${NC}"
curl -s "http://localhost:8000/processing-modes" | jq .

# Test 2: Process claim for Able Wealth Management
echo -e "\n${YELLOW}Test 2: Process claim for Able Wealth Management${NC}"
curl -s -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d "$(cat tests/manual_testing/test_data.json | jq '.[0]')" | jq .

# Test 3: Process claim for Adell, Harriman & Carpenter
echo -e "\n${YELLOW}Test 3: Process claim for Adell, Harriman & Carpenter${NC}"
curl -s -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d "$(cat tests/manual_testing/test_data.json | jq '.[1]')" | jq .

# Test 4: Process claim for ALLIANCE GLOBAL PARTNERS
echo -e "\n${YELLOW}Test 4: Process claim for ALLIANCE GLOBAL PARTNERS${NC}"
curl -s -X POST "http://localhost:8000/process-claim-basic" \
  -H "Content-Type: application/json" \
  -d "$(cat tests/manual_testing/test_data.json | jq '.[2]')" | jq .

# Test 5: List cache for BIZ_001
echo -e "\n${YELLOW}Test 5: List cache for BIZ_001${NC}"
curl -s -X GET "http://localhost:8000/cache/list?business_ref=BIZ_001" | jq .

# Test 6: Get latest compliance report for BIZ_001
echo -e "\n${YELLOW}Test 6: Get latest compliance report for BIZ_001${NC}"
curl -s -X GET "http://localhost:8000/compliance/latest/BIZ_001" | jq .

# Test 7: Get compliance report by reference ID
echo -e "\n${YELLOW}Test 7: Get compliance report by reference ID${NC}"
curl -s -X GET "http://localhost:8000/compliance/by-ref/BIZ_001/test-ref-001" | jq .

echo -e "\n${GREEN}All tests completed!${NC}"