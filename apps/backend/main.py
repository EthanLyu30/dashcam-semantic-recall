from dotenv import load_dotenv
load_dotenv()

try:
    from .dvr_semantic_backend.api import create_app
except ImportError:  # pragma: no cover - supports direct script execution
    from dvr_semantic_backend.api import create_app


app = create_app()

