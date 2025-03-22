import asyncio
from dataclasses import dataclass

from agents import Agent, RunContextWrapper, Runner, function_tool

from agents import set_default_openai_key
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set the default OpenAI API key using the function from the agents module
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    set_default_openai_key(openai_api_key, use_for_tracing=True)
else:
    print("Warning: OPENAI_API_KEY environment variable is not set")
    
@dataclass
class UserInfo:  
    name: str
    uid: int
    age: int

@function_tool
async def fetch_user_age(wrapper: RunContextWrapper[UserInfo]) -> str:  
    return f"User {wrapper.context.name} is {wrapper.context.age} years old"

async def main():
    user_info = UserInfo(name="John", age=32, uid=123)  

    agent = Agent[UserInfo](  
        name="Assistant",
        tools=[fetch_user_age],
    )

    result = await Runner.run(
        starting_agent=agent,
        input="What is the age of the user?",
        context=user_info,
    )

    print(result.final_output)  
    # The user John is 47 years old.

if __name__ == "__main__":
    asyncio.run(main())