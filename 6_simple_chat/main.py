import asyncio
import os
from dataclasses import dataclass
from typing import List, Dict, Any
from dotenv import load_dotenv

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
async def get_jokes(wrapper: RunContextWrapper[ChatContext], topic: str) -> str:
    """Get jokes based on the requested topic"""
    api_key = os.getenv("JOKES_API_KEY")
    return f"Here's a joke about {topic} for user {wrapper.context.username}... (API Key: {api_key[:5] if api_key else 'Not set'}...)"

@function_tool
async def get_btc_price(wrapper: RunContextWrapper[ChatContext]) -> str:
    """Get the current Bitcoin price"""
    api_key = os.getenv("BTC_API_KEY")
    return f"Current Bitcoin price for {wrapper.context.username}: $XX,XXX.XX (API Key: {api_key[:5] if api_key else 'Not set'}...)"

async def main():
    # Get user info from environment
    user_id = os.getenv("USER_ID", "default_id")
    username = os.getenv("USERNAME", "default_user")
    
    # Initialize chat context
    ctx = ChatContext(user_id=user_id, username=username)
    
    # Get model configuration from environment
    model_name = os.getenv("MODEL_NAME", "o3-mini")
    
    # Create agents with type annotation for context
    btc_agent = Agent[ChatContext](
        name="Bitcoin Agent",
        instructions="Provide the current Bitcoin price when requested",
        model=model_name,
        tools=[get_btc_price],
    )
    
    jokes_agent = Agent[ChatContext](
        name="Jokes Agent",
        instructions="Tell jokes about the topic requested by the user",
        model=model_name,
        tools=[get_jokes],
    )
    
    # Create triage agent that will receive history directly in instructions
    triage_agent = Agent[ChatContext](
        name="Triage Agent",
        instructions="""
        You determine which agent to use based on the user's history and current request.
        
        USER PROFILE:
        - The user has asked about Bitcoin twice in the last few days
        - The user usually asks for jokes on Fridays
        
        Use the Bitcoin agent for questions about cryptocurrencies and prices.
        Use the Jokes agent for humor or entertainment requests.
        Respond directly for general questions.
        
        {{CHAT_HISTORY}}
        """,
        handoffs=[btc_agent, jokes_agent],
    )
    
    print(f"Bot: Hello {username}! How can I help you today?")
    
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