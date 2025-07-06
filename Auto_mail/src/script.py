import os
import yaml
from pathlib import Path

def load_config(config_path):
    abs_config_path = os.path.abspath(config_path)
    if not os.path.exists(abs_config_path):
        print("using default config")
        abs_config_path = Path(__file__).parent.parent / 'config' / 'config.yaml'
    with open(abs_config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config