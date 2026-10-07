"""Processes one CVAT job: classifies each frame, downloads images, writes JSON."""


from pathlib import Path

from .annotations import get_annotations_for_frame, get_tags_for_frame
from .config import COVERAGE_THRESHOLD
from .coverage import calculate_annotation_coverage
from .cvat_api import build_frame_metadata, get_job_annotations, build_label_map
from .image_download import download_frame
from .writers import create_labelme_json


def process_job(
    job,
    anomaly_map,
    task,
    task_output_folder,
    report_rows,
    processed_anomaly_keys
):
    """
    Process one assigned job.

    Classification:
        1. Calculate annotation coverage.
        2. If coverage < COVERAGE_THRESHOLD:
              ANOMALY - INCOMPLETE_ANNOTATION
        3. If coverage is complete:
              check Excel using (job_id, frame_number)
        4. Excel match:
              ANOMALY - EXCEL
        5. Otherwise:
              COMPLETED

    Excel is therefore a secondary anomaly check for frames that are
    already fully annotated.
    """
    job_id = int(job["id"])

    print("\n" + "=" * 100)
    print(f"PROCESSING JOB {job_id}")
    print("=" * 100)

    start_frame = int(
        job.get("start_frame", 0)
    )

    stop_frame = int(
        job.get("stop_frame", start_frame)
    )

    print(
        f"Frame range: {start_frame} - {stop_frame}"
    )

    frame_map = build_frame_metadata(job)

    print("Getting job annotations...")

    annotations = get_job_annotations(job_id)
    label_map = build_label_map(task)

    # --------------------------------------------------------
    # COMMON PROJECT FOLDERS
    # --------------------------------------------------------
    # All tasks/jobs in this project write into the same:
    #
    # Project/
    #   Completed/
    #     images/
    #     annotations/
    #   Anomaly/
    #     images/
    #     annotations/
    #
    # --------------------------------------------------------

    anomaly_images = (
        Path(task_output_folder)
        / "Anomaly"
        / "images"
    )

    anomaly_annotations = (
        Path(task_output_folder)
        / "Anomaly"
        / "annotations"
    )

    completed_images = (
        Path(task_output_folder)
        / "Completed"
        / "images"
    )

    completed_annotations = (
        Path(task_output_folder)
        / "Completed"
        / "annotations"
    )

    for folder in [
        anomaly_images,
        anomaly_annotations,
        completed_images,
        completed_annotations
    ]:
        folder.mkdir(
            parents=True,
            exist_ok=True
        )

    processed = 0
    anomaly_count = 0
    completed_count = 0

    for frame_number in sorted(frame_map.keys()):

        frame_key = (
            job_id,
            frame_number
        )

        metadata = frame_map[frame_number]

        # ----------------------------------------------------
        # GET CONVERTED ANNOTATIONS FIRST
        # ----------------------------------------------------

        shapes = get_annotations_for_frame(
            annotations,
            frame_number,
            label_map
        )

        tags = get_tags_for_frame(
            annotations,
            frame_number,
            label_map
        )

        image_width = int(
            metadata.get("width", 0) or 0
        )

        image_height = int(
            metadata.get("height", 0) or 0
        )

        coverage_percent, covered_area, image_area, complete = (
            calculate_annotation_coverage(
                shapes,
                image_width,
                image_height
            )
        )

        excel_match = frame_key in anomaly_map

        # ----------------------------------------------------
        # FINAL CLASSIFICATION
        # ----------------------------------------------------

        if not complete:
            category = "Anomaly"
            reason = (
                f"Incomplete annotation; "
                f"coverage={coverage_percent:.4f}% "
                f"(threshold={COVERAGE_THRESHOLD:.2f}%)"
            )

            processed_anomaly_keys.add(frame_key)

            image_folder = anomaly_images
            annotation_folder = anomaly_annotations

        elif excel_match:
            category = "Anomaly"

            excel_reason = "; ".join(
                anomaly_map[frame_key]["reasons"]
            )

            reason = (
                f"Excel anomaly; "
                f"coverage={coverage_percent:.4f}%"
            )

            if excel_reason:
                reason += f"; {excel_reason}"

            processed_anomaly_keys.add(frame_key)

            image_folder = anomaly_images
            annotation_folder = anomaly_annotations

        else:
            category = "Completed"

            reason = (
                f"Fully annotated; "
                f"coverage={coverage_percent:.4f}%"
            )

            image_folder = completed_images
            annotation_folder = completed_annotations

        print(
            f"\rJob {job_id} | Frame {frame_number} | "
            f"Coverage {coverage_percent:.4f}% | "
            f"{category}",
            end="",
            flush=True
        )

        # ----------------------------------------------------
        # DOWNLOAD IMAGE
        # ----------------------------------------------------

        temporary_image = (
            image_folder
            / f".job_{job_id}_frame_{frame_number}.tmp"
        )

        try:
            image_name = download_frame(
                job_id,
                frame_number,
                metadata,
                temporary_image
            )

            final_image = (
                image_folder
                / image_name
            )

            temporary_image.replace(final_image)

        except Exception as exc:

            if temporary_image.exists():
                temporary_image.unlink(
                    missing_ok=True
                )

            print(
                f"\nERROR downloading "
                f"Job {job_id}, Frame {frame_number}:"
            )
            print(exc)

            report_rows.append({
                "job_id": job_id,
                "frame_number": frame_number,
                "category": category,
                "reason": reason,
                "coverage_percent": round(
                    coverage_percent,
                    4
                ),
                "annotation_complete": complete,
                "excel_match": excel_match,
                "image": "",
                "annotation": "",
                "status": "IMAGE_DOWNLOAD_FAILED",
                "message": str(exc)
            })

            continue

        # ----------------------------------------------------
        # LABELME JSON
        # ----------------------------------------------------

        image_stem = Path(image_name).stem

        annotation_name = (
            image_stem + ".json"
        )

        annotation_file = (
            annotation_folder
            / annotation_name
        )

        create_labelme_json(
            image_name=image_name,
            image_width=image_width,
            image_height=image_height,
            shapes=shapes,
            output_file=annotation_file,
            tags=tags
        )

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        report_rows.append({
            "job_id": job_id,
            "frame_number": frame_number,
            "category": category,
            "reason": reason,
            "coverage_percent": round(
                coverage_percent,
                4
            ),
            "annotation_complete": complete,
            "excel_match": excel_match,
            "image": str(final_image),
            "annotation": str(annotation_file),
            "status": "SUCCESS",
            "message": ""
        })

        processed += 1

        if category == "Anomaly":
            anomaly_count += 1
        else:
            completed_count += 1

    print()

    print(
        f"Job {job_id} completed:"
    )
    print(
        f"  Anomaly   : {anomaly_count}"
    )
    print(
        f"  Completed : {completed_count}"
    )
