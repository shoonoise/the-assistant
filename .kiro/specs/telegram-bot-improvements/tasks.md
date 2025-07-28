# Implementation Plan

- [x] 1. Create enhanced command handler infrastructure
  - Implement FlexibleCommandHandler base class with dual-mode support
  - Add CommandValidator class for input validation
  - Create ErrorHandler class for graceful error recovery
  - _Requirements: 1.1, 1.2, 5.1, 5.4_

- [x] 2. Implement message formatting system
  - Create MessageFormatter class with HTML support
  - Add methods for safe user content formatting
  - Implement consistent confirmation message formatting
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 3. Update help command with proper formatting
  - Modify handle_help_command to use MessageFormatter
  - Replace problematic markdown with HTML formatting
  - Ensure all commands display correctly without escaping issues
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4. Create persistent keyboard management system
  - Implement PersistentKeyboardManager class
  - Create main keyboard layout with essential commands
  - Add keyboard button to command mapping dictionary
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

- [x] 5. Implement keyboard button handler
  - Create handler for persistent keyboard button presses
  - Map keyboard buttons to corresponding commands
  - Ensure identical behavior between buttons and typed commands
  - _Requirements: 4.8, 5.2_

- [x] 6. Update memory_add command with dual-mode support
  - Modify handle_memory_add_command to support both inline args and dialog
  - Add descriptive prompt for dialog mode
  - Implement confirmation message after memory storage
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 7. Update add_task command with dual-mode support
  - Modify handle_add_task_command for flexible argument handling
  - Add helpful prompt when no arguments provided
  - Include usage examples in dialog prompt
  - _Requirements: 1.5, 5.1_

- [x] 8. Update add_countdown command with dual-mode support
  - Modify handle_add_countdown_command for dual-mode operation
  - Add descriptive prompt with examples for dialog mode
  - Ensure consistent behavior between modes
  - _Requirements: 1.6, 5.1_

- [x] 9. Update ignore_email command with dual-mode support
  - Modify handle_ignore_email_command to show usage when no args
  - Ensure existing usage information display works correctly
  - _Requirements: 1.7_

- [x] 10. Create settings interface with inline keyboards
  - Implement SettingsInterfaceManager class
  - Create inline keyboard for settings selection
  - Replace conversation handler approach with callback-based system
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 11. Implement settings callback handlers
  - Create callback query handler for settings button presses
  - Handle setting value input after button selection
  - Add cancel functionality for settings interface
  - _Requirements: 3.2, 3.3, 3.4, 3.5_

- [x] 12. Add track habit placeholder functionality
  - Create handle_track_habit_command with placeholder message
  - Add button to persistent keyboard
  - Document extension points for future implementation
  - _Requirements: 4.6, 4.10_

- [x] 13. Update conversation states and constants
  - Add new conversation states for dialog mode commands
  - Update KEYBOARD_COMMAND_MAP with button mappings
  - Extend ConversationState enum as needed
  - _Requirements: 5.1, 4.8_

- [x] 14. Update all message responses to include persistent keyboard
  - Modify all command handlers to send persistent keyboard with responses
  - Ensure keyboard remains available across all interactions
  - Update error messages to include keyboard
  - _Requirements: 4.9, 5.4_

- [x] 15. Update start command to initialize persistent keyboard
  - Modify handle_start_command to send initial keyboard
  - Ensure new users see the persistent keyboard immediately
  - _Requirements: 4.1, 4.9_

- [x] 16. Create comprehensive error handling
  - Add try-catch blocks to all command handlers
  - Implement user-friendly error messages
  - Ensure errors don't break keyboard functionality
  - _Requirements: 5.4, 5.5_

- [x] 17. Update command registration and setup
  - Register new callback query handlers for inline keyboards
  - Add keyboard button message handler
  - Update create_telegram_client function with new handlers
  - _Requirements: 3.2, 4.8, 5.2_

- [x] 18. Add input validation for all dialog modes
  - Implement validation for memory input in dialog mode
  - Add validation for task and countdown inputs
  - Provide clear feedback for invalid inputs
  - _Requirements: 1.3, 1.4, 5.5_

- [x] 19. Update existing conversation handlers
  - Modify memory deletion conversation to work with new keyboard
  - Ensure existing settings conversation is replaced properly
  - Test compatibility with persistent keyboard
  - _Requirements: 4.9, 5.1_

- [x] 20. Integrate all components and test end-to-end functionality
  - Wire together all new components
  - Test complete user flows from keyboard to completion
  - Verify consistent behavior across all command types
  - Ensure backward compatibility with existing functionality
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_