"""CVAT lookups: user, project, tasks, jobs, frame metadata, labels, annotations."""


from .config import PROJECT_NAME_OR_ID, TASK_NAME_OR_ID
from .http_client import request_json, get_paginated
from .utils import parse_name_or_id


def get_current_user():
    """
    Get the user associated with the current API token.
    """
    return request_json("GET", "/api/users/self")


def resolve_project():
    """
    Resolve project using:

        Project_1 #3

    The numeric ID is preferred when supplied.
    """
    project_name, project_id = parse_name_or_id(
        PROJECT_NAME_OR_ID
    )

    if project_id is not None:
        project = request_json(
            "GET",
            f"/api/projects/{project_id}"
        )

        actual_name = project.get("name", "")

        if actual_name != project_name:
            print(
                "WARNING: Project name differs from configuration."
            )
            print(f"Configured : {project_name}")
            print(f"CVAT       : {actual_name}")

        return project

    projects = get_paginated(
        "/api/projects",
        params={
            "name": project_name
        }
    )

    exact_matches = [
        p for p in projects
        if str(p.get("name", "")).strip() == project_name
    ]

    if not exact_matches:
        raise RuntimeError(
            f"Project not found: {PROJECT_NAME_OR_ID}"
        )

    if len(exact_matches) > 1:
        raise RuntimeError(
            f"Multiple projects found with name: {project_name}. "
            f"Use 'Project Name #ID' in configuration."
        )

    return exact_matches[0]


def resolve_task(project):
    """
    Resolve:

        testing #129

    and verify that it belongs to the configured project.
    """
    task_name, task_id = parse_name_or_id(
        TASK_NAME_OR_ID
    )

    if task_id is not None:
        task = request_json(
            "GET",
            f"/api/tasks/{task_id}"
        )
    else:
        tasks = get_paginated(
            "/api/tasks",
            params={
                "project_id": project["id"],
                "name": task_name
            }
        )

        exact_matches = [
            t for t in tasks
            if str(t.get("name", "")).strip() == task_name
        ]

        if not exact_matches:
            raise RuntimeError(
                f"Task not found: {TASK_NAME_OR_ID}"
            )

        if len(exact_matches) > 1:
            raise RuntimeError(
                f"Multiple tasks found with name: {task_name}. "
                f"Use 'Task Name #ID'."
            )

        task = exact_matches[0]

    actual_project_id = task.get("project_id")

    if actual_project_id is None:
        actual_project_id = (
            task.get("project", {}) or {}
        ).get("id")

    if actual_project_id is not None:
        if int(actual_project_id) != int(project["id"]):
            raise RuntimeError(
                f"Task {task['id']} does not belong to "
                f"project {project['id']}."
            )

    return task


def get_project_tasks(project_id):
    """
    Get all tasks belonging to the selected project.
    """
    tasks = get_paginated(
        "/api/tasks",
        params={
            "project_id": int(project_id),
            "page_size": 100,
        }
    )

    print(
        f"\nFound {len(tasks)} task(s) in Project {project_id}."
    )

    for task in tasks:
        print(
            f"Task {task.get('id')} | "
            f"{task.get('name')}"
        )

    return tasks


def get_task_jobs(task_id, task=None):
    """
    Return every job in the selected task that is assigned to a person.

    IMPORTANT:
      - The current API-token user is NOT used as a job filter.
      - Jobs assigned to Likith, Dhruva, or any other user are included.
      - Jobs with no assignee are skipped.

    CVAT documents ``task_id`` as a supported filter for GET /api/jobs.
    """

    all_jobs = get_paginated(
        "/api/jobs",
        params={
            "task_id": int(task_id),
            "page_size": 100,
        }
    )

    print(
        f"\nFound {len(all_jobs)} job(s) returned by CVAT "
        f"for Task {task_id}."
    )

    # TaskRead can contain a jobs summary. If CVAT says the task has more
    # jobs than the list endpoint returned, stop rather than silently
    # exporting an incomplete task. This usually indicates a permission or
    # organization-scope issue with the API token.
    if isinstance(task, dict):
        jobs_summary = task.get("jobs")
        expected_count = None

        if isinstance(jobs_summary, dict):
            for key in ("count", "total", "size"):
                if jobs_summary.get(key) is not None:
                    try:
                        expected_count = int(jobs_summary[key])
                    except (TypeError, ValueError):
                        expected_count = None
                    break

        if (
            expected_count is not None
            and expected_count > len(all_jobs)
        ):
            raise RuntimeError(
                f"CVAT reports {expected_count} job(s) for Task "
                f"{task_id}, but the API token can currently see only "
                f"{len(all_jobs)} job(s). The token/user likely does not "
                f"have permission to access the other jobs. Grant the "
                f"account permission to view the whole task/project, then "
                f"run the script again."
            )

    processable_jobs = []

    print("\nChecking job assignments...")

    for job in all_jobs:
        assignee = job.get("assignee")

        # Only unassigned jobs are skipped.
        if not assignee:
            print(
                f"Job {job.get('id')} | "
                f"UNASSIGNED | SKIPPED"
            )
            continue

        if isinstance(assignee, dict):
            assignee_id = assignee.get("id")
            assignee_name = assignee.get(
                "username",
                f"User_{assignee_id}"
            )
        else:
            assignee_id = assignee
            assignee_name = str(assignee)

        print(
            f"Job {job.get('id')} | "
            f"Assignee: {assignee_name} "
            f"(ID: {assignee_id}) | "
            f"State: {job.get('state')} | "
            f"Frames: {job.get('start_frame')} - "
            f"{job.get('stop_frame')} | INCLUDED"
        )

        processable_jobs.append(job)

    print(
        f"\nAssigned jobs to process: "
        f"{len(processable_jobs)}"
    )

    return processable_jobs


def print_jobs(jobs):
    """
    Display the jobs found for the selected task.
    """

    print("\n" + "=" * 100)
    print("ASSIGNED JOBS TO PROCESS (ALL USERS)")
    print("=" * 100)

    if not jobs:
        print("No matching assigned jobs found.")
        return

    print(
        f"{'Job ID':<12}"
        f"{'State':<18}"
        f"{'Stage':<18}"
        f"{'Start':<12}"
        f"{'Stop':<12}"
        f"{'Assignee':<20}"
    )

    print("-" * 100)

    for job in jobs:

        assignee = job.get("assignee")

        if isinstance(assignee, dict):
            assignee_name = assignee.get(
                "username",
                assignee.get("id", "")
            )
        else:
            assignee_name = assignee or ""

        print(
            f"{str(job.get('id', '')):<12}"
            f"{str(job.get('state', '')):<18}"
            f"{str(job.get('stage', '')):<18}"
            f"{str(job.get('start_frame', '')):<12}"
            f"{str(job.get('stop_frame', '')):<12}"
            f"{str(assignee_name):<20}"
        )

    print("=" * 100)


def get_job_details(job_id):
    return request_json(
        "GET",
        f"/api/jobs/{job_id}"
    )


def get_job_metadata(job_id):
    """
    Returns frame metadata.

    CVAT's DataMetaRead contains frame metadata including
    frame name, width and height.
    """
    return request_json(
        "GET",
        f"/api/jobs/{job_id}/data/meta"
    )


def build_frame_metadata(job):
    """
    Build:

        frame_number -> {
            name,
            width,
            height
        }
    """
    job_id = job["id"]

    metadata = get_job_metadata(job_id)

    frames = metadata.get("frames") or []

    start_frame = metadata.get(
        "start_frame",
        job.get("start_frame", 0)
    )

    included_frames = metadata.get(
        "included_frames"
    )

    frame_map = {}

    if included_frames:
        frame_numbers = included_frames
    else:
        frame_numbers = list(
            range(
                int(start_frame or 0),
                int(
                    metadata.get(
                        "stop_frame",
                        job.get("stop_frame", -1)
                    )
                ) + 1
            )
        )

    for index, frame_info in enumerate(frames):

        if index >= len(frame_numbers):
            break

        frame_number = int(
            frame_numbers[index]
        )

        frame_map[frame_number] = {
            "name": frame_info.get(
                "name",
                ""
            ),
            "width": frame_info.get(
                "width",
                0
            ),
            "height": frame_info.get(
                "height",
                0
            )
        }

    # Fallback if CVAT doesn't return frame metadata.
    if not frame_map:
        start = int(
            job.get("start_frame", 0)
        )

        stop = int(
            job.get("stop_frame", start)
        )

        for frame_number in range(
            start,
            stop + 1
        ):
            frame_map[frame_number] = {
                "name": "",
                "width": 0,
                "height": 0
            }

    return frame_map


def get_job_annotations(job_id):
    """
    Get annotations belonging only to this job.
    """
    return request_json(
        "GET",
        f"/api/jobs/{job_id}/annotations/"
    )


def build_label_map(task):
    """
    Build a reliable CVAT label-id -> label-name map.

    Do not iterate over task["labels"] directly: on newer CVAT versions
    that field can be a LabelsSummary rather than the actual label list.
    The Labels API provides the concrete label objects.
    """

    task_id = int(task["id"])

    labels = get_paginated(
        "/api/labels",
        params={
            "task_id": task_id,
            "page_size": 100,
        }
    )

    # Some CVAT setups expose inherited project labels more reliably through
    # project_id, so use it as a fallback if task_id returns no labels.
    if not labels and task.get("project_id") is not None:
        labels = get_paginated(
            "/api/labels",
            params={
                "project_id": int(task["project_id"]),
                "page_size": 100,
            }
        )

    label_map = {}

    for label in labels:
        if not isinstance(label, dict):
            continue

        label_id = label.get("id")
        label_name = label.get("name")

        if label_id is not None:
            label_map[int(label_id)] = (
                label_name or f"class_{label_id}"
            )

    print(
        f"Labels available: {len(label_map)}"
    )

    if not label_map:
        print(
            "WARNING: No labels were returned by /api/labels. "
            "Annotations may be exported with fallback class names."
        )

    return label_map
