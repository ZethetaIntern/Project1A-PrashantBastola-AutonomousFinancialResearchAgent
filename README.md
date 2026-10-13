# Autonomous Financial Research Agent

A Python-based autonomous financial research agent designed to support financial analysis through registered tools, configurable LLM providers, retry handling, token-usage tracking, and structured logging.

## Features

- **Tool registry:** Registered financial research tools with argument validation and structured error handling.
- **Multiple LLM providers:** Provider-independent integration through LiteLLM, supporting OpenAI, Anthropic, Groq, Gemini, OpenRouter, and local Ollama.
- **Retry handling:** Exponential backoff for selected temporary provider and network errors.
- **Token tracking:** Tracks input tokens, output tokens, total tokens, and provider-reported cost metadata when available.
- **Configuration management:** Loads application settings and credentials from environment variables.
- **Logging:** Outputs timestamped logs to the terminal and a rotating log file.
- **Automated tests:** Uses pytest to validate client behavior and tool functionality.

## Requirements

- Python 3.13 or a compatible Python version supported by the installed dependencies.
- pip
- An API key for the hosted LLM provider you choose, or a running local Ollama installation.
- Git (optional, for cloning the repository).

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ZethetaIntern/Project1A-PrashantBastola-AutonomousFinancialResearchAgent.git
cd Project1A-PrashantBastola-AutonomousFinancialResearchAgent
```

If you already have the repository locally, open its directory instead.

### 2. Create a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` and configure the provider you want to use. For example, for Groq:

```dotenv
LLM_PROVIDER=groq
LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=your_groq_api_key
```

Replace the example key with your own key. Check your provider's current documentation for available models and access limits.

Other supported provider choices are:

| Provider | `LLM_PROVIDER` value | Credential or requirement |
|---|---|---|
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| Groq | `groq` | `GROQ_API_KEY` |
| Gemini | `gemini` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter` | `OPENROUTER_API_KEY` |
| Ollama | `ollama` | Local Ollama service and compatible model |

For Ollama, set `OLLAMA_BASE_URL` to the address of your local service and use the model identifier expected by your Ollama/LiteLLM setup.

Keep real API keys in `.env`. Do not commit `.env` or put secrets in source code. The repository's `.env.example` should contain placeholders only.

## Configuration options

The application reads configuration from `.env` and environment variables.

| Setting | Purpose |
|---|---|
| `APP_ENV` | Application environment |
| `LOG_LEVEL` | Logging threshold, such as `INFO` or `DEBUG` |
| `LLM_PROVIDER` | Selected LLM provider |
| `LLM_MODEL` | Provider-compatible model identifier |
| `VECTOR_DB_PROVIDER` | Vector database selection |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB persistence directory |
| `MAX_TOOL_CALLS` | Maximum configured tool-call limit |
| `TOOL_TIMEOUT_SECONDS` | Configured tool/request timeout |
| `MAX_RETRIES` | Number of additional attempts after a retryable failure |

Additional environment variables are available for provider credentials and external financial or web data services.

## Validate the configuration

Run:

```bash
python -c "from config import settings; settings.validate_settings(); print('Configuration valid')"
```

This checks supported provider settings and configured limits. It does not make a provider API request.

## Run tests

Run the complete test suite:

```bash
python -m pytest -v
```

Run only the LLM client tests:

```bash
python -m pytest tests/test_llm_client.py -v
```

The LLM client tests use mocked responses, so they do not require a live provider API key or consume provider tokens.

## Logging

Importing the LLM client initializes the centralized logging configuration.

Logs are written to:

- Terminal output
- `logs/agent.log`

The log file rotates at 5 MB and retains up to three backup files.

To inspect recent log entries:

```bash
tail -20 logs/agent.log
```

Log entries can include request metadata, retry attempts, token usage, and errors. Avoid logging API keys, credentials, or sensitive financial information.

## Project structure

```text
.
├── agent/                  # Agent implementation
├── config/
│   ├── __init__.py
│   ├── settings.py         # Environment-based settings
│   └── logging_config.py   # Centralized logging
├── docs/                   # Project documentation
├── llm/
│   ├── __init__.py
│   └── client.py           # LiteLLM client, retries, and usage tracking
├── memory/                 # Agent memory components
├── synthesis/              # Research synthesis components
├── tests/
│   ├── test_llm_client.py
│   ├── test_smoke.py
│   └── test_tools.py
├── tools/                  # Registered research tools
├── .env.example            # Example configuration
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Troubleshooting

**Missing API key**

Set the key corresponding to your selected hosted provider in `.env`. Keep the key private.

**Unsupported provider**

Check that `LLM_PROVIDER` is one of the supported values listed above.

**Model unavailable**

Check your provider's current model identifiers, account access, and usage limits. Model availability may change.

**Ollama connection failure**

Verify that Ollama is installed, running, and serving the selected model at the configured base URL.

**Dependency issues**

Activate the virtual environment and reinstall dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

**Test failures**

Run the relevant test with `-v` for detailed output, then inspect the associated source code and error message.

## Security

- Never commit `.env` or real API credentials.
- Use `.env.example` for placeholder configuration only.
- Review logs before sharing them publicly.
- Treat financial research output as analytical assistance, not guaranteed financial advice.

## Project status

The configuration module, LiteLLM client, retry handling, token-usage tracking, centralized logging, and automated tests have been implemented and tested locally. Consult the latest test results and repository history when verifying the current state of the project.