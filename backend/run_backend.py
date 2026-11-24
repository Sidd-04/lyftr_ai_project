import os
import sys

# Ensure backend directory is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Load .env from root
from dotenv import load_dotenv
load_dotenv(os.path.join(current_dir, "..", ".env"))
load_dotenv()

import uvicorn

if __name__ == "__main__":
    print("Starting Lyftr AI backend on http://127.0.0.1:8000 ...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
