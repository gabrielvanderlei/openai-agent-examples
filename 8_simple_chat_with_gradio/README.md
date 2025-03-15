# Gradio Chat with Dynamic API Tools

This application creates a chat interface using Gradio that allows users to interact with an AI assistant capable of using various API tools. The key feature is the ability to dynamically add new API configurations at runtime, allowing the system to extend its capabilities without modifying the code.

## Features

- Chat interface powered by Gradio
- Dynamic API tool configuration via JSON
- Multiple specialized agents for different tasks
- Triage agent that routes requests to the appropriate specialized agent
- Command system for adding new API tools at runtime

## Prerequisites

- Python 3.8+
- OpenAI API key (set in .env file or environment variables)
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository
2. Install the required packages:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your OpenAI API key:

```
OPENAI_API_KEY=your-api-key-here
```

## Usage

Run the application:

```bash
python app.py
```

This will start the Gradio interface on `http://localhost:7860` by default.

## Adding New API Tools

You can add new API tools directly in the chat interface using the `!add_api` command followed by a JSON configuration:

```
!add_api {"name": "Cat Facts API", "description": "Get a random cat fact", "url": "https://catfact.ninja/fact", "method": "GET", "output_mapping": {"fact": "fact", "length": "length"}, "error_message": "Sorry, I couldn't retrieve a cat fact at the moment."}
```

## API Configuration Format

The JSON configuration for an API tool consists of:

- `name`: A unique name for the API
- `description`: Description of what the API does
- `url`: The API endpoint URL (can include placeholders like `{city}` that will be filled by parameters)
- `method`: HTTP method (GET, POST, etc.)
- `headers`: Optional headers to include in the request
- `params`: Optional query parameters to include in the request
- `body`: Optional request body for POST/PUT requests
- `input_schema`: Schema defining the input parameters for the API
- `output_mapping`: Mapping from the API response to the output fields (using dot notation for nested fields)
- `timeout`: Timeout for the API request in seconds
- `error_message`: Custom error message when the API request fails

## Example API Configurations

See the `api_configs.json` file for example API configurations.

## Architecture

The system uses the following components:

1. **ChatContext** - Manages conversation history
2. **APIConfig** - Defines the configuration for an API endpoint
3. **DynamicAPIToolManager** - Creates and manages dynamic API tools
4. **Agent System** - Routes requests to specialized agents
   - Triage Agent - Routes requests to specialized agents
   - Specialized Agents - Handle specific tasks using their assigned tools

## Extending

You can extend the system by:

1. Adding new built-in tools in the code
2. Adding new API configurations at runtime
3. Modifying the agent system to include additional specialized agents