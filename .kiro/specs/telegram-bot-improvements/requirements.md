# Requirements Document

## Introduction

This feature improves the Telegram bot user experience by implementing inline argument support with dialog fallbacks, fixing help command issues, redesigning settings interface with inline buttons, and adding a persistent bot keyboard with key commands. The improvements focus on making the bot more intuitive and user-friendly while maintaining all existing functionality.

## Requirements

### Requirement 1

**User Story:** As a user, I want commands to support both inline arguments and dialog-based input, so that I can use commands flexibly depending on my preference and context.

#### Acceptance Criteria

1. WHEN a user types `/memory_add` without arguments THEN the system SHALL prompt with a descriptive message asking for memory input
2. WHEN a user types `/memory_add some text` with arguments THEN the system SHALL process the text directly without prompting
3. WHEN a user is prompted for memory input THEN the system SHALL display "Write anything you want me to remember about you, it will be used during our interaction, e.g. in the briefings"
4. WHEN a user provides memory input after being prompted THEN the system SHALL confirm if the memory was stored successfully
5. WHEN a user types `/add_task` without arguments THEN the system SHALL prompt for task instruction with appropriate guidance
6. WHEN a user types `/add_countdown` without arguments THEN the system SHALL prompt for countdown description with examples
7. WHEN a user types `/ignore_email` without arguments THEN the system SHALL show usage information and examples

### Requirement 2

**User Story:** As a user, I want the `/help` command to display all commands correctly without formatting issues, so that I can easily understand what commands are available.

#### Acceptance Criteria

1. WHEN a user types `/help` THEN the system SHALL display all available commands without markdown escaping issues
2. WHEN the help message is displayed THEN all command names SHALL be properly formatted and readable
3. WHEN the help message is displayed THEN the system SHALL use plain text or HTML formatting instead of problematic markdown
4. WHEN the help message includes command examples THEN they SHALL be displayed correctly without parsing errors

### Requirement 3

**User Story:** As a user, I want the `/update_settings` command to show options as inline buttons in the chat, so that I can easily select settings without using an app keyboard.

#### Acceptance Criteria

1. WHEN a user types `/update_settings` THEN the system SHALL display setting options as inline keyboard buttons
2. WHEN setting options are displayed THEN they SHALL appear in the chat message, not as a persistent app keyboard
3. WHEN a user clicks a setting button THEN the system SHALL prompt for the new value for that specific setting
4. WHEN a user provides a new setting value THEN the system SHALL confirm the update and remove the inline keyboard
5. WHEN the settings interface is active THEN users SHALL be able to cancel the operation with a cancel button

### Requirement 4

**User Story:** As a user, I want a persistent bot keyboard with essential commands, so that I can quickly access the most important features without typing commands.

#### Acceptance Criteria

1. WHEN a user starts the bot THEN the system SHALL display a persistent keyboard with essential commands
2. WHEN the persistent keyboard is displayed THEN it SHALL include "Briefing" button
3. WHEN the persistent keyboard is displayed THEN it SHALL include "Schedule Task" button  
4. WHEN the persistent keyboard is displayed THEN it SHALL include "Add Countdown" button
5. WHEN the persistent keyboard is displayed THEN it SHALL include "Track Habit" button (placeholder for future implementation)
6. WHEN the persistent keyboard is displayed THEN it SHALL include "Memories" button
7. WHEN the persistent keyboard is displayed THEN it SHALL include "Settings" button
8. WHEN a user taps a keyboard button THEN the system SHALL execute the corresponding command
9. WHEN the keyboard is displayed THEN it SHALL remain available across all bot interactions
10. WHEN a user taps "Track Habit" THEN the system SHALL respond with a placeholder message indicating future implementation

### Requirement 5

**User Story:** As a user, I want consistent and intuitive command behavior across all bot interactions, so that I can predict how commands will work.

#### Acceptance Criteria

1. WHEN any command supports arguments THEN it SHALL work both with inline arguments and dialog prompts
2. WHEN a command is executed via keyboard button THEN it SHALL behave identically to typing the command
3. WHEN error messages are displayed THEN they SHALL be clear and provide guidance on correct usage
4. WHEN confirmation messages are shown THEN they SHALL be consistent in format and tone across all commands
5. WHEN the bot prompts for input THEN it SHALL provide clear instructions and examples where helpful