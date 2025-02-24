# realtime-agent

Welcome to the `realtime-agent` project! This application leverages OpenAI's Realtime API to provide seamless, real-time interactions. It allows users to start a session, capture both audio and text input, and receive immediate transcriptions along with text-to-speech (TTS) playback directly in the browser.

## Getting Started

Follow these steps to run the app locally:

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

3. **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

4. **Set up your environment variables:**
    Create a `.env` file in the project's root directory with the following content:
    ```env
    OPENAI_API_KEY=""
    REALTIME_MODEL="gpt-4o-realtime-preview-2024-12-17"
    TEMPERATURE=0.8
    VOICE="alloy"
    TURN_DETECTION_CONFIG={"type": "server_vad"}
    INPUT_AUDIO_TRANSCRIPT_CONFIG={"model": "whisper-1"}
    TOOL_CHOICE="auto"

    LOG_LEVEL=INFO
    LOG_DIR=./logs
    EXC_INFO=False

    API_HOST="0.0.0.0"
    API_PORT=8000
    ```

    **Note:** Only `OPENAI_API_KEY`, `REALTIME_MODEL`, and `TURN_DETECTION_CONFIG` are mandatory.

5. **Run the app using the main script:**
    ```sh
    python main.py
    ```

## Running with Docker

You can also run the app using Docker:

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

Once the app is running, open your browser and navigate to `http://localhost:8000`. The frontend now supports multiple interaction methods:

### Session Controls

- **Start Session:**  
  Click the **Start Session** button to initiate a new session. The session ID will be displayed, and a WebSocket connection is opened to handle real-time communication.

- **Stop Session:**  
  Click the **Stop Session** button to end the session. This stops audio recording (if active), clears the transcript displays, and closes the WebSocket connection.

### Audio Recording & TTS Playback

- **Start/Stop Recording:**  
  The **Start Recording** button toggles to **Stop Recording** when recording is active. When activated, the browser will capture audio from your microphone and send audio chunks via the WebSocket. Incoming `audio_delta` messages from the server trigger TTS playback, ensuring seamless audio playback using an AudioContext with a 24kHz sample rate.

### Text Input

- **Send Text:**  
  Use the text field to type messages and click **Send** (or press Enter). The text is sent to the agent, and your input is also displayed in the transcript area. This allows you to combine audio and text interactions in real time.

### Transcription Displays

There are two transcript boxes:
- **Input Transcript:** Shows transcriptions from either the user’s spoken words or manually entered text.
- **Response Transcript:** Displays transcriptions or text deltas from the agent's responses.

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
By default, a schema will be created for each function in `TOOL_LIST`. If you wish to define the schemas for the functions in `TOOL_LIST` yourself, you can pass the list of schemas in `TOOL_SCHEMA_LIST`. Make sure the schema list follows OpenAI's Realtime API required format for function calling.

## Customizing the Agent's Instructions

The instructions given to the agent can be customized by modifying the `INSTRUCTIONS` variable in the `app/config.py` file.

## Customizing the Initial User Message

You can prompt the agent to generate an initial response as soon as you click the **Start Session** button by sending an initial message to the server. This prompt can be customized by modifying the `INITIAL_USER_MESSAGE` variable in the `app/config.py` file.