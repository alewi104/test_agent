# main.py
#
#

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from tools import read_file, get_project_structure, write_test_file, run_pytest
from pathlib import Path
import sys

load_dotenv()
MAX_ITERATIONS = 8

class DependencyList(BaseModel):
    files: list[str] = Field(description="Relative project files needed to understand this page.")

class PlaywrightTest(BaseModel):
    filename:str
    content:str

llm = ChatOpenAI(model = "gpt-5.4-mini", temperature=0)

tools = [read_file, write_test_file, run_pytest]
tools_by_name = {t.name: t for t in tools}
llm_with_tools = llm.bind_tools(tools)


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
print(f"Identified {len(files)} relevant file(s): {files}")


system_prompt = f"""You are an expert Playwright test engineer. Your job is to generate
ONE Playwright pytest test (Python, pytest-playwright, sync API) covering the primary
user flows of a target page, get it passing, and stop.
 
Target URL: {target_url}
Target page: {page}
Project root: {project_path}
Files identified as likely relevant: {files}
 
You have three tools:
- read_file(path, project_root): read a project file. Use this to read the files listed
  above, and feel free to read additional files if you discover you need them (e.g. a
  config, a shared component, a selector you can't otherwise verify).
- write_test_file(filename, content, overwrite): write or overwrite the test file.
- run_pytest(filename): run the test file and see the result.
 
Process:
1. Read whatever files you need to understand the page's user-facing behavior.
2. Write the test.
3. Run it.
4. If it fails, read whatever you need to (re-check source, selectors, etc.) and fix it.
5. Repeat until it passes, or you've made a genuine best effort and can explain why it
   still fails.
 
When you are finished (test passes, or you've exhausted reasonable attempts), respond
with a final plain-text summary and DO NOT call any more tools. That is how the loop
knows you're done.
"""

messages = [HumanMessage(content=system_prompt), HumanMessage(content="Begin.")]

for i in range(MAX_ITERATIONS):
    ai_msg = llm_with_tools.invoke(messages)
    messages.append(ai_msg)
 
    if not ai_msg.tool_calls:
        print("\nAgent finished:")
        print(ai_msg.content)
        break
 
    for call in ai_msg.tool_calls:
        tool = tools_by_name.get(call["name"])
        if tool is None:
            result = f"ERROR: unknown tool '{call['name']}'"
        else:
            try:
                result = tool.invoke(call["args"])
            except Exception as e:
                result = f"ERROR running {call['name']}: {e}"
 
        print(f"[{i}] {call['name']}({call['args']}) -> {str(result)[:200]}")
        messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
else:
    print(f"\nStopped after reaching MAX_ITERATIONS={MAX_ITERATIONS} without the agent signaling completion.")


