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
REPAIR_CSV_PATH = os.path.join(PROJECT_ROOT, "repair_history.csv")
RAW_DATASET_PATH = r"C:\Users\jahan\.gemini\antigravity\scratch\MotherboardHealthAI\data\Laptop_Motherboard_Health_Monitoring_Dataset.csv"

# Model folder
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")

# Feature Thresholds (Configurable)
TEMP_WARNING_THRESHOLD = 75.0  # °C
VOLTAGE_NOMINAL = 15.0         # Volts
VOLTAGE_TOLERANCE = 3.0        # Volts +/-
CPU_HIGH_THRESHOLD = 85.0      # %
RAM_HIGH_THRESHOLD = 85.0      # %
FAN_MIN_RPM = 2000.0           # RPM

# Retrieval Similarity Weights (Configurable)
WEIGHT_COMPLAINT_SEMANTIC = 0.55
WEIGHT_SYMPTOMS_SEMANTIC = 0.20
WEIGHT_PROBLEM_TYPE = 0.15
WEIGHT_MODEL_CONTEXT = 0.10
