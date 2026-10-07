# cvat_segegration
This repo describes an automated workflow for validating CVAT annotations, classifying image frames, exporting LabelMe annotations, and organizing results into standardized output folders.

---

## Features

- Processes a whole CVAT project, or a single task
- Processes every **assigned** job, regardless of who it is assigned to (unassigned jobs are skipped)
- Calculates how much of each image is covered by polygons/rectangles (overlaps counted once, clipped to the image)
- Flags frames listed in an Excel sheet as anomalies
- Downloads each frame as an image and converts the CVAT annotations to LabelMe 5.4.1 JSON
- Writes CSV reports covering every frame and every Excel entry

---

## How frames are classified

For every frame in every assigned job:

| Step | Condition | Result |
|------|-----------|--------|
| 1 | Annotation coverage is below the threshold (99.99%) | **Anomaly** (incomplete annotation) |
| 2 | Coverage is complete **and** the `(job id, frame number)` is listed in the Excel file | **Anomaly** (Excel) |
| 3 | Otherwise | **Completed** |

`void` is treated like any other area annotation. Points and lines do not contribute to coverage.

---

## Requirements

- Python 3.8+
- A CVAT account with a **Personal Access Token**
- Permission to view all jobs in the project (otherwise the tool stops rather than export an incomplete task)

Install the dependencies:

```bash
pip install -r requirements.txt
```

---

## Project structure

```
.
├── main.py                  # Entry point
├── requirements.txt
└── cvat_export/
    ├── config.py            # All settings
    ├── utils.py             # Name helpers
    ├── http_client.py       # HTTP session and CVAT API helpers
    ├── cvat_api.py          # Project, task, job, metadata and label lookups
    ├── excel_reader.py      # Excel anomaly list reader
    ├── annotations.py       # CVAT to LabelMe conversion
    ├── coverage.py          # Annotation coverage calculation
    ├── image_download.py    # Frame download and image naming
    ├── writers.py           # LabelMe JSON and CSV writers
    ├── job_processor.py     # Per-job classification and export
    ├── reporting.py         # Excel matching report
    └── app.py               # Orchestration
```

---

## Configuration

Edit `cvat_export/config.py`:

| Setting | Description |
|---------|-------------|
| `CVAT_URL` | Base URL of your CVAT server |
| `CVAT_TOKEN` | Your Personal Access Token |
| `PROJECT_NAME_OR_ID` | Project name, or `Name #ID` (e.g. `Project_1 #3`). The ID is preferred when given |
| `TASK_NAME_OR_ID` | Task name or `Name #ID`. **Leave empty to process all tasks in the project** |
| `EXCEL_FILE` | Path to the Excel anomaly list |
| `BACKUP_FOLDER` | Root folder for the output |
| `IMAGE_QUALITY` | `original` (best quality) or `compressed` (smaller/faster) |
| `LABELME_VERSION` | LabelMe JSON version written to the files |
| `CONNECT_TIMEOUT` / `READ_TIMEOUT` | API timeouts in seconds |
| `COVERAGE_THRESHOLD` | Minimum coverage (%) for a frame to count as fully annotated (`99.99`) |

> **Security:** do not commit your real token. Keep `CVAT_TOKEN` empty in the repository and add it only on your own machine.

---

## Excel file format

The first sheet must have these column headers (case-insensitive):

| Reason | JOB ID | Frame Number |
|--------|--------|--------------|
| Blurry image | 100 | 409, 430 |
| Glare | 101 | 1365 |

- `Frame Number` can hold one number or several, separated by commas, semicolons or new lines.
- Rows missing a `JOB ID` or `Frame Number` are skipped.

---

## Usage

```bash
python main.py
```

The tool prints the project, tasks and jobs it found, then asks for confirmation before it starts:

```
Start processing N task(s) and all assigned jobs? (Y/N):
```

---

## Output

```
<BACKUP_FOLDER>/
└── <YYYY-MM-DD>/
    └── Project_<id>_<name>/
        ├── Completed/
        │   ├── images/
        │   └── annotations/
        ├── Anomaly/
        │   ├── images/
        │   └── annotations/
        ├── Processing_Report.csv
        └── Excel_Matching_Report.csv
```

- **Images** are named `job_<id>_frame_<000000>_<original name>.<ext>`.
- **Annotations** are LabelMe JSON files with the same base name as the image.
- CVAT tags are preserved in the JSON under `cvatTags`.

### Supported shapes

| CVAT | LabelMe |
|------|---------|
| polygon | polygon |
| rectangle | rectangle |
| polyline | line |
| points | point |

Other shape types (ellipse, cuboid, skeleton, etc.) are not exported. Track shapes are included for the frames they appear on.

### Reports

**`Processing_Report.csv`** has one row per frame, with the category, reason, coverage %, completeness, Excel match, file paths and a status (`SUCCESS` or `IMAGE_DOWNLOAD_FAILED`).

**`Excel_Matching_Report.csv`** has one row per Excel entry, with one of these statuses:

| Status | Meaning |
|--------|---------|
| `MATCHED` | The frame was found and exported as an anomaly |
| `JOB_NOT_IN_SELECTED_TASK` | The job is not among the processed assigned jobs |
| `FRAME_NOT_FOUND` | The job was processed, but the frame number does not exist in that job |

---

## Troubleshooting

| Problem | Likely cause |
|---------|--------------|
| `Please enter your CVAT Personal Access Token` | `CVAT_TOKEN` is empty in `config.py` |
| `CVAT reports N job(s)... but the API token can currently see only M` | The token's user lacks permission to view all jobs in the task/project |
| `Excel file not found` | Check `EXCEL_FILE` |
| `Excel is missing required columns` | Row 1 must contain `Reason`, `JOB ID` and `Frame Number` |
| `Multiple projects/tasks found with name ...` | Use the `Name #ID` format |