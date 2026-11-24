import os
import sys
from dotenv import load_dotenv

# Ensure root directory is in python path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(root_dir, "backend"))

# Load .env
load_dotenv(os.path.join(root_dir, ".env"))

import uvicorn

if __name__ == "__main__":
    print("Starting Lyftr AI backend on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=os.path.join(root_dir, "backend"))
