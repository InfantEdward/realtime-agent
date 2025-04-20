import uvicorn
from dotenv import load_dotenv
from app.realtime_api import RealtimeAPI
from app.config import get_app_config

load_dotenv()

app = RealtimeAPI(title="Browser-Based Realtime with Audio Playback")
app_config = get_app_config()
API_HOST = app_config.API_HOST
API_PORT = app_config.API_PORT

if __name__ == "__main__":
    uvicorn.run(app, host=API_HOST, port=API_PORT)
