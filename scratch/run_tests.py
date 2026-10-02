import subprocess
import os

workspace = r"d:\AI-Agent-Coordination-Engine"
os.chdir(workspace)

with open("test_output.txt", "w") as f:
    try:
        # Assuming venv is used, use python -m pytest
        # Or just try pytest
        result = subprocess.run(["python", "-m", "pytest", "tests/test_m3_workflow.py"], capture_output=True, text=True)
        f.write("--- M3 Tests ---\n")
        f.write(result.stdout)
        f.write(result.stderr)
    except Exception as e:
        f.write(str(e))
