# main.py
#
#

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from tools import read_file, get_project_structure, write_test_file, run_pytest
from pathlib import Path
import sys

load_dotenv()

class TestResponse(BaseModel):
    path: str = Field(description="Relative path where the test file should be written")
    content: str = Field(description="Full contents of the Playwright test file")
    overwrite: bool = Field(description="Whether to overwrite an existing file")

llm = ChatOpenAI(model = "gpt-5.4-mini")

SYSTEM_PROMPT = """
            You are a QA engineer generating Playwright tests for a web application.

            CRITICAL: Tests must be written in Python using pytest-playwright syntax, NOT JavaScript.
            - Filename must end in .py (e.g. "test_pico_folio.py")
            - Use `def test_something(page):` function syntax, not `test('...', async ({ page }) => {...})`
            - Use the sync API: `page.goto(...)`, `expect(page.get_by_role(...)).to_be_visible()`
            - Import via: `from playwright.sync_api import Page, expect`
            - Do NOT use `import { test, expect } from '@playwright/test'` — that is JavaScript syntax and will not run.

            Follow this exact sequence:
            1. Call get_project_structure once to understand the project.
            2. Call read_file on only the files relevant to testable user flows.
            3. Write ONE test file covering the main flows using write_test_file.
            4. Call run_pytest on that file.
            5. If it fails, fix the SAME file (overwrite=True) — do not create new files.
            6. Repeat steps 4-5 at most twice more, then stop regardless of outcome and report status.

            Do not write more than one test file unless the project clearly has multiple
            distinct, unrelated features that each need their own file.

            You have a strict budget: at most 3 file writes and 3 test runs total.  
            """

structure_limiter = ToolCallLimitMiddleware(tool_name="get_project_structure", run_limit=1, exit_behavior="end")
global_limiter = ToolCallLimitMiddleware(run_limit=12, exit_behavior="continue")

agent = create_agent(
    model=llm, 
    system_prompt=SYSTEM_PROMPT,
    tools=[read_file, get_project_structure, write_test_file, run_pytest],
    middleware=[structure_limiter, global_limiter], 
    response_format=ToolStrategy(TestResponse)
)

path_input = input(" Provide the path to the project's directory: ")
target_url = input(" Provide the target URL")

project_path = Path(path_input)
if not project_path.exists():
    print(f"Warning: {project_path} does not exist.")
    sys.exit()

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": f"Generate Playwright tests for {target_url}. The project structure is at {project_path}"}]},
    config={"recursion_limit": 60},
    stream_mode="values",
):
    chunk["messages"][-1].pretty_print()

# raw_response = agent.invoke({"messages": [{"role": "user", "content": f"Generate Playwright tests for {target_url}. The project structure is at {project_path}"}]}, config={"recursion_limit": 35},)

# structured = raw_response.get("structured_response")
# if structured:
#     print(structured)
# else:
#     print("Agent stopped early (likely hit a tool call limit) before producing structured output.")
#     print("Last message:")
#     raw_response["messages"][-1].pretty_print()
