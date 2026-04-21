from pathlib import Path

APP_HOST = "0.0.0.0"
APP_PORT = 8765
BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = Path(__file__).parent / "data"
ANALYZER_DIR_NAME = ".wso2analyzer"
ANALYZER_HOME = Path.home() / ".wso2analyzer"
RECENTS_FILE = ANALYZER_HOME / "recents.json"
LOG_FORMATS_FILE = ANALYZER_HOME / "log_formats.json"
REPOS_REGISTRY_FILE = ANALYZER_HOME / "repos.json"
REPOS_CHECKOUT_DIR = ANALYZER_HOME / "repos"
MAX_RECENT_PROJECTS = 10

REPOS_SEED_FILE = DATA_DIR / "repos.json"
JAR_OVERRIDES_SEED_FILE = DATA_DIR / "jar-overrides.json"
FEATURES_SEED_FILE = DATA_DIR / "features.json"

MAX_WORKTREES_PER_REPO = 10
