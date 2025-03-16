"""
Command-line menu helper for batch processing of business entity compliance claims.
Provides options to run processing, toggle settings, manage logging, and adjust wait time.
"""

import logging
from typing import Dict, Set

logger = logging.getLogger('firm_main_menu_helper')

def display_menu(skip_financials: bool, skip_legal: bool, wait_time: float) -> str:
    """
    Display the menu and return the user's choice.

    Args:
        skip_financials (bool): Whether financial reviews are skipped.
        skip_legal (bool): Whether legal reviews are skipped.
        wait_time (float): Delay between processing records.

    Returns:
        str: User's menu choice.
    """
    print("\nFirm Compliance CSV Processor Menu:")
    print("1. Run batch processing")
    print(f"2. Toggle financial review (currently: {'skipped' if skip_financials else 'enabled'})")
    print(f"3. Toggle legal review (currently: {'skipped' if skip_legal else 'enabled'})")
    print("4. Save settings")
    print("5. Manage logging groups")
    print("6. Flush logs")
    print("7. Set trace mode (all groups on, DEBUG level)")
    print("8. Set production mode (minimal logging)")
    print(f"9. Set wait time between records (currently: {wait_time} seconds)")
    print("10. Exit")
    return input("Enter your choice (1-10): ").strip()

def handle_menu_choice(choice: str, skip_financials: bool, skip_legal: bool, 
                       enabled_groups: Set[str], group_levels: Dict[str, str], wait_time: float, 
                       config: Dict[str, object], loggers: Dict[str, logging.Logger], 
                       LOG_LEVELS: Dict[str, tuple], save_config_func, flush_logs_func) -> tuple:
    """
    Handle the user's menu choice and update settings.

    Args:
        choice (str): User's menu selection.
        skip_financials (bool): Current state of financial review toggle.
        skip_legal (bool): Current state of legal review toggle.
        enabled_groups (Set[str]): Enabled logging groups.
        group_levels (Dict[str, str]): Logging levels for each group.
        wait_time (float): Current wait time between records.
        config (Dict[str, object]): Configuration dictionary.
        loggers (Dict[str, logging.Logger]): Logger instances.
        LOG_LEVELS (Dict[str, tuple]): Mapping of level choices to log levels.
        save_config_func (callable): Function to save config.
        flush_logs_func (callable): Function to flush logs.

    Returns:
        tuple: Updated (skip_financials, skip_legal, enabled_groups, group_levels, wait_time).
    """
    if choice == "2":
        skip_financials = not skip_financials
        logger.info(f"Financial review {'skipped' if skip_financials else 'enabled'}")
        print(f"Financial review is now {'skipped' if skip_financials else 'enabled'}")
    elif choice == "3":
        skip_legal = not skip_legal
        logger.info(f"Legal review {'skipped' if skip_legal else 'enabled'}")
        print(f"Legal review is now {'skipped' if skip_legal else 'enabled'}")
    elif choice == "4":
        config.update({
            "skip_financials": skip_financials,
            "skip_legal": skip_legal,
            "enabled_logging_groups": list(enabled_groups),
            "logging_levels": dict(group_levels)
        })
        save_config_func(config)
        print(f"Settings saved to {config['config_file']}")
    elif choice == "5":
        manage_logging_groups(enabled_groups, group_levels, LOG_LEVELS)
    elif choice == "6":
        flush_logs_func()
        print("Logs flushed")
    elif choice == "7":
        enabled_groups.clear()
        enabled_groups.update({"services", "agents", "core"})
        group_levels.update({group: "DEBUG" for group in enabled_groups})
        print("Trace mode enabled: all groups ON, level DEBUG")
    elif choice == "8":
        enabled_groups.clear()
        enabled_groups.add("core")
        group_levels.update({"core": "INFO", "services": "WARNING", "agents": "WARNING"})
        print("Production mode enabled: minimal logging (core INFO, others OFF)")
    elif choice == "9":
        try:
            new_wait_time = float(input(f"Enter wait time in seconds (current: {wait_time}, default: {config['default_wait_time']}): ").strip())
            if new_wait_time >= 0:
                wait_time = new_wait_time
                logger.info(f"Wait time set to {wait_time} seconds")
                print(f"Wait time set to {wait_time} seconds")
            else:
                print("Wait time must be non-negative")
        except ValueError:
            print("Invalid input. Please enter a number")
    elif choice == "10":
        logger.info("User chose to exit")
        print("Exiting...")
    else:
        logger.warning(f"Invalid menu choice: {choice}")
        print("Invalid choice. Please enter 1-10.")
    return skip_financials, skip_legal, enabled_groups, group_levels, wait_time

def manage_logging_groups(enabled_groups: Set[str], group_levels: Dict[str, str], LOG_LEVELS: Dict[str, tuple]):
    """
    Submenu for managing logging groups and levels.

    Args:
        enabled_groups (Set[str]): Set of enabled logging groups.
        group_levels (Dict[str, str]): Logging levels for each group.
        LOG_LEVELS (Dict[str, tuple]): Mapping of level choices to log levels.
    """
    print("\nLogging Groups Management:")
    print("Available groups: services, agents, core")
    for group in ["services", "agents", "core"]:
        status = "enabled" if group in enabled_groups else "disabled"
        level = group_levels.get(group, "INFO")
        print(f"{group} - {status}, Level: {level}")
    print("\nOptions:")
    print("1. Toggle group on/off")
    print("2. Set group level")
    print("3. Back")
    sub_choice = input("Enter your choice (1-3): ").strip()

    if sub_choice == "1":
        group = input("Enter group name (services/agents/core): ").strip().lower()
        if group in ["services", "agents", "core"]:
            if group in enabled_groups:
                enabled_groups.remove(group)
                logger.info(f"Disabled logging group: {group}")
                print(f"{group} logging disabled")
            else:
                enabled_groups.add(group)
                logger.info(f"Enabled logging group: {group}")
                print(f"{group} logging enabled")
        else:
            print("Invalid group name")
    elif sub_choice == "2":
        group = input("Enter group name (services/agents/core): ").strip().lower()
        if group in ["services", "agents", "core"]:
            print("Levels: 1=DEBUG, 2=INFO, 3=WARNING, 4=ERROR, 5=CRITICAL")
            level_choice = input("Enter level (1-5): ").strip()
            if level_choice in LOG_LEVELS:
                group_levels[group] = LOG_LEVELS[level_choice][0]
                logger.info(f"Set {group} logging level to {LOG_LEVELS[level_choice][0]}")
                print(f"{group} level set to {LOG_LEVELS[level_choice][0]}")
            else:
                print("Invalid level choice")
        else:
            print("Invalid group name")
    elif sub_choice != "3":
        print("Invalid choice")