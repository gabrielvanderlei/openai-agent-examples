import asyncio
import json
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
from dotenv import load_dotenv
import os

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
    chat_history: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.chat_history is None:
            self.chat_history = []
    
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

@function_tool
async def get_joke(wrapper: RunContextWrapper[ChatContext], topic: str = None) -> str:
    """Get a joke from a public API"""
    async with httpx.AsyncClient() as client:
        try:
            if topic:
                # Try to get a joke related to the topic (this endpoint doesn't support topics directly,
                # but we can use the search feature to find jokes that might be related)
                response = await client.get(
                    "https://official-joke-api.appspot.com/random_joke",
                    timeout=10.0
                )
                joke_data = response.json()
                
                # Format the joke
                return f"Here's a joke for {wrapper.context.username}:\n\n{joke_data['setup']}\n{joke_data['punchline']}"
            else:
                # Get a random joke
                response = await client.get(
                    "https://official-joke-api.appspot.com/random_joke",
                    timeout=10.0
                )
                joke_data = response.json()
                
                # Format the joke
                return f"Here's a random joke for {wrapper.context.username}:\n\n{joke_data['setup']}\n{joke_data['punchline']}"
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
async def get_btc_price(wrapper: RunContextWrapper[ChatContext]) -> str:
    """Get the current Bitcoin price from a public API"""
    async with httpx.AsyncClient() as client:
        try:
            # Use CoinGecko's public API
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
            # If the API call fails, return a message about the issue
            return f"Sorry {wrapper.context.username}, I couldn't access the cryptocurrency API at the moment. The service might be experiencing high traffic."

@function_tool
async def get_weather(wrapper: RunContextWrapper[ChatContext], city: str) -> str:
    """Get the current weather for a city from a public API"""
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
            return f"Sorry {wrapper.context.username}, I couldn't retrieve the weather for {city} at the moment."

@function_tool
async def get_time(wrapper: RunContextWrapper[ChatContext], timezone: str = None) -> str:
    """Get the current time in a specific timezone"""
    current_time = datetime.utcnow()
    timezone_info = f" in {timezone}" if timezone else " (UTC)"
    return f"Current time{timezone_info} for {wrapper.context.username}: {current_time.strftime('%Y-%m-%d %H:%M:%S')}"

@function_tool
async def search_news(wrapper: RunContextWrapper[ChatContext], query: str) -> str:
    """Search for news headlines (simulated)"""
    # This is a simulated function since most news APIs require authentication
    simulated_headlines = [
        f"New developments in {query} research announced today",
        f"Experts debate the future of {query} in global markets",
        f"Five things you need to know about {query} this week",
        f"How {query} is changing the landscape of its industry",
    ]
    
    return f"Here are some headlines about '{query}' for {wrapper.context.username}:\n\n" + "\n".join(
        f"- {headline}" for headline in simulated_headlines
    )

async def main():
    # Initialize chat context with default values (no API keys needed)
    user_id = "user123"
    username = "Guest"
    
    # Initialize chat context
    ctx = ChatContext(user_id=user_id, username=username)
    
    # Create agents with type annotation for context
    btc_agent = Agent[ChatContext](
        name="Bitcoin Agent",
        instructions="Provide the current Bitcoin price when requested",
        tools=[get_btc_price],
    )
    
    jokes_agent = Agent[ChatContext](
        name="Jokes Agent",
        instructions="Tell jokes about the topic requested by the user",
        tools=[get_joke],
    )
    
    weather_agent = Agent[ChatContext](
        name="Weather Agent",
        instructions="Provide weather information for cities around the world. Always require a city name.",
        tools=[get_weather],
    )
    
    time_agent = Agent[ChatContext](
        name="Time Agent",
        instructions="Provide current time information",
        tools=[get_time],
    )
    
    news_agent = Agent[ChatContext](
        name="News Agent",
        instructions="Search for and provide news headlines about specific topics",
        tools=[search_news],
    )
    
    # Create triage agent that will receive history directly in instructions
    triage_agent = Agent[ChatContext](
        name="Triage Agent",
        instructions="""
        You determine which agent to use based on the user's history and current request.
        
        USER PROFILE:
        - You're talking to a user who might ask about various topics
        - Try to route requests to the appropriate specialized agent
        
        AVAILABLE AGENTS:
        - Bitcoin Agent: Use for questions about Bitcoin prices and cryptocurrency
        - Jokes Agent: Use for requests for jokes or humor
        - Weather Agent: Use for questions about weather in different cities. Note that a city must be specified.
        - Time Agent: Use for questions about the current time
        - News Agent: Use for requests about news on specific topics
        
        Respond directly for general questions that don't fit these categories.
        
        {{CHAT_HISTORY}}
        """,
        handoffs=[btc_agent, jokes_agent, weather_agent, time_agent, news_agent],
    )
    
    print(f"Bot: Hello {username}! How can I help you today? I can tell you jokes, check Bitcoin prices, provide weather updates, tell you the time, or search for news.")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "bye", "quit"]:
            print("Bot: Goodbye! It was nice chatting with you.")
            break
        
        # Add user message to context
        ctx.add_message("user", user_input)
        
        # Update instructions with current history
        history_text = ctx.get_history_text()
        current_instructions = triage_agent.instructions.replace("{{CHAT_HISTORY}}", history_text)
        triage_agent.instructions = current_instructions
        
        # Process the message with context
        result = await Runner.run(
            starting_agent=triage_agent,
            input=user_input,
            context=ctx,
        )
        
        response = result.final_output
        print(f"Bot: {response}")
        
        # Add system response to context
        ctx.add_message("system", response)
        
        # Reset template placeholder for next iteration
        triage_agent.instructions = triage_agent.instructions.replace(history_text, "{{CHAT_HISTORY}}")

if __name__ == "__main__":
    asyncio.run(main())