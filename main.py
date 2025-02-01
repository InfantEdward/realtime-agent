import os
import uvicorn
from dotenv import load_dotenv
from app.realtime_api import RealtimeAPI

load_dotenv()

app = RealtimeAPI(title="Browser-Based Realtime with Audio Playback")
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8000))

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
