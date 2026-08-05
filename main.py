import sys
import io
import os
try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
        
    load_dotenv()
except ImportError:
    pass

# Set stdout encoding to utf-8 for Windows console support
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

from src.coordinator import run_all

if __name__ == "__main__":
    print("Starting Multi-Agent E-Commerce Dispute Resolution System...")
    run_all()
    print("Completed processing all 50 cases successfully!")
