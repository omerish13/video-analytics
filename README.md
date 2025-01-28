# Video Movement Detector

## Description
A program that detects and shows movements in a video.

## Installation
```bash
# Clone the repository
git clone https://github.com/omerish13/video-analytics.git

# Navigate to the project directory
cd video-analytics

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
# Install dependencies
pip install -r requirements.txt 

# My recommendation - use UV
# Create virtual environment (optional)
# Install uv from https://docs.astral.sh/uv/
uv venv
source .venv/bin/activate  # On Windows, use `.venv\bin\activate.ps1`
# Install dependencies
uv pip intall -r requirements.txt
 
```

## Usage
```python
python main.py
```

## Project Structure
```
video-analytics/
├── README.md
├── entities
│   ├── __init__.py
│   ├── detector.py
│   ├── display.py
│   └── streamer.py
├── main.py
├── pyproject.toml
├── requirements.txt
├── utils
│   ├── __init__.py
│   └── menu.py
└── uv.lock
```

## Requirements
- Python 3.12
- Dependencies listed in requirements.txt