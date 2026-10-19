"""
Run script for ESR Foods Application
"""
import uvicorn
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
load_dotenv(os.path.join(project_root, ".env"))

if __name__ == "__main__":
    print("Starting ESR Foods Business Operations Management System...")
    print("Backend API: http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")
    print("Bootstrap the database with python backend/seed_data.py before first use.")
    print()
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
