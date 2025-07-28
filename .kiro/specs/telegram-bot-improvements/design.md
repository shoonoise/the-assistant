# Design Document

## Overview

This design improves the Telegram bot user experience by implementing a flexible command argument system, fixing help command formatting issues, redesigning the settings interface with inline keyboards, and adding a persistent bot keyboard. The solution maintains backward compatibility while enhancing usability through modern Telegram bot patterns.

## Architecture

### Command Handler Architecture

The current command handler system will be enhanced with a dual-mode approach:
- **Direct Mode**: Commands with inline arguments are processed immediately
- **Dialog Mode**: Commands without arguments trigger interactive prompts

### Keyboard Management System

Two types of keyboards will be implemented:
- **Persistent Reply Keyboard**: Always visible at the bottom of the chat for quick access to main features
- **Inline Keyboards**: Temporary, message-attached keyboards for settings and confirmations

### Message Formatting System

A centralized message formatting system will handle:
- Plain text for user-generated content to avoid parsing issues
- HTML formatting for structured bot messages
- Proper escaping for special characters

## Components and Interfaces

### Enhanced Command Handlers

```python
class FlexibleCommandHandler:
    """Base class for commands supporting both inline and dialog modes."""
    
    async def handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        args: list[str]
    ) -> None:
        """Handle command with flexible argument support."""
        if args:
            await self.handle_direct_mode(update, context, args)
        else:
            await self.handle_dialog_mode(update, context)
    
    async def handle_direct_mode(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        args: list[str]
    ) -> None:
        """Process command with provided arguments."""
        pass
    
    async def handle_dialog_mode(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Start interactive dialog for argument collection."""
        pass
```

### Persistent Keyboard Manager

```python
class PersistentKeyboardManager:
    """Manages the persistent reply keyboard for quick access."""
    
    def create_main_keyboard(self) -> ReplyKeyboardMarkup:
        """Create the main persistent keyboard."""
        keyboard = [
            ["📊 Briefing", "📅 Schedule Task"],
            ["⏰ Add Countdown", "📈 Track Habit"],
            ["🧠 Memories", "⚙️ Settings"]
        ]
        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Choose an option or type a command..."
        )
    
    async def send_with_keyboard(
        self, 
        update: Update, 
        text: str
    ) -> None:
        """Send message with persistent keyboard attached."""
        await update.message.reply_text(
            text,
            reply_markup=self.create_main_keyboard(),
            parse_mode=ParseMode.HTML
        )
```

### Settings Interface Manager

```python
class SettingsInterfaceManager:
    """Manages inline keyboard-based settings interface."""
    
    def create_settings_keyboard(self) -> InlineKeyboardMarkup:
        """Create inline keyboard for settings selection."""
        keyboard = [
            [InlineKeyboardButton("👋 How to greet", callback_data="setting:greet")],
            [InlineKeyboardButton("⏰ Briefing time", callback_data="setting:briefing_time")],
            [InlineKeyboardButton("👤 About me", callback_data="setting:about_me")],
            [InlineKeyboardButton("📍 Location", callback_data="setting:location")],
            [InlineKeyboardButton("❌ Cancel", callback_data="setting:cancel")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_setting_callback(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard button presses for settings."""
        query = update.callback_query
        await query.answer()
        
        setting_key = query.data.split(":")[1]
        if setting_key == "cancel":
            await query.edit_message_text("Settings cancelled.")
            return
        
        # Store setting key in user data and prompt for value
        context.user_data["pending_setting"] = setting_key
        await query.edit_message_text(
            f"Enter new value for {SETTINGS_LABEL_MAP[setting_key]}:"
        )
```

### Message Formatter

```python
class MessageFormatter:
    """Centralized message formatting to avoid parsing issues."""
    
    @staticmethod
    def format_help_message() -> str:
        """Format help message using HTML for reliable rendering."""
        commands = []
        for command, description in COMMAND_REGISTRY.items():
            commands.append(f"/{command} - {html.escape(description)}")
        
        return (
            "<b>📚 Available Commands</b>\n\n" +
            "\n".join(commands) +
            "\n\n<b>💡 Tips:</b>\n"
            "• Use the keyboard buttons below for quick access\n"
            "• Commands support both inline arguments and dialogs\n"
            "• Type /settings to customize your experience"
        )
    
    @staticmethod
    def format_user_content(text: str) -> str:
        """Format user-generated content safely."""
        # Use plain text to avoid parsing issues with user input
        return text
    
    @staticmethod
    def format_confirmation(action: str, content: str) -> str:
        """Format confirmation messages consistently."""
        return f"✅ {action}: {html.escape(content)}"
```

## Data Models

### Enhanced Conversation States

```python
class ConversationState(IntEnum):
    """Extended conversation states for new functionality."""
    
    # Existing states
    SELECT_SETTING = 0
    ENTER_VALUE = 1
    SELECT_MEMORY_TO_DELETE = 2
    
    # New states for dialog mode
    MEMORY_INPUT = 3
    TASK_INPUT = 4
    COUNTDOWN_INPUT = 5
    EMAIL_PATTERN_INPUT = 6
```

### Command Context Data

```python
@dataclass
class CommandContext:
    """Context data for command processing."""
    
    command: str
    args: list[str]
    user_id: int
    chat_id: int
    is_dialog_mode: bool
    pending_action: str | None = None
```

### Keyboard Button Mapping

```python
KEYBOARD_COMMAND_MAP: dict[str, str] = {
    "📊 Briefing": "briefing",
    "📅 Schedule Task": "add_task",
    "⏰ Add Countdown": "add_countdown", 
    "📈 Track Habit": "track_habit",
    "🧠 Memories": "memory",
    "⚙️ Settings": "settings"
}
```

## Error Handling

### Command Validation

```python
class CommandValidator:
    """Validates command arguments and provides helpful feedback."""
    
    @staticmethod
    async def validate_memory_input(text: str) -> tuple[bool, str]:
        """Validate memory input and return success status with message."""
        if not text.strip():
            return False, "Memory cannot be empty. Please provide some text."
        
        if len(text) > 500:
            return False, "Memory is too long (max 500 characters)."
        
        return True, "Memory is valid."
    
    @staticmethod
    async def validate_task_input(text: str) -> tuple[bool, str]:
        """Validate task instruction input."""
        if not text.strip():
            return False, "Task instruction cannot be empty."
        
        return True, "Task instruction is valid."
```

### Error Recovery

```python
class ErrorHandler:
    """Handles errors gracefully with user-friendly messages."""
    
    @staticmethod
    async def handle_command_error(
        update: Update, 
        error: Exception, 
        command: str
    ) -> None:
        """Handle command execution errors."""
        error_message = (
            f"❌ Sorry, there was an error processing the /{command} command.\n\n"
            "Please try again or contact support if the problem persists."
        )
        
        await update.message.reply_text(
            error_message,
            reply_markup=PersistentKeyboardManager().create_main_keyboard()
        )
```

## Testing Strategy

### Unit Tests

- **Command Handler Tests**: Test both direct and dialog modes for each command
- **Keyboard Manager Tests**: Verify keyboard creation and button mapping
- **Message Formatter Tests**: Ensure proper HTML escaping and formatting
- **Validation Tests**: Test input validation for all command types

### Integration Tests

- **End-to-End Command Flow**: Test complete command execution from button press to completion
- **Conversation Handler Tests**: Verify state transitions in dialog mode
- **Keyboard Interaction Tests**: Test inline keyboard callbacks and persistent keyboard responses
- **Error Handling Tests**: Verify graceful error recovery and user feedback

### User Experience Tests

- **Command Discoverability**: Ensure all commands are accessible via keyboard and help
- **Dialog Flow Tests**: Verify intuitive dialog prompts and confirmations
- **Keyboard Persistence Tests**: Ensure keyboard remains available across interactions
- **Message Formatting Tests**: Verify messages display correctly across different clients

## Implementation Phases

### Phase 1: Enhanced Command Handlers
- Implement FlexibleCommandHandler base class
- Update memory_add, add_task, add_countdown commands
- Add input validation and error handling

### Phase 2: Settings Interface Redesign
- Replace conversation handler with inline keyboard approach
- Implement SettingsInterfaceManager
- Add callback query handlers for settings

### Phase 3: Persistent Keyboard Implementation
- Create PersistentKeyboardManager
- Add keyboard button to command mapping
- Update all message responses to include keyboard

### Phase 4: Help Command and Message Formatting
- Implement MessageFormatter with HTML support
- Update help command to use new formatting
- Fix all markdown escaping issues

### Phase 5: Track Habit Placeholder
- Add placeholder handler for track habit functionality
- Prepare interface for future implementation
- Document extension points for habit tracking