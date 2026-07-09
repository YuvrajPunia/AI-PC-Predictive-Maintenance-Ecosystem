import os

# Root directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# SQLite database settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{os.path.join(BASE_DIR, 'app', 'pc_health.db')}"
)

# CSV dataset locations (directly in project root as provided)
PC_CSV_PATH = os.path.join(PROJECT_ROOT, "organization_pcs.csv")
REPAIR_CSV_PATH = os.path.join(PROJECT_ROOT, "accurate_repair_history_v2.csv")
RAW_DATASET_PATH = os.path.join(PROJECT_ROOT, "physically_meaningful_pc_health_dataset.csv")

# Model folder
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Feature Thresholds (Configurable)
TEMP_WARNING_THRESHOLD = 75.0  # °C
TEMP_CRITICAL_THRESHOLD = 95.0 # °C
VOLTAGE_NOMINAL = 12.0         # Volts (aligned with physically_meaningful_pc_health_dataset)
VOLTAGE_TOLERANCE = 2.0        # Volts +/-
CPU_HIGH_THRESHOLD = 85.0      # %
RAM_HIGH_THRESHOLD = 85.0      # %
FAN_MIN_RPM = 2000.0           # RPM

# Retrieval Similarity Weights (Configurable)
WEIGHT_COMPLAINT_SEMANTIC = 0.65
WEIGHT_SYMPTOMS_SEMANTIC = 0.20
WEIGHT_PROBLEM_TYPE = 0.05
WEIGHT_MODEL_CONTEXT = 0.10
DEFAULT_RETRIEVAL_THRESHOLD = 65.0

