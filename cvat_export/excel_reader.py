"""Reads the anomaly Excel sheet (Reason | JOB ID | Frame Number)."""


import re
from pathlib import Path

from openpyxl import load_workbook


def normalize_header(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def parse_frame_numbers(value):
    """
    Excel examples:

        409,430
        1365
        125,012,581,272
        1934,1949,1911

    Commas are treated as frame separators.

    Returns:
        [409, 430]
    """
    if value is None:
        return []

    # Excel numeric value
    if isinstance(value, int):
        return [value]

    if isinstance(value, float):
        if value.is_integer():
            return [int(value)]

        raise ValueError(
            f"Invalid non-integer frame number: {value}"
        )

    text = str(value).strip()

    if not text:
        return []

    # Support comma, semicolon and newline separators.
    parts = re.split(r"[,;\n]+", text)

    frames = []

    for part in parts:
        part = part.strip()

        if not part:
            continue

        # Remove accidental spaces
        part = part.replace(" ", "")

        if not re.fullmatch(r"\d+", part):
            raise ValueError(
                f"Invalid frame value '{part}' "
                f"from Excel cell '{value}'"
            )

        frames.append(int(part))

    return frames


def read_anomaly_excel(excel_file):
    """
    Read:

        Reason | JOB ID | Frame Number

    Returns:

        {
            (job_id, frame_number): {
                "reasons": [...]
            }
        }
    """
    excel_path = Path(excel_file)

    if not excel_path.exists():
        raise FileNotFoundError(
            f"Excel file not found:\n{excel_path}"
        )

    workbook = load_workbook(
        filename=excel_path,
        data_only=True
    )

    worksheet = workbook.active

    headers = {}

    for column in range(
        1,
        worksheet.max_column + 1
    ):
        value = worksheet.cell(
            row=1,
            column=column
        ).value

        headers[normalize_header(value)] = column

    required_columns = [
        "reason",
        "job id",
        "frame number"
    ]

    missing = [
        column
        for column in required_columns
        if column not in headers
    ]

    if missing:
        raise RuntimeError(
            "Excel is missing required columns: "
            + ", ".join(missing)
        )

    anomaly_map = {}

    for row_number in range(
        2,
        worksheet.max_row + 1
    ):
        reason = worksheet.cell(
            row=row_number,
            column=headers["reason"]
        ).value

        job_value = worksheet.cell(
            row=row_number,
            column=headers["job id"]
        ).value

        frame_value = worksheet.cell(
            row=row_number,
            column=headers["frame number"]
        ).value

        if job_value is None or frame_value is None:
            continue

        try:
            job_id = int(str(job_value).strip())
        except ValueError:
            raise RuntimeError(
                f"Invalid JOB ID in Excel row {row_number}: "
                f"{job_value}"
            )

        try:
            frames = parse_frame_numbers(frame_value)
        except ValueError as exc:
            raise RuntimeError(
                f"Excel row {row_number}: {exc}"
            ) from exc

        reason_text = (
            str(reason).strip()
            if reason is not None
            else ""
        )

        for frame_number in frames:
            key = (job_id, frame_number)

            if key not in anomaly_map:
                anomaly_map[key] = {
                    "reasons": []
                }

            if (
                reason_text
                and reason_text not in anomaly_map[key]["reasons"]
            ):
                anomaly_map[key]["reasons"].append(
                    reason_text
                )

    return anomaly_map
