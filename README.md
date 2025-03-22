# openai-agent-examples

This repository contains practical examples of how to use the OpenAI Agents library to create and orchestrate AI agents.

## Useful Documentation

- [Official OpenAI Agents Python Repository](https://github.com/openai/openai-agents-python)
- [OpenAI Platform Documentation](https://platform.openai.com/docs/guides/agents)
- [Library Documentation](https://openai.github.io/openai-agents-python/)

## Getting Started

### Installation

```bash
pip install openai-agents
```

### API Key Configuration

```bash
export OPENAI_API_KEY=sk-...
```

For easier environment variable management in more complex examples:

```bash
pip install python-dotenv
```

## Included Examples

### 1. Simple Agent (`simple_agent.py`)

This example shows how to create a basic agent with defined instructions:

```python
from agents import Agent

agent = Agent(
    name="Math Tutor",
    instructions="You provide help with math problems. Explain your reasoning at each step and include examples",
)
```

### 2. Handoffs Between Specialized Agents

Demonstrates how to create a triage system that routes questions to specialized agents:

```python
triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's homework question",
    handoffs=[history_tutor_agent, math_tutor_agent]
)
```

### 3. Input Guardrails (`1_simple_agent.py`)

Implements safety checks to validate user inputs:

```python
from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner
from pydantic import BaseModel
import asyncio

class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str

# Complete example in file 1_simple_agent.py
```

### 4. Python Functions as Tools (`2_function_tool.py`)

Shows how to turn Python functions into tools for agents:

```python
@function_tool  
async def fetch_weather(location: Location) -> str:
    """Fetch the weather for a given location.

    Args:
        location: The location to fetch the weather for.
    """
    # In real life, we'd fetch the weather from a weather API
    return "sunny"
```

### 5. Agents as Tools (`3_agent_as_function.py`)

Demonstrates how to use agents as tools for centralized orchestration:

```python
orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions=(
        "You are a translation agent. You use the tools given to you to translate."
        "If asked for multiple translations, you call the relevant tools."
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate the user's message to French",
        ),
    ],
)
```

### 6. Simple Tool (`4_simple_tool.py`)

A minimalist example of how to create a tool:

```python
from agents import Agent, ModelSettings, function_tool

@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny"

agent = Agent(
    name="Haiku agent",
    instructions="Always respond in haiku form",
    model="o3-mini",
    tools=[get_weather],
)
```

### 7. Local Context (`5_local_context.py`)

How to pass and use context in agents:

```python
@dataclass
class UserInfo:  
    name: str
    uid: int

@function_tool
async def fetch_user_age(wrapper: RunContextWrapper[UserInfo]) -> str:  
    return f"User {wrapper.context.name} is 47 years old"
```

### 8. Chat Management

Complete example of a chat system with history and multiple specialized agents:

```python
@dataclass
class ChatContext:
    user_id: str
    username: str
    chat_history: List[Dict[str, str]] = None
    
    # Methods for managing chat history
    # ...

# Specialized agents and triage system
# See complete code for more details
```

### 5_1 - voice example
- The voice example was added in a recent update.
- It need to be executed in an environment with audio support.
- And run: 

```sh
pip install openai-agents[voice] sounddevice
```

## How the System Works

In summary, OpenAI Agents works like a web system:
- Triage: Acts as a router that directs requests
- Handoffs: Represent the available routes
- Guardrails: Define the format and validation of requests
- Agents: Process specific requests
- User message: Represents the request itself

What still needs to be considered for a complete chat system:
- Management of user message history
- External tools for advanced processing

## Running the Examples

Each example can be run directly from the terminal:

```bash
python 1_simple_agent.py
python 2_function_tool.py
# etc.
```