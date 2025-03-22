import asyncio
from agents import Agent, ModelSettings, function_tool, Runner

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

@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Haiku agent",
    instructions="Always respond in haiku form",
    tools=[get_weather],
)

async def main():
    result = await Runner.run(agent, input="Return weather in San Francisco.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())