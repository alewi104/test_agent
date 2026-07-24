# main.py
#
#

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from tools import read_file, get_project_structure, write_test_file, run_pytest

load_dotenv()

class TestResponse(BaseModel):
    path: str = Field(description="Relative path where the test file should be written")
    content: str = Field(description="Full contents of the Playwright test file")
    overwrite: bool = Field(description="Whether to overwrite an existing file")

llm = ChatOpenAI(model = "gpt-5.4-mini")

SYSTEM_PROMPT = """
            You are a quality assurance engineer that will help to generate Playwright tests for web applications.
            Use the necessary tools to complete yout task.   
            """


agent = create_agent(
    model=llm, 
    system_prompt=SYSTEM_PROMPT,
    tools=[read_file, get_project_structure, write_test_file, run_pytest], 
    response_format=ToolStrategy(TestResponse)
)

raw_response = agent.invoke({"messages": [{"role": "user", "content": "Generate Playwright tests for https://alewi104.github.io/pico-folio/." r"The project structure is at 'C:\Users\Ahlaireah\Documents\Documents\Personal Projects\PortfolioSite\Pico-8-Portfolio-Site'"}]})
print(raw_response["structured_response"])
