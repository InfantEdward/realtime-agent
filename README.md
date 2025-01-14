# realtime-agent

Welcome to the `realtime-agent` project! This application leverages OpenAI's Realtime API to provide seamless real-time interactions. Inspired by the "push_to_talk" example from the openai-python repository, our app offers enhanced functionality and customization. Check out the original example here: https://github.com/openai/openai-python/blob/main/examples/realtime/push_to_talk_app.py.

## Getting Started

Follow these steps to get the app up and running:

1. **Create a virtual environment:**
    ```sh
    python -m venv venv
    ```

2. **Activate the virtual environment:**
    - On Windows:
        ```sh
        .\venv\Scripts\activate
        ```
    - On macOS/Linux:
        ```sh
        source venv/bin/activate
        ```

3. **Install the required libraries:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Set up your environment variables:**
    Create a `.env` file in the root directory of the project and add the following variables:
    ```env
    OPENAI_API_KEY=""
    REALTIME_MODEL="gpt-4o-realtime-preview-2024-12-17"
    TURN_DETECTION_CONFIG={"type": "server_vad"}
    INPUT_AUDIO_TRANSCRIPT_CONFIG={"model": "whisper-1"}
    INPUT_AUDIO_TRANSCRIPT_PREFIX=""
    OUTPUT_AUDIO_TRANSCRIPT_PREFIX=""
    INPUT_OUTPUT_TRANSCRIPTS_SEP="\n\n\n"
    TOOL_CHOICE="auto"

    LOG_LEVEL=INFO
    LOG_DIR=./logs
    LOG_REALTIME_EVENTS=False
    EXC_INFO=False
    ```

    Note: Only `OPENAI_API_KEY`, `REALTIME_MODEL`, and `TURN_DETECTION_CONFIG` are mandatory. The rest are optional and can be customized as needed. Additionally, the turn detection currently only supports `{"type": "server_vad"}`.

5. **Run the app through the `main.py` script:**
    ```sh
    python main.py
    ```

## Customizing the Tools

You can easily customize the tools available to the agent by modifying the `TOOL_LIST` in the `main.py` file. If you need to create custom tools, ensure they have a docstring and follow the format of the `obtener_clima` function in `user_tools.py`. The first part of the docstring should be the description of the tool, followed by a "------" separating that description and the description of every input argument.

### Example:

```python
def example_tool(argument: str) -> str:
    """This is an example tool.

    ------
    Parameters:
        argument: Description of the argument.
    """
    return f"Processed {argument}"
```

## Customizing the Agent's Instructions

The instructions given to the agent can be customized by passing them when initializing the agent with the `system_prompt` variable. In the current setup, this is defined as `INSTRUCTIONS` in the `main.py` file.