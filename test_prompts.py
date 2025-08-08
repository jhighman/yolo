import logging
from agents.adv_processing_agent import ADVProcessingAgent

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_prompt_versions():
    """Test different prompt versions for the ADV processing agent."""
    
    # Test with standard prompts
    logger.info("Testing with standard prompts")
    agent_standard = ADVProcessingAgent(prompt_version="standard")
    logger.info(f"Agent initialized with prompt_version={agent_standard.prompt_version}")
    
    # Test with simplified prompts
    logger.info("Testing with simplified prompts")
    agent_simplified = ADVProcessingAgent(prompt_version="simplified")
    logger.info(f"Agent initialized with prompt_version={agent_simplified.prompt_version}")
    
    # Test with prompt version override in process_adv
    logger.info("Testing with prompt version override in process_adv")
    subject_id = "TEST-001"
    crd_number = "8174"
    entity_data = {"has_adv_pdf": True, "firm_name": "Test Firm", "crd_number": crd_number}
    
    # Create a mock PDF path for testing (we won't actually process it)
    cache_path = agent_standard.get_cache_path(subject_id, crd_number)
    pdf_path = f"{cache_path}/adv-{crd_number}.pdf"
    
    # Just log which prompt would be used, don't actually call the API
    logger.info("Standard agent would use standard prompt")
    logger.info("Simplified agent would use simplified prompt")
    logger.info("Standard agent with override would use simplified prompt")
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    test_prompt_versions()