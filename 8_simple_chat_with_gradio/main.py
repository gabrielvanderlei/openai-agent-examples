import asyncio
import json
import random
import gradio as gr
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Callable
import httpx
from dotenv import load_dotenv
import os
import inspect
import functools

from agents import Agent, RunContextWrapper, Runner, function_tool, set_default_openai_key

# Load environment variables
load_dotenv()

# Set the default OpenAI API key using the function from the agents module
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    set_default_openai_key(openai_api_key, use_for_tracing=True)
else:
    print("Warning: OPENAI_API_KEY environment variable is not set")

@dataclass
class ChatContext:
    user_id: str
    username: str
    chat_history: List[Dict[str, str]] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        """Add a message to the chat history"""
        self.chat_history.append({"role": role, "content": content})
    
    def get_history_text(self, max_messages: int = 5) -> str:
        """Convert recent history to formatted text for inclusion in instructions"""
        if not self.chat_history:
            return ""
        
        history_text = "\nCHAT HISTORY:\n"
        for entry in self.chat_history[-max_messages:]:
            role_display = "User" if entry["role"] == "user" else "System"
            history_text += f"{role_display}: {entry['content']}\n"
        
        return history_text

@dataclass
class APIConfig:
    """Configuration for an API endpoint"""
    name: str
    description: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0
    error_message: str = "Sorry, I couldn't access the API at the moment."

# Create some standard built-in tools

@function_tool
async def get_time(wrapper: RunContextWrapper[ChatContext], timezone: str = None) -> str:
    """Get the current time in a specific timezone"""
    current_time = datetime.utcnow()
    timezone_info = f" in {timezone}" if timezone else " (UTC)"
    return f"Current time{timezone_info} for {wrapper.context.username}: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"

@function_tool
async def get_weather(wrapper: RunContextWrapper[ChatContext], city: str) -> str:
    """Get the current weather for a city"""
    async with httpx.AsyncClient() as client:
        try:
            # Use weatherapi.com's public endpoint
            response = await client.get(
                f"https://wttr.in/{city}?format=j1",
                timeout=10.0
            )
            
            weather_data = response.json()
            current = weather_data.get("current_condition", [{}])[0]
            location = weather_data.get("nearest_area", [{}])[0]
            
            location_name = location.get("areaName", [{}])[0].get("value", city)
            country = location.get("country", [{}])[0].get("value", "")
            
            temp_c = current.get("temp_C", "N/A")
            temp_f = current.get("temp_F", "N/A")
            condition = current.get("weatherDesc", [{}])[0].get("value", "Unknown")
            humidity = current.get("humidity", "N/A")
            
            return f"Current weather in {location_name}, {country} for {wrapper.context.username}:\n" \
                   f"Temperature: {temp_c}°C / {temp_f}°F\n" \
                   f"Condition: {condition}\n" \
                   f"Humidity: {humidity}%"
        except Exception as e:
            # If the API call fails, return a message about the issue
            return f"Sorry {wrapper.context.username}, I couldn't retrieve the weather for {city} at the moment. Error: {str(e)}"

@function_tool
async def get_joke(wrapper: RunContextWrapper[ChatContext]) -> str:
    """Get a random joke"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://official-joke-api.appspot.com/random_joke",
                timeout=10.0
            )
            joke_data = response.json()
            
            return f"Here's a joke for {wrapper.context.username}:\n\n{joke_data['setup']}\n{joke_data['punchline']}"
        except Exception as e:
            # Fallback jokes in case the API fails
            fallback_jokes = [
                {"setup": "Why don't scientists trust atoms?", "punchline": "Because they make up everything!"},
                {"setup": "Why did the scarecrow win an award?", "punchline": "Because he was outstanding in his field!"},
                {"setup": "Why couldn't the bicycle stand up by itself?", "punchline": "It was two tired!"},
            ]
            joke = random.choice(fallback_jokes)
            return f"Here's a joke for {wrapper.context.username}:\n\n{joke['setup']}\n{joke['punchline']}"

@function_tool
async def get_bitcoin_price(wrapper: RunContextWrapper[ChatContext]) -> str:
    """Get the current Bitcoin price in USD"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=10.0
            )
            price_data = response.json()
            
            if "bitcoin" in price_data and "usd" in price_data["bitcoin"]:
                price = price_data["bitcoin"]["usd"]
                return f"Current Bitcoin price for {wrapper.context.username}: ${price:,}"
            else:
                return f"Sorry {wrapper.context.username}, I couldn't retrieve the Bitcoin price at the moment."
        except Exception as e:
            return f"Sorry {wrapper.context.username}, I couldn't access the cryptocurrency API at the moment. Error: {str(e)}"

# Registry for custom API tools
custom_api_tools = {}

@function_tool
async def get_cat_fact(wrapper: RunContextWrapper[ChatContext]) -> str:
    """Get a random cat fact"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://catfact.ninja/fact", 
                timeout=10.0
            )
            fact_data = response.json()
            
            return f"Cat Fact: {fact_data['fact']}"
        except Exception as e:
            return f"Sorry {wrapper.context.username}, I couldn't retrieve a cat fact at the moment. Error: {str(e)}"

# Function to add the tool to the registry
def register_cat_fact_tool():
    custom_api_tools["cat_fact"] = get_cat_fact
    return get_cat_fact

# Function to register custom API tools from JSON config
def register_api_tool_from_config(config_json):
    """
    Register a new API tool from a JSON configuration
    Returns a message indicating success or failure
    """
    try:
        # Parse the JSON config
        config = json.loads(config_json)
        
        # Validate required fields
        if "name" not in config or "url" not in config:
            return "Error: API configuration must include 'name' and 'url' fields"
        
        # For now, we'll only support predefined tools
        tool_type = config.get("type", "").lower()
        
        if tool_type == "cat_fact":
            tool = register_cat_fact_tool()
            return f"Successfully registered '{config['name']}' API tool"
        else:
            return f"Error: Unsupported API tool type '{tool_type}'. Currently supported types: cat_fact"
    
    except json.JSONDecodeError:
        return "Error: Invalid JSON configuration"
    except Exception as e:
        return f"Error registering API tool: {str(e)}"

async def process_message(ctx, message, triage_agent):
    # Add user message to context
    ctx.add_message("user", message)
    
    # Update instructions with current history
    history_text = ctx.get_history_text()
    current_instructions = triage_agent.instructions.replace("{{CHAT_HISTORY}}", history_text)
    triage_agent.instructions = current_instructions
    
    # Process the message with context
    result = await Runner.run(
        starting_agent=triage_agent,
        input=message,
        context=ctx,
    )
    
    response = result.final_output
    
    # Add system response to context
    ctx.add_message("system", response)
    
    # Reset template placeholder for next iteration
    triage_agent.instructions = triage_agent.instructions.replace(history_text, "{{CHAT_HISTORY}}")
    
    return response

def create_agents(model_name="o3-mini"):
    """Create the agent system with all available tools"""
    # Create specialized agents
    weather_agent = Agent[ChatContext](
        name="Weather Agent",
        instructions="Provide weather information for cities around the world. Always require a city name.",
        model=model_name,
        tools=[get_weather],
    )
    
    joke_agent = Agent[ChatContext](
        name="Joke Agent",
        instructions="Tell jokes when requested by the user.",
        model=model_name,
        tools=[get_joke],
    )
    
    bitcoin_agent = Agent[ChatContext](
        name="Bitcoin Agent",
        instructions="Provide the current Bitcoin price when requested.",
        model=model_name,
        tools=[get_bitcoin_price],
    )
    
    time_agent = Agent[ChatContext](
        name="Time Agent",
        instructions="Provide current time information.",
        model=model_name,
        tools=[get_time],
    )
    
    # List of all specialized agents
    specialized_agents = [weather_agent, joke_agent, bitcoin_agent, time_agent]
    
    # Add any custom API agents
    for name, tool in custom_api_tools.items():
        if name == "cat_fact":
            cat_fact_agent = Agent[ChatContext](
                name="Cat Fact Agent",
                instructions="Provide random facts about cats when requested.",
                model=model_name,
                tools=[tool],
            )
            specialized_agents.append(cat_fact_agent)
    
    # Build the instruction text for available agents
    agent_descriptions = []
    agent_descriptions.append("- Weather Agent: Use for questions about weather in different cities. Always require a city name.")
    agent_descriptions.append("- Joke Agent: Use for requests for jokes or humor.")
    agent_descriptions.append("- Bitcoin Agent: Use for questions about Bitcoin prices.")
    agent_descriptions.append("- Time Agent: Use for questions about the current time.")
    
    # Add descriptions for custom agents
    if "cat_fact" in custom_api_tools:
        agent_descriptions.append("- Cat Fact Agent: Use for requests about cat facts.")
    
    agent_instructions = "\nAVAILABLE AGENTS:\n" + "\n".join(agent_descriptions)
    
    # Create the triage agent
    triage_agent = Agent[ChatContext](
        name="Triage Agent",
        instructions=f"""
        You determine which agent to use based on the user's history and current request.
        
        USER PROFILE:
        - You're talking to a user who might ask about various topics
        - Try to route requests to the appropriate specialized agent
        {agent_instructions}
        
        Respond directly for general questions that don't fit these categories.
        
        {{CHAT_HISTORY}}
        """,
        handoffs=specialized_agents,
        model=model_name,
    )
    
    return triage_agent

def build_gradio_interface():
    """Build and launch the Gradio interface"""
    # Create the agents
    triage_agent = create_agents()
    
    # Create a context for the chat
    ctx = ChatContext(user_id="gradio_user", username="User")
    
    # Message handler for processing messages
    async def message_handler(message, history):
        if message.startswith("!register "):
            # Command to register a new API tool
            config_json = message[10:].strip()
            result = register_api_tool_from_config(config_json)
            
            # Recreate the triage agent with new tools
            nonlocal triage_agent
            triage_agent = create_agents()
            
            return result
        else:
            # Regular chat message
            response = await process_message(ctx, message, triage_agent)
            return response
    
    # Gradio interface wrapper function
    async def greet(message, history):
        return await message_handler(message, history)
    
    # Create the Gradio interface
    demo = gr.ChatInterface(
        fn=greet,
        title="AI Agent Chat with API Tools",
        description="""
        Chat with an AI agent that can access various APIs to help you.
        
        Available commands:
        - !register {json_config}: Register a new API tool with JSON configuration
        
        Available APIs:
        - Weather: Ask about the weather in any city
        - Jokes: Ask for a joke
        - Bitcoin Price: Ask for the current Bitcoin price
        - Time: Ask for the current time
        
        You can register new API tools, such as:
        - Cat Facts: Get random facts about cats
        """,
        examples=[
            "What's the weather in London?",
            "Tell me a joke",
            "What's the Bitcoin price?",
            "What time is it?",
            '!register {"name": "Cat Facts API", "type": "cat_fact"}'
        ],
        cache_examples=False,
    )
    
    return demo

def main():
    """Main function to run the Gradio interface"""
    demo = build_gradio_interface()
    demo.launch()

if __name__ == "__main__":
    main()