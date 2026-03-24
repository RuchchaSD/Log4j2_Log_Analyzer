from pathlib import Path

APP_HOST = "0.0.0.0"
APP_PORT = 8765
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ANALYZER_DIR_NAME = ".wso2analyzer"
RECENTS_FILE = Path.home() / ".wso2analyzer" / "recents.json"
MAX_RECENT_PROJECTS = 10
