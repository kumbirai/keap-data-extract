import os
import sys
import subprocess
from pathlib import Path


def build_executable():
    """
    Build the executable using PyInstaller
    """
    # Get the project root directory
    project_root = Path(__file__).parent.absolute()

    # Create dist directory if it doesn't exist
    dist_dir = project_root / "dist"
    dist_dir.mkdir(exist_ok=True)

    # Create build directory if it doesn't exist
    build_dir = project_root / "build"
    build_dir.mkdir(exist_ok=True)

    # Determine the correct path separator for the platform
    separator = ";" if sys.platform == "win32" else ":"

    # Determine icon file based on platform
    icon_file = "assets/icon.ico" if sys.platform == "win32" else "assets/icon.png"

    # PyInstaller command
    pyinstaller_cmd = ["pyinstaller", "--name=keap_data_extract", "--onefile",  # Create a single executable
        "--noconsole",  # Don't show console window but still allow arguments
        f"--icon={icon_file}",  # Add application icon
        f"--add-data=src{separator}src",  # Include source files
        "--hidden-import=sqlalchemy", "--hidden-import=psycopg2", "--hidden-import=alembic", "--hidden-import=dotenv", 
        "--hidden-import=dateutil", "--hidden-import=dateutil.parser", "--hidden-import=dateutil.tz",
        "--hidden-import=requests", "--hidden-import=urllib3", "--hidden-import=certifi", "--hidden-import=charset_normalizer", "--hidden-import=idna",
        "--hidden-import=logging", "--hidden-import=logging.handlers", "--hidden-import=logging.config", "--hidden-import=logging.handlers.RotatingFileHandler",
        "--hidden-import=datetime", "--hidden-import=typing", "--hidden-import=urllib.parse", "--hidden-import=sqlalchemy.orm", "--hidden-import=sqlalchemy.exc",
        f"--add-data=.env{separator}.",  # Include .env file
        f"--add-data=logs{separator}logs",  # Include logs directory
        f"--add-data=checkpoints{separator}checkpoints",  # Include checkpoints directory
        "src/__main__.py"  # Main entry point
    ]

    # Run PyInstaller
    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("Build completed successfully!")
        executable_name = "keap_data_extract.exe" if sys.platform == "win32" else "keap_data_extract"
        print(f"Executable can be found in: {dist_dir / executable_name}")
    except subprocess.CalledProcessError as e:
        print(f"Build failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
