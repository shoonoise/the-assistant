# The Assistant

A Temporal-based personal assistant that integrates with Obsidian notes, Google Calendar, and Telegram to automate workflows and provide intelligent reminders.

## Project Structure

```
the-assistant/
├── src/the_assistant/           # Main package
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── activities/              # Temporal activities
│   │   ├── get_calendar_events.py
│   │   └── scan_obsidian_notes.py
│   ├── integrations/            # External service clients
│   │   ├── google_client.py     # Google Calendar integration
│   │   ├── obsidian_client.py   # Obsidian vault operations
│   │   └── telegram_client.py   # Telegram bot integration
│   ├── utils/                   # Utility functions
│   │   └── helpers.py
│   └── workflows/               # Temporal workflows
│       ├── french_lesson.py
│       ├── daily_briefing.py
│       └── trip_reminder.py
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   │   ├── test_activities.py  # Tests for Temporal activities
│   │   ├── test_utils.py       # Tests for utility functions
│   │   └── integrations/       # Integration-specific unit tests
│   │       └── obsidian/       # Obsidian-specific tests
│   ├── integration/            # Integration tests
│   │   ├── test_workflows.py   # Workflow integration tests
│   │   ├── test_obsidian_integration.py
│   │   └── test_google_integration.py
│   └── conftest.py             # Shared test fixtures
├── obsidian_vault/             # Mount point for Obsidian vault
├── secrets/                    # Credentials and secrets
├── docker-compose.yml          # Docker services
├── pyproject.toml              # Python package configuration
└── README.md
```

## Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Docker and Docker Compose
- Obsidian vault (for note integration)
- Google Calendar API credentials
- Telegram bot token

### Installation

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd the-assistant
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Set up environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Configure credentials**:
   - Place Google Calendar credentials in `secrets/google.json`
   - Set up Telegram bot token in `.env`
   - Configure Obsidian vault path in `.env`

5. **Initialize the database**:


   ```bash
   # For verbose output
   uv run python scripts/init_db_with_migrations.py --verbose
   
   # To specify a custom database URL
   uv run python scripts/init_db_with_migrations.py --database-url postgresql+asyncpg://user:pass@host:port/dbname
   
   # To run only migrations (if database already exists)
   make migrate
   ```

6. **Start services**:

   ```bash
   docker-compose up -d
   ```

### Environment Variables

Create a `.env` file in the project root:

```env
# Temporal server address
TEMPORAL_HOST=temporal:7233

# API Keys and Tokens
TELEGRAM_TOKEN=your_telegram_bot_token_here

# Secret used for signing OAuth state tokens
JWT_SECRET=change_me

# Paths (inside container)
OBSIDIAN_VAULT_PATH=/vault
GOOGLE_CREDENTIALS_PATH=/secrets/google.json
# Fernet key for encrypting stored credentials
DB_ENCRYPTION_KEY=your-generated-key
```

Generate a new key using:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

and assign it to `DB_ENCRYPTION_KEY`. This variable is required and the
application will exit if it is missing.

### Google Calendar Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create credentials (Service Account or OAuth 2.0)
5. Download the JSON file and place it in `secrets/google.json`
6. To authenticate multiple Google accounts, start the OAuth flow with an
   `account` query parameter, for example `?account=personal` or
   `?account=work`.

### Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/BotFather)
2. Get the bot token
3. Add the token to your `.env` file
4. Start a chat with your bot to get your chat ID

### Database Schema

The application uses a PostgreSQL database with SQLAlchemy models and Alembic migrations for schema management:

1. **Users Table**: Stores user identity and integration information
   - `id`: Primary key
   - `auth_provider`: Authentication provider (e.g., "telegram", "google")
   - `external_id`: External identifier from the auth provider
   - `username`: Optional username
   - `first_name`, `last_name`: User's name
   - `google_credentials_enc`: Encrypted Google credentials (if applicable)
   - Timestamps for registration, creation, and updates

2. **User Settings Table**: Stores user preferences in a key-value structure
   - `id`: Primary key
   - `user_id`: Foreign key to users table
   - `key`: Setting name
   - `value_json`: Setting value stored as JSON text
   - Timestamps for creation and updates

The database schema is managed using Alembic migrations. Use `make init-db` to initialize the database or `make migrate` to apply new migrations.

**Creating new migrations:**
```bash
make migration MESSAGE="Add new feature"
```

### Obsidian Integration

1. Mount your Obsidian vault directory to `/vault` in the container
2. Ensure your notes use the expected format:
   - Trip notes: `#trip` tag with `status: planned` in frontmatter
   - Tasks: Use `- [ ]` for unchecked and `- [x]` for checked tasks

## Usage

### Running the Application

**Development mode**:

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f app
```

**Production mode**:

```bash
# Build and run
docker-compose up -d --build
```

### Accessing Services

- **FastAPI**: <http://localhost:8000>
- **Temporal UI**: <http://localhost:8080>
- **PostgreSQL**: localhost:5432

### Testing

Run the test suite:

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Obsidian-specific tests
python -m pytest tests/unit/integrations/obsidian/ -v

# All tests
python -m pytest tests/ -v
```

### Workflows

#### Trip Reminder

Scans Obsidian notes for upcoming trips and sends reminders about pending tasks.

**Trigger**: Scheduled (daily check)
**Requirements**: Notes with `#trip` tag and `status: planned`

#### French Lesson Manager

Monitors Google Calendar for French lesson events and sends preparation reminders.

**Trigger**: Calendar events matching "French Lesson"
**Features**: Pre-lesson notifications, post-lesson feedback

#### Daily Briefing

Summarizes today's and tomorrow's events along with the local weather forecast and a list of recent unread emails.

**Trigger**: Scheduled (morning) or manual
**Content**: Weather, events for today and tomorrow, top unread emails

## Development

### Package Structure

The project follows Python packaging standards with:

- `src/the_assistant/` - Main package directory
- Proper `__init__.py` files for imports
- `pyproject.toml` for dependency management
- Hatchling as build backend

### Adding New Workflows

1. Create workflow in `src/the_assistant/workflows/`
2. Add required activities in `src/the_assistant/activities/`
3. Add integration clients in `src/the_assistant/integrations/`
4. Register workflow in Temporal worker
5. Add tests in `tests/`

### Adding New Integrations

1. Create client in `src/the_assistant/integrations/`
2. Implement required methods with proper error handling
3. Add activities that use the integration
4. Add configuration variables to `.env`
5. Update documentation

## Troubleshooting

### Common Issues

1. **Docker services not starting**:
   - Check port conflicts (5432, 7233, 8000)
   - Verify Docker is running
   - Check logs: `docker-compose logs`

2. **Temporal connection issues**:
   - Ensure Temporal server is running
   - Check `TEMPORAL_HOST` in `.env`
   - Verify network connectivity

3. **Google Calendar authentication**:
   - Verify `secrets/google.json` exists
   - Check credentials scope and permissions
   - Ensure Calendar API is enabled

4. **Obsidian integration not working**:
   - Check vault path mounting
   - Verify note format and metadata
   - Ensure vault directory is accessible and contains markdown files

5. **Database initialization issues**:
   - Ensure PostgreSQL is running
   - Check database connection parameters
   - Verify `DB_ENCRYPTION_KEY` is set in `.env`
   - Run `make init-db` or use `--verbose` flag for detailed logs
   - Check migration status with `uv run alembic current`
   - Ensure the user has permissions to create databases and tables

### Logs

Check application logs:

```bash
docker-compose logs -f app
```

Check Temporal UI for workflow execution details:
<http://localhost:8080>

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Run the test suite
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
