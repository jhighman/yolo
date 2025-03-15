import logging
import logging.handlers
import os
from pathlib import Path
from typing import Dict, Set, Any

# Define LOGGER_GROUPS at module scope
LOGGER_GROUPS = {
    'services': {
        'services': 'services',
        'firm_normalizer': 'firm_normalizer',
        'firm_marshaller': 'firm_marshaller',
        'firm_business': 'firm_business',
        'firm_name_matcher': 'firm_name_matcher'
    },
    'agents': {
        'finra_disciplinary': 'finra_disciplinary_agent',
        'sec_disciplinary': 'sec_disciplinary_agent',
        'finra_arbitration': 'finra_arbitration_agent',
        'finra_brokercheck': 'finra_brokercheck_agent',
        'nfa_basic': 'nfa_basic_agent',
        'sec_arbitration': 'sec_arbitration_agent',
        'sec_iapd': 'sec_iapd_agent',
        'agent_manager': 'agent_manager'
    },
    'evaluation': {
        'evaluation': 'firm_evaluation_processor',
        'evaluation_builder': 'firm_evaluation_report_builder',
        'evaluation_director': 'firm_evaluation_report_director'
    },
    'core': {
        'main': 'main',
        'business': 'business',
        'services': 'services',
        'finra_disciplinary': 'finra_disciplinary_agent',
        'sec_disciplinary': 'sec_disciplinary_agent',
        'finra_arbitration': 'finra_arbitration_agent',
        'finra_brokercheck': 'finra_brokercheck_agent',
        'nfa_basic': 'nfa_basic_agent',
        'sec_arbitration': 'sec_arbitration_agent',
        'sec_iapd': 'sec_iapd_agent',
        'agent_manager': 'agent_manager',
        'evaluation_processor': 'firm_evaluation_processor',
        'api': 'api'
    }
}

# Global flag to track if logging has been initialized
_LOGGING_INITIALIZED = False

def setup_logging(debug: bool = False) -> Dict[str, logging.Logger]:
    """Configure logging for all modules, ensuring idempotency."""
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return {key: logging.getLogger(name) for key, name in LOGGER_GROUPS['core'].items()}

    # Create logs directory structure
    log_dir = "logs"
    for group in LOGGER_GROUPS.keys():
        os.makedirs(os.path.join(log_dir, group), exist_ok=True)

    # Set level based on debug flag
    base_level = logging.DEBUG if debug else logging.INFO

    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Create console handler for all logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(base_level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(base_level)

    # Initialize all loggers from groups
    loggers = {}
    for group_name, group_loggers in LOGGER_GROUPS.items():
        # Create a file handler for this group
        group_log_file = os.path.join(log_dir, group_name, f"{group_name}.log")
        file_handler = logging.handlers.RotatingFileHandler(
            group_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(base_level)
        file_handler.setFormatter(formatter)
        
        # Create and configure loggers for this group
        for logger_key, logger_name in group_loggers.items():
            logger = logging.getLogger(logger_name)
            logger.setLevel(base_level)
            logger.propagate = False  # Don't propagate to root logger
            logger.addHandler(console_handler)  # Add console handler
            logger.addHandler(file_handler)  # Add group-specific file handler
            loggers[logger_key] = logger

    # Add group information to the loggers dict
    loggers['_groups'] = LOGGER_GROUPS

    _LOGGING_INITIALIZED = True
    return loggers

def reconfigure_logging(loggers: Dict[str, Any], enabled_groups: Set[str], group_levels: Dict[str, str]) -> None:
    """Reconfigure logging settings for specified logger groups.
    
    Args:
        loggers: Dictionary containing logger instances and group information
        enabled_groups: Set of group names to enable
        group_levels: Dictionary mapping group names to their desired log levels
    """
    # Get the groups dictionary from the loggers dict, defaulting to empty dict if not found
    groups = loggers.get('_groups', {})
    if not isinstance(groups, dict):
        return
        
    for group_name, group_loggers in groups.items():
        if not isinstance(group_loggers, dict):
            continue
            
        if group_name in enabled_groups:
            level = group_levels.get(group_name, logging.INFO)
            numeric_level = level if isinstance(level, int) else getattr(logging, str(level).upper(), logging.INFO)
            for logger_name in group_loggers.values():
                if isinstance(logger_name, str):
                    logger = logging.getLogger(logger_name)
                    logger.setLevel(numeric_level)
                    logger.disabled = False
        else:
            for logger_name in group_loggers.values():
                if isinstance(logger_name, str):
                    logger = logging.getLogger(logger_name)
                    logger.disabled = True

def flush_logs():
    """Flush all log handlers to ensure logs are written to disk."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.flush()