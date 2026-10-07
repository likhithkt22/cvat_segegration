"""Central configuration. Edit the values below before running."""

# ============================================================
# CONFIGURATION
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CVAT_URL = os.getenv("CVAT_URL", "")
CVAT_TOKEN = os.getenv("CVAT_TOKEN", "")
EXCEL_FILE = os.getenv("EXCEL_FILE", "")
BACKUP_FOLDER = os.getenv("BACKUP_FOLDER", "")


# Project and Task
PROJECT_NAME_OR_ID = "Project_1 #3"
TASK_NAME_OR_ID = ""  # Empty = process ALL tasks in the project


# original = best quality available
# compressed = smaller/faster
IMAGE_QUALITY = "original"

# LabelMe JSON version requested
LABELME_VERSION = "5.4.1"

# API timeouts
CONNECT_TIMEOUT = 30
READ_TIMEOUT = 600

# Wait between CVAT request-status checks
REQUEST_POLL_SECONDS = 2

# Minimum percentage of image area that must be covered by annotation
# polygons/rectangles to consider the frame fully annotated.
# void is treated like every other area annotation.
ANNOTATION_COVERAGE_THRESHOLD = 80


# Minimum percentage of image area that must be covered for a frame to be
# considered fully annotated. This is the threshold actually used by
# coverage.calculate_annotation_coverage().
COVERAGE_THRESHOLD = 80
