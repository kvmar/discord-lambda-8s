# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Discord Lambda 8s is a serverless Discord bot built on AWS Lambda and API Gateway. It implements a queue and matchmaking system for competitive gaming with features like leaderboards, ELO ranking (TrueSkill), and team assignment.

**Core Tech Stack:**
- Python 3.9 (Lambda runtime)
- Discord.py-style Interaction API
- AWS Lambda + API Gateway (serverless compute)
- DynamoDB (via boto3) for data persistence
- GitHub Actions for CI/CD

## Architecture

### High-Level Flow

```
Discord User Command/Button
    ↓
API Gateway → Lambda Function (lambda_function.py)
    ↓
Signature Verification (nacl library)
    ↓
Interaction Routing:
  ├── Ping (type=1) → Return PING_RESPONSE
  ├── Command (type=2) → CommandRegistry.find_func() → Execute command
  └── Button Click (component_type=2) → ButtonManager.button_flow_tree()
```

### Module Organization

**discord_lambda/** — Reusable Discord bot framework
- `Interaction`: Parses Discord interactions, provides response methods (send_response, send_followup, defer)
- `Embedding`: Builds rich message embeds with fields, colors, thumbnails
- `Components`: Constructs button action rows
- `CommandRegistry`: Discovers and registers slash commands from command directory
- `CommandRegistryPickler`: Serializes CommandRegistry for Lambda layer (auto-executed during build)
- `CommandArg`: Defines slash command options and choices

**commands/** — Discord slash commands
- Each file defines one or more commands via `def setup(registry: CommandRegistry)` 
- Commands are executed with `def command_name(interaction: Interaction, **args)`
- Example: `queue.py`, `leaderboard.py`, `help.py`

**core/** — Business logic managers
- `QueueManager`: Manages player queues, team selection, match state
- `LeaderboardManager`: Builds and formats ranked player leaderboards (paginated with buttons)
- `ButtonManager`: Routes button clicks to handler functions (join/leave queue, team won, etc.)

**dao/** — Data Access Objects (DynamoDB operations)
- `QueueDao`: CRUD operations for queue records
- `PlayerDao`: Player profile management (ELO, name, game history)
- `LeaderboardDao`: Leaderboard queries and rankings

**lambda_function.py** — AWS Lambda handler
- Entry point: `lambda_handler(event, context)`
- Verifies Discord request signature (security requirement)
- Routes interactions to appropriate handlers
- Loads pickled CommandRegistry from Lambda layer at runtime

## Key Concepts

### Interaction Lifecycle

1. **Receive**: Discord sends signed HTTP POST to API Gateway
2. **Verify**: Check signature with PUBLIC_KEY to prevent spoofing
3. **Parse**: Extract interaction type, user, command name, options
4. **Route**:
   - Type 1 (PING) → Return `{"type": 1}` immediately
   - Type 2 (COMMAND) → Defer, find function in registry, execute
   - Component (BUTTON) → Route via ButtonManager button_flow_tree
5. **Respond**: Send via callback URL (immediate) or webhook URL (followup within 15 min)

### Embedding Pattern

```python
from discord_lambda import Embedding, Components

# Create embed with fields
embed = Embedding(
    title="Queue Status",
    desc="Current players in queue",
    color=0x0099FF  # Blue
)
embed.add_field("Players", "3/5", inline=True)
embed.add_field("Captain", "Alice", inline=True)

# Create buttons
components = Components()
components.add_button(label="Join", custom_id="queue#join", disabled=False, style=1)
components.add_button(label="Leave", custom_id="queue#leave", disabled=False, style=4)

# Send response
interaction.send_response(embeds=[embed], components=[components], ephemeral=False)
```

### Command Registration Pattern

```python
# commands/mycommand.py
def my_command(interaction: Interaction, option1: str, option2: int) -> None:
    """Handler receives options as kwargs from Discord"""
    interaction.defer()  # Always defer for long operations
    # Do work...
    interaction.send_response(embeds=[...], ephemeral=True)

def setup(registry: CommandRegistry) -> None:
    """Called during initialization to register this command"""
    registry.register_cmd(
        func=my_command,
        name="mycommand",
        desc="Does something useful",
        options=[
            CommandArg(name="option1", desc="A string", type=CommandArg.Types.STRING, required=True),
            CommandArg(name="option2", desc="A number", type=CommandArg.Types.INTEGER, required=False)
        ]
    )
```

### Custom ID Parsing

Button `custom_id` values encode state as delimited strings for routing:
```python
# In ButtonManager.button_flow_tree:
if QueueManager.join_queue_custom_id in interaction.custom_id:
    queue_id = interaction.custom_id.split("#")[1]  # Extract queue_id from "queue#join#queueid"
    # Handle join
```

## Development Workflow

### Adding a New Command

1. Create file in `commands/` directory (e.g., `commands/mycommand.py`)
2. Define command handler function with signature:
   ```python
   def my_command(interaction: Interaction, **args) -> None:
       interaction.defer(ephemeral=False)  # Or ephemeral=True for private responses
       # ... do work ...
       interaction.send_response(embeds=[...], ephemeral=False)
   ```
3. Define `setup(registry: CommandRegistry)` function to register it
4. Push to `dev` branch to trigger deployment

### Adding a Button Handler

1. Define handler in `core/ButtonManager.py`:
   ```python
   def my_button_handler(guild_id: str, inter: Interaction):
       # Extract data from inter.custom_id
       inter.send_response(embeds=[...], ephemeral=True)
   ```
2. Add routing check in `button_flow_tree()`:
   ```python
   if MyManager.my_custom_id in interaction.custom_id:
       my_button_handler(interaction.guild_id, interaction)
   ```
3. Include button in Embedding's Components when rendering that view

### Querying Data (DAOs)

```python
from dao.PlayerDao import PlayerDao
from dao.QueueDao import QueueDao

player_dao = PlayerDao()
queue_dao = QueueDao()

# Get player
player = player_dao.get_player(guild_id="123456", player_id="user789")

# Update player
player_dao.update_player(guild_id="123456", player_id="user789", skill=2000)

# Get queue
queue = queue_dao.get_queue(guild_id="123456", queue_id="main")

# Add to queue
queue_dao.add_player_to_queue(guild_id="123456", queue_id="main", player_id="user789")
```

## Build & Deployment

### Build Process (GitHub Actions)

**Trigger:** Push to `dev` branch or manual workflow dispatch

**Steps:**
1. **Dependency Upload** (`upload_deps` job):
   - Install requirements.txt in Docker (Python 3.9 SDK image)
   - Run `CommandRegistryPickler` to serialize all commands (discovers `commands/` dir)
   - Package as Lambda layer (strips boto3/botocore to avoid Lambda conflicts)
   - Upload to S3, create Lambda layer, attach to function

2. **Source Upload** (`upload_source` job):
   - Zip entire repository
   - Upload to Lambda function via API
   - Set environment variables (APP_ID, PUBLIC_KEY, BOT_TOKEN, etc.)

### Local Testing

No local test runner configured. Testing is done via:
- Discord test server after deployment
- Manual command/button invocation
- CloudWatch logs from Lambda

### Environment Variables

Required secrets in GitHub (Settings → Secrets):
- `APP_ID`: Discord application ID
- `PUBLIC_KEY`: Discord public key (for signature verification)
- `BOT_TOKEN`: Discord bot token (for registering commands)
- `AWS_ACCESS_KEY_ID`: AWS credentials
- `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `BOT_ENV`: Environment label (e.g., "DEV", "PROD")

Additional secrets can be added:
1. Add to GitHub repository secrets
2. Add to `.github/workflows/awsLambda.yml` in the `environment:` section
3. Access via `os.environ.get("VAR_NAME")` in code

## File Reference

| File | Purpose |
|------|---------|
| `lambda_function.py` | AWS Lambda entry point; signature verification; interaction routing |
| `commands/*.py` | Discord slash command implementations |
| `core/QueueManager.py` | Queue management, team assignment, match state transitions |
| `core/LeaderboardManager.py` | Ranked leaderboard generation, pagination, button navigation |
| `core/ButtonManager.py` | Routes button clicks to handler functions |
| `dao/*.py` | DynamoDB operations for queues, players, leaderboards |
| `discord_lambda/Interaction.py` | Parses Discord interactions, provides response API |
| `discord_lambda/Embedding.py` | Rich message embed builder (Discord embeds) |
| `discord_lambda/Components.py` | Button/action row builder |
| `discord_lambda/CommandRegistry.py` | Discovers commands in `commands/` dir, syncs with Discord API |
| `discord_lambda/CommandRegistryPickler.py` | Serializes CommandRegistry for Lambda layer |
| `.github/workflows/awsLambda.yml` | CI/CD pipeline for dev deployments |
| `.github/workflows/awsLambdaProd.yml` | CI/CD pipeline for prod deployments (to `main` branch) |
| `requirements.txt` | Python dependencies (pynacl, boto3, requests, trueskill, etc.) |

## Common Commands

### Deploy to Dev
```bash
git push origin dev
# GitHub Actions auto-triggers awsLambda.yml
# Monitor progress in Actions tab
```

### Deploy to Prod
```bash
git push origin main
# GitHub Actions auto-triggers awsLambdaProd.yml
```

### Manual Dependency Layer Update
If you add to `requirements.txt`:
```bash
# GitHub Actions will auto-rebuild on push to dev
# Or manually trigger from Actions → Deploy to Lambda → Run workflow
```

### Check Lambda Logs
CloudWatch Logs: AWS Console → CloudWatch → Logs → `/aws/lambda/DiscordApiLambda`

## Code Style & Patterns

### Immutability in Embeddings & Components

The framework enforces immutability by concatenating lists instead of mutating:
```python
# DO: Immutable pattern (concatenate)
self.fields = self.fields + [{"name": name, "value": value, "inline": inline}]

# DON'T: Mutate in place
self.fields.append({"name": name, "value": value, "inline": inline})
```

### Deferred Responses

For commands that take > 3 seconds:
```python
interaction.defer(ephemeral=False)  # Tell Discord "I'm working on it"
# ... perform work (up to 15 min) ...
interaction.send_response(embeds=[...], ephemeral=False)  # Send result
```

### Error Handling

The Lambda handler wraps command execution:
```python
try:
    func(interaction, **args)
except Exception as e:
    interaction.send_response(
        embeds=[Embedding(":x: Error", f"The request could not be completed:\n`{e}`", color=0xFF0000)],
        ephemeral=True
    )
    raise e  # Log to CloudWatch
```

## Useful Patterns

### Pagination with Buttons

LeaderboardManager uses custom IDs with page numbers:
```python
custom_id = f"leaderboard_page#{page}"  # Button ID encodes page

# In ButtonManager handler:
page = int(inter.custom_id.split("#")[1])  # Extract page
embed, component = LeaderboardManager.build_leaderboard_page(guild_id, page)
inter.send_response(embeds=[embed], components=[component])
```

### Team Assignment

QueueManager handles team selection after captain picks:
```python
# Auto-pick: Randomly assigns remaining players
# Manual pick: Captain clicks player buttons to draft teams
# Match state transitions: Waiting → Picking → Playing → Finished
```

### ELO/Skill Ratings

Uses `trueskill` package:
```python
from trueskill import Rating, rate

# Players have skill ratings
player_a_skill = Rating(mu=2000, sigma=100)
player_b_skill = Rating(mu=2100, sigma=80)

# After match, update ratings
new_ratings = rate([player_a_skill, player_b_skill], ranks=[0, 1])  # 0=winner
```

## Testing Notes

- No unit tests or pytest setup currently
- Testing is manual via Discord bot in test server
- CloudWatch logs provide debugging (see lambda_function.py print statements)
- TrueSkill and queue logic can be unit tested if framework is added

## Known Limitations & Considerations

1. **No Local Development**: Commands must be deployed to AWS to test. Suggested: add pytest setup for unit testing DAOs and managers.
2. **Button State**: Custom IDs encode all state (guild_id, queue_id, page, etc.) since Lambda is stateless.
3. **15-Minute Timeout**: Deferred interactions must respond within 15 minutes. Long operations may timeout.
4. **CommandRegistry Pickling**: The registry is pickled once during layer creation and loaded from `/opt/CommandRegistry.pickle` at runtime. Ensures commands don't re-register on every invocation.

## Additional Resources

- Discord API Docs: https://discord.com/developers/docs
- TrueSkill: https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/
- AWS Lambda: https://docs.aws.amazon.com/lambda/
- README.md: Full setup guide and class reference
