# main.py
#
#

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.messages import HumanMessage
from tools import read_file, get_project_structure, write_test_file, run_pytest
from pathlib import Path
import sys

load_dotenv()

class DependencyList(BaseModel):
    files: list[str] = Field(description="Relative project files needed to understand this page.")

class PlaywrightTest(BaseModel):
    filename:str
    content:str

llm = ChatOpenAI(model = "gpt-5.4-mini", temperature=0)

structure_limiter = ToolCallLimitMiddleware(tool_name="get_project_structure", run_limit=1, exit_behavior="end")
global_limiter = ToolCallLimitMiddleware(run_limit=12, exit_behavior="continue")

SYSTEM_PROMPT = """
            You are a QA engineer generating Playwright tests for a web application.

            CRITICAL: Tests must be written in Python using pytest-playwright syntax, NOT JavaScript.
            - Filename must end in .py (e.g. "test_pico_folio.py")
            - Use `def test_something(page):` function syntax, not `test('...', async ({ page }) => {...})`
            - Use the sync API: `page.goto(...)`, `expect(page.get_by_role(...)).to_be_visible()`
            - Import via: `from playwright.sync_api import Page, expect`
            - Do NOT use `import { test, expect } from '@playwright/test'` — that is JavaScript syntax and will not run.

            Rules:
            - Never call the same tool twice with identical arguments.
            - Reuse previous tool results instead of calling the tool again.
            - Only rerun pytest after modifying the test file.
            - Never rerun pytest if the file has not changed.
            - If a tool has already produced the needed information, continue reasoning without another call.

            Do not write more than one test file unless the project clearly has multiple
            distinct, unrelated features that each need their own file.
  
            """

page = Path(input( "What page would you like to make tests for?: ").strip().strip('"'))
project_path = Path(input(" Provide the path to the project's directory: ").strip().strip('"'))
target_url = input(" Provide the target URL").strip()

if not project_path.exists():
    print(f"Warning: {project_path} does not exist.")
    sys.exit()

structure = get_project_structure.invoke({"path": str(project_path)})
response = llm.with_structured_output(DependencyList).invoke([HumanMessage(content=f"""
        Project structure: {structure}. Target page: {page}. 
        Return ONLY the project files required to understand the user-facing behavior of this page. 
        Include the page itself.
        """)])
files = response.files

source = []
for file in files:
    text = read_file.invoke({"path": file, "project_root": str(project_path)})
    source.append(f"FILE: {file}  {text}")
project_context = "\n\n".join(source)



agent = create_agent(
    model=llm, 
    system_prompt=SYSTEM_PROMPT,
    tools=[read_file, get_project_structure, write_test_file, run_pytest],
    middleware=[structure_limiter, global_limiter] 
    # response_format=ToolStrategy(TestResponse)
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": f"Generate Playwright tests for {target_url}. The project structure is at {project_path}"}]},
    config={"recursion_limit": 15},
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
