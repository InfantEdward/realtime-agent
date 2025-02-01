# realtime-agent

Welcome to the `realtime-agent` project! This application leverages OpenAI's Realtime API to provide seamless real-time interactions. It allows users to start a session, record audio, and receive real-time transcriptions and text-to-speech (TTS) playback directly in their browser.

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

    API_HOST="0.0.0.0"
    API_PORT=8000
    ```

    Note: Only `OPENAI_API_KEY`, `REALTIME_MODEL`, and `TURN_DETECTION_CONFIG` are mandatory. The rest are optional and can be customized as needed. Additionally, the turn detection currently only supports `{"type": "server_vad"}`.

5. **Run the app through the `main.py` script:**
    ```sh
    python main.py
    ```

## Running with Docker

You can also run the app using Docker. Follow these steps:

1. **Build the Docker image:**
    ```sh
    docker build -t realtime-agent .
    ```

2. **Run the Docker container:**
    ```sh
    docker run -p 8000:8000 --env-file .env realtime-agent
    ```

3. **Run the Docker container with a volume for logs:**
    ```sh
    docker run -p 8000:8000 --env-file .env -v $(pwd)/logs:/app/logs realtime-agent
    ```

## Using the Browser Frontend

Once the app is running, open your browser and navigate to `http://localhost:8000`. You will see the Realtime Agent App interface with the following controls:

1. **Start Session:** Click the "Start Session" button to initiate a new session. The session ID will be displayed.
2. **Stop Session:** Click the "Stop Session" button to end the current session.
3. **Start/Stop Recording:** Click the "Start Recording" button to begin recording audio. The button will change to "Stop Recording" while recording is active. Click it again to stop recording.

The transcriptions will be displayed in real-time in the "Transcript" section, and TTS playback will be scheduled automatically.

## Customizing the Tools

You can easily customize the tools available to the agent by modifying the `TOOL_LIST` in the `app/config.py` file. If you need to create custom tools, ensure they have a docstring and follow the format of the `obtener_clima` function in `app/user_tools.py`. The first part of the docstring should be the description of the tool, followed by a "------" separating that description and the description of every input argument.

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

The instructions given to the agent can be customized by modifying the `INSTRUCTIONS` variable in the `app/config.py` file.