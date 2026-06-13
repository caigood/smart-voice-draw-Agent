import os
from pathlib import Path
from dotenv import load_dotenv

# 显式指定 .env 文件路径，避免工作目录问题
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

IMAGE_API_KEY = os.getenv("IMAGE_API_KEY", "")
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "https://api.openai.com/v1")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "dall-e-3")

# CrewAI 存储路径配置（使用项目目录内的 .crewai 目录，避免写入系统目录）
CREWAI_STORAGE_DIR = Path(__file__).parent / ".crewai"
CREWAI_LOCALAPPDATA_DIR = CREWAI_STORAGE_DIR / "localappdata"
CREWAI_CONFIG_DIR = CREWAI_STORAGE_DIR / "config"
CREWAI_HOME_DIR = CREWAI_STORAGE_DIR / "home"
os.environ["CREWAI_STORAGE_DIR"] = str(CREWAI_STORAGE_DIR)
os.environ["CREWAI_HOME"] = str(CREWAI_STORAGE_DIR)
os.environ["LOCALAPPDATA"] = str(CREWAI_LOCALAPPDATA_DIR)
os.environ["APPDATA"] = str(CREWAI_LOCALAPPDATA_DIR)
os.environ["XDG_CONFIG_HOME"] = str(CREWAI_CONFIG_DIR)
os.environ["HOME"] = str(CREWAI_HOME_DIR)
os.environ["USERPROFILE"] = str(CREWAI_HOME_DIR)
os.environ["CREWAI_TELEMETRY"] = "false"
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
CREWAI_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
CREWAI_LOCALAPPDATA_DIR.mkdir(parents=True, exist_ok=True)
CREWAI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
CREWAI_HOME_DIR.mkdir(parents=True, exist_ok=True)

try:
    import appdirs
    appdirs.user_data_dir = lambda *args, **kwargs: str(CREWAI_STORAGE_DIR)
    appdirs.user_config_dir = lambda *args, **kwargs: str(CREWAI_CONFIG_DIR)
    appdirs.user_cache_dir = lambda *args, **kwargs: str(CREWAI_STORAGE_DIR / "cache")
except Exception:
    pass
