import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)

TICKETS_FILE = os.path.join(DATA_DIR, "tickets.json")

# Chunking config
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

# Retrieval config
RETRIEVER_K = 5

# Embeddings config
EMBEDDINGS_MODEL = "all-MiniLM-L6-v2"

# LLM config
LLM_TEMPERATURE = 0

# Scope definitions
SCOPE_GLOBAL = "GLOBAL"
SCOPE_CLIENT = "CLIENT"
SCOPE_SYSTEM = "SYSTEM"
SCOPE_PRIVATE = "PRIVATE"

SCOPES = [SCOPE_GLOBAL, SCOPE_CLIENT, SCOPE_SYSTEM, SCOPE_PRIVATE]
