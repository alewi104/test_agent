# DocMaster

An agentic tool that reads a target project's source files and generates [Playwright](https://playwright.dev/) end-to-end tests for it. Point it at a project directory and a live URL, and the agent explores the codebase, writes test files, runs them, and iterates on failures.

## How it works

DocMaster uses a [LangChain](https://www.langchain.com/) tool-calling agent (built on `create_agent`) backed by `gpt-5.4-mini`. Given a project path and a target URL, the agent:

1. Explores the target project's directory structure
2. Reads relevant source files to understand what's testable
3. Writes Playwright test files to a sandboxed local output directory
4. Runs the generated tests via `pytest`
5. Reads failures and revises tests until they pass (or it runs out of attempts)

Generated tests are written locally to `tests_output/` — the agent never modifies the target project itself. Once you're happy with the output, copy the test files into your target project manually.

## Features

- **Read-only project analysis** — inspects the target project without ever writing to it
- **Sandboxed test generation** — all writes are constrained to a local `tests_output/` directory, with path-traversal protection
- **Self-correcting test loop** — runs generated tests and feeds failures back to the model
- **Structured output** — test metadata is returned as a validated Pydantic model (`TestResponse`)

## Requirements

- Python 3.10+
- An OpenAI API key with access to `gpt-5.4-mini`

## Installation

```bash
git clone <your-repo-url>
cd DocMaster
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
playwright install
```

Create a `.env` file in the project root with your OpenAI API key:

```
OPENAI_API_KEY=your-key-here
```

## Usage

Run the agent from the project root:

```bash
python main.py
```

You'll be prompted for:

- **Project directory path** — the local path to the project you want tests generated for
- **Target URL** — the live URL of the running application, used for `page.goto(...)` calls in generated tests

Generated test files land in `tests_output/` in the DocMaster directory. From there, run them directly:

```bash
pytest tests_output/ -v
```

Or copy them into your target project's own test suite once you've reviewed them.

## Project structure

```
test_agent/
  main.py            # Entry point — collects input, invokes the agent
  tools.py            # Agent tools: read_file, get_project_structure, write_test_file, run_pytest
  tests_output/        # Sandboxed output directory for generated tests
  .env                 # OpenAI API key (not committed)
  requirements.txt
```

## Tools available to the agent

| Tool | Purpose |
|---|---|
| `read_file` | Reads the contents of a file in the target project |
| `get_project_structure` | Returns a directory tree of the target project, ignoring common noise (`node_modules`, `.git`, etc.) |
| `write_test_file` | Writes a generated Playwright test into the sandboxed `tests_output/` directory |
| `run_pytest` | Runs a generated test via `pytest` and returns pass/fail output |

## Notes

- If you hit an `openai.RateLimitError`, you've exceeded your account's tokens-per-minute limit. The agent's request/retry behavior can be adjusted in `main.py`; consider trimming how much file content and directory depth is fed into context if this happens frequently.
- This project is under active development — tool coverage and agent reliability will continue to expand.

## License
