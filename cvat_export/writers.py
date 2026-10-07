"""File writers: LabelMe JSON and CSV reports."""


import csv
import json

from .config import LABELME_VERSION


def create_labelme_json(
    image_name,
    image_width,
    image_height,
    shapes,
    output_file,
    tags=None
):
    """
    Create LabelMe 5.4.1 JSON.
    """
    data = {
        "version": LABELME_VERSION,
        "flags": {},
        "shapes": shapes,
        "imagePath": image_name,
        "imageData": None,
        "imageHeight": int(
            image_height or 0
        ),
        "imageWidth": int(
            image_width or 0
        )
    }

    # Preserve CVAT tags as an additional
    # non-destructive field.
    if tags:
        data["cvatTags"] = tags

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def write_csv_report(
    output_file,
    rows,
    fieldnames
):
    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)
