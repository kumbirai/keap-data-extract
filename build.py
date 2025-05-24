import os
import sys
import subprocess
from pathlib import Path

def build_executable():
    """
    Build the Windows executable using PyInstaller
    """
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()
    
    # Create dist directory if it doesn't exist
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)
    
    # Create build directory if it doesn't exist
    build_dir = project_root / "build"
    build_dir.mkdir(exist_ok=True)
    
    # PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=keap_data_extract",
        "--onefile",  # Create a single executable
        "--windowed",  # Don't show console window
        "--add-data=src;src",  # Include source files
        "--hidden-import=sqlalchemy",
        "--hidden-import=psycopg2",
        "--hidden-import=alembic",
        "--hidden-import=dotenv",
        "src/__main__.py"  # Main entry point
    ]
    
    # Run PyInstaller
    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("Build completed successfully!")
        print(f"Executable can be found in: {dist_dir / 'keap_data_extract.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable() 