# main.py
#
#

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
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


test = llm.with_structured_output(PlaywrightTest).invoke([HumanMessage(content=f"""
        Generate ONE Playwright pytest test
        Target URL: {target_url}
        Project files: {project_context}
        Requirements: 
            - Python
            - pytest-playwright
            - sync API
            - Cover primary user flows
""")])

write_test_file.invoke({"filename": test.filename, "content": test.content})

MAX_ATTEMPTS = 3
current_content = test.content

for attempt in range(MAX_ATTEMPTS):
    result = run_pytest.invoke({"filename": test.filename})

    if result.startswith("PASSED"):
        print("Success!")
        break

    print("Test Failed. Retrying...")
    fix = llm.with_structured_output(PlaywrightTest).invoke([HumanMessage(content=f"""
        The following Playwright test failed. Current test: {current_content}. Pytest output: {result}
        Return the corrected test. Keep the same filename.
    """)])

    current_content = fix.content

    write_test_file.invoke({"filename": fix.filename, "content": current_content, "overwrite": True})


