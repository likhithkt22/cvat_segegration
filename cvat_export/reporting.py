"""Cross-checks Excel entries against what was actually processed."""


from pathlib import Path

from .writers import write_csv_report


def validate_excel_matches(
    anomaly_map,
    assigned_jobs,
    processed_anomaly_keys,
    output_folder
):
    """
    Report Excel entries that were not found
    in the assigned job/frame ranges returned for this task.
    """
    assigned_job_ids = {
        int(job["id"])
        for job in assigned_jobs
    }

    rows = []

    for (
        job_id,
        frame_number
    ), information in sorted(
        anomaly_map.items()
    ):

        if job_id not in assigned_job_ids:
            status = "JOB_NOT_IN_SELECTED_TASK"

        elif (
            job_id,
            frame_number
        ) not in processed_anomaly_keys:
            status = "FRAME_NOT_FOUND"

        else:
            status = "MATCHED"

        rows.append({
            "job_id": job_id,
            "frame_number": frame_number,
            "reason": "; ".join(
                information["reasons"]
            ),
            "status": status
        })

    report_file = (
        Path(output_folder)
        / "Excel_Matching_Report.csv"
    )

    write_csv_report(
        report_file,
        rows,
        [
            "job_id",
            "frame_number",
            "reason",
            "status"
        ]
    )

    return rows
