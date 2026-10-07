"""Application orchestration: wires every module together (the old main())."""


from datetime import datetime
from pathlib import Path

from .config import CVAT_TOKEN, TASK_NAME_OR_ID, EXCEL_FILE, BACKUP_FOLDER
from .cvat_api import (
    get_current_user,
    resolve_project,
    resolve_task,
    get_project_tasks,
    get_task_jobs,
    print_jobs,
)
from .excel_reader import read_anomaly_excel
from .job_processor import process_job
from .reporting import validate_excel_matches
from .utils import safe_name
from .writers import write_csv_report


def main():

    if (
        not CVAT_TOKEN.strip()
        or CVAT_TOKEN == "PASTE_YOUR_CVAT_PERSONAL_ACCESS_TOKEN_HERE"
    ):
        raise RuntimeError(
            "Please enter your CVAT Personal Access Token in CVAT_TOKEN."
        )

    print("\n" + "=" * 100)
    print("CVAT PROJECT ANOMALY / COMPLETED EXPORT TOOL")
    print("=" * 100)

    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    print("\nReading Excel file...")

    anomaly_map = read_anomaly_excel(
        EXCEL_FILE
    )

    print(
        f"Anomaly entries loaded: "
        f"{len(anomaly_map)}"
    )

    # --------------------------------------------------------
    # CURRENT USER
    # --------------------------------------------------------

    print("\nGetting current CVAT user...")

    user = get_current_user()

    user_id = user.get("id")
    username = user.get("username", "")

    print(
        f"Logged in as: "
        f"{username} (ID: {user_id})"
    )

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    print("\nResolving project...")

    project = resolve_project()

    project_id = int(project["id"])
    project_name = project.get(
        "name",
        f"Project_{project_id}"
    )

    print(
        f"Project: "
        f"{project_name} "
        f"(ID: {project_id})"
    )

    # --------------------------------------------------------
    # TASKS
    # --------------------------------------------------------

    if TASK_NAME_OR_ID.strip():

        print(
            f"\nSpecific task configured: "
            f"{TASK_NAME_OR_ID}"
        )

        tasks = [
            resolve_task(project)
        ]

    else:

        print(
            "\nNo specific task configured."
        )
        print(
            "Getting ALL tasks in the project..."
        )

        tasks = get_project_tasks(
            project_id
        )

    if not tasks:
        print(
            "\nNo tasks found in the project."
        )
        return

    print(
        f"\nTasks to process: {len(tasks)}"
    )

    # --------------------------------------------------------
    # COMMON PROJECT OUTPUT FOLDER
    # --------------------------------------------------------

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    project_output_folder = (
        Path(BACKUP_FOLDER)
        / today
        / (
            f"Project_{project_id}_"
            f"{safe_name(project_name)}"
        )
    )

    project_output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    # Create the common structure before processing.
    for folder in [
        project_output_folder / "Completed" / "images",
        project_output_folder / "Completed" / "annotations",
        project_output_folder / "Anomaly" / "images",
        project_output_folder / "Anomaly" / "annotations",
    ]:
        folder.mkdir(
            parents=True,
            exist_ok=True
        )

    print(
        f"\nProject output folder:\n"
        f"{project_output_folder}"
    )

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    print("\n" + "=" * 100)

    confirmation = input(
        f"Start processing {len(tasks)} task(s) "
        f"and all assigned jobs? (Y/N): "
    ).strip().lower()

    if confirmation not in ("y", "yes"):
        print("Operation cancelled.")
        return

    # --------------------------------------------------------
    # PROCESS ALL TASKS
    # --------------------------------------------------------

    report_rows = []
    processed_anomaly_keys = set()
    all_assigned_jobs = []

    total_tasks = len(tasks)
    processed_tasks = 0

    for task in tasks:

        task_id = int(task["id"])
        task_name = task.get(
            "name",
            f"Task_{task_id}"
        )

        print("\n" + "#" * 100)
        print(
            f"TASK {processed_tasks + 1}/{total_tasks}: "
            f"{task_name} (ID: {task_id})"
        )
        print("#" * 100)

        # Get all assigned jobs for this task.
        jobs = get_task_jobs(
            task_id,
            task
        )

        print_jobs(jobs)
        all_assigned_jobs.extend(jobs)

        if not jobs:
            print(
                f"No assigned jobs in Task {task_id}. "
                f"Skipping task."
            )
            processed_tasks += 1
            continue

        # IMPORTANT:
        # task_output_folder is the SAME project folder for every task.
        for job in jobs:

            process_job(
                job=job,
                anomaly_map=anomaly_map,
                task=task,
                task_output_folder=project_output_folder,
                report_rows=report_rows,
                processed_anomaly_keys=processed_anomaly_keys
            )

        processed_tasks += 1

    # --------------------------------------------------------
    # EXCEL MATCHING REPORT
    # --------------------------------------------------------

    matching_rows = validate_excel_matches(
        anomaly_map,
        all_assigned_jobs,
        processed_anomaly_keys,
        project_output_folder
    )

    # --------------------------------------------------------
    # PROCESSING REPORT
    # --------------------------------------------------------

    processing_report = (
        project_output_folder
        / "Processing_Report.csv"
    )

    write_csv_report(
        processing_report,
        report_rows,
        [
            "job_id",
            "frame_number",
            "category",
            "reason",
            "coverage_percent",
            "annotation_complete",
            "excel_match",
            "image",
            "annotation",
            "status",
            "message"
        ]
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    success_rows = [
        row
        for row in report_rows
        if row["status"] == "SUCCESS"
    ]

    anomaly_rows = [
        row
        for row in success_rows
        if row["category"] == "Anomaly"
    ]

    completed_rows = [
        row
        for row in success_rows
        if row["category"] == "Completed"
    ]

    incomplete_rows = [
        row
        for row in anomaly_rows
        if row["annotation_complete"] is False
    ]

    excel_anomaly_rows = [
        row
        for row in anomaly_rows
        if row["annotation_complete"] is True
        and row["excel_match"] is True
    ]

    matched = sum(
        1
        for row in matching_rows
        if row["status"] == "MATCHED"
    )

    not_in_task = sum(
        1
        for row in matching_rows
        if row["status"] == "JOB_NOT_IN_SELECTED_TASK"
    )

    frame_not_found = sum(
        1
        for row in matching_rows
        if row["status"] == "FRAME_NOT_FOUND"
    )

    print("\n" + "=" * 100)
    print("PROCESSING COMPLETED")
    print("=" * 100)

    print(
        f"Project              : "
        f"{project_name} (ID {project_id})"
    )

    print(
        f"Tasks processed      : "
        f"{processed_tasks}/{total_tasks}"
    )

    print(
        f"Total images         : "
        f"{len(success_rows)}"
    )

    print(
        f"Anomaly images       : "
        f"{len(anomaly_rows)}"
    )

    print(
        f"  Incomplete coverage: "
        f"{len(incomplete_rows)}"
    )

    print(
        f"  Excel anomalies    : "
        f"{len(excel_anomaly_rows)}"
    )

    print(
        f"Completed images     : "
        f"{len(completed_rows)}"
    )

    print(
        f"Excel anomaly match  : "
        f"{matched}"
    )

    print(
        f"Job not in task      : "
        f"{not_in_task}"
    )

    print(
        f"Frame not found      : "
        f"{frame_not_found}"
    )

    print(
        f"\nOutput folder:\n"
        f"{project_output_folder}"
    )

    print(
        f"\nProcessing report:\n"
        f"{processing_report}"
    )

    print(
        f"\nExcel matching report:\n"
        f"{project_output_folder / 'Excel_Matching_Report.csv'}"
    )

    print("=" * 100)
