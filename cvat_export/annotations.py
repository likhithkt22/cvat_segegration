"""Converts CVAT annotations (shapes, tracks, tags) into LabelMe structures."""


import json


def attributes_to_dict(attributes):
    """
    Convert CVAT attributes into:

        {
            "attribute_name": "value"
        }
    """
    result = {}

    for attribute in attributes or []:
        spec_id = attribute.get(
            "spec_id"
        )

        value = attribute.get(
            "value"
        )

        name = attribute.get(
            "name"
        )

        key = name or f"attribute_{spec_id}"

        result[key] = value

    return result


def cvat_shape_to_labelme(
    shape,
    label_map
):
    """
    Convert a CVAT shape to LabelMe format.

    Supported:
        polygon
        rectangle
        polyline
        points

    Ellipse/cuboid/skeleton/etc. are reported as unsupported.
    """
    shape_type = str(
        shape.get("type", "")
    ).lower()

    label_id = shape.get(
        "label_id"
    )

    label = label_map.get(
        int(label_id)
    ) if label_id is not None else "unknown"

    points = shape.get(
        "points",
        []
    )

    if not isinstance(points, list):
        points = []

    group = shape.get(
        "group"
    )

    if group == 0:
        group = None

    attributes = attributes_to_dict(
        shape.get("attributes")
    )

    description = ""

    if attributes:
        description = json.dumps(
            attributes,
            ensure_ascii=False
        )

    # --------------------------------------------
    # POLYGON
    # --------------------------------------------

    if shape_type == "polygon":

        if len(points) < 6:
            return None

        converted_points = []

        for index in range(
            0,
            len(points) - 1,
            2
        ):
            converted_points.append([
                float(points[index]),
                float(points[index + 1])
            ])

        if len(converted_points) < 3:
            return None

        return {
            "label": label,
            "points": converted_points,
            "group_id": group,
            "description": description,
            "shape_type": "polygon",
            "flags": {}
        }

    # --------------------------------------------
    # RECTANGLE
    # --------------------------------------------

    if shape_type == "rectangle":

        if len(points) < 4:
            return None

        x1 = float(points[0])
        y1 = float(points[1])
        x2 = float(points[2])
        y2 = float(points[3])

        return {
            "label": label,
            "points": [
                [x1, y1],
                [x2, y2]
            ],
            "group_id": group,
            "description": description,
            "shape_type": "rectangle",
            "flags": {}
        }

    # --------------------------------------------
    # POLYLINE
    # --------------------------------------------

    if shape_type == "polyline":

        converted_points = []

        for index in range(
            0,
            len(points) - 1,
            2
        ):
            converted_points.append([
                float(points[index]),
                float(points[index + 1])
            ])

        if len(converted_points) < 2:
            return None

        return {
            "label": label,
            "points": converted_points,
            "group_id": group,
            "description": description,
            "shape_type": "line",
            "flags": {}
        }

    # --------------------------------------------
    # POINTS
    # --------------------------------------------

    if shape_type == "points":

        converted_points = []

        for index in range(
            0,
            len(points) - 1,
            2
        ):
            converted_points.append([
                float(points[index]),
                float(points[index + 1])
            ])

        return {
            "label": label,
            "points": converted_points,
            "group_id": group,
            "description": description,
            "shape_type": "point",
            "flags": {}
        }

    return None


def get_annotations_for_frame(
    annotations,
    frame_number,
    label_map
):
    """
    Extract annotations belonging to one frame.
    """
    shapes = []

    # --------------------------------------------
    # Normal image shapes
    # --------------------------------------------

    for shape in annotations.get(
        "shapes",
        []
    ):
        if int(
            shape.get("frame", -1)
        ) != int(frame_number):
            continue

        converted = cvat_shape_to_labelme(
            shape,
            label_map
        )

        if converted:
            shapes.append(converted)

    # --------------------------------------------
    # Tracks
    # --------------------------------------------

    for track in annotations.get(
        "tracks",
        []
    ):
        label_id = track.get(
            "label_id"
        )

        group = track.get(
            "group"
        )

        if group == 0:
            group = None

        for tracked_shape in track.get(
            "shapes",
            []
        ):

            tracked_frame = tracked_shape.get(
                "frame"
            )

            if tracked_frame is None:
                continue

            if int(tracked_frame) != int(
                frame_number
            ):
                continue

            # Combine track information with
            # tracked shape information.
            shape = dict(
                tracked_shape
            )

            shape["label_id"] = label_id
            shape["group"] = group

            converted = cvat_shape_to_labelme(
                shape,
                label_map
            )

            if converted:
                shapes.append(converted)

    return shapes


def get_tags_for_frame(
    annotations,
    frame_number,
    label_map
):
    """
    LabelMe does not have a direct CVAT-tag equivalent.
    We preserve CVAT tags in the JSON as 'cvatTags'.
    """
    tags = []

    for tag in annotations.get(
        "tags",
        []
    ):
        if int(
            tag.get("frame", -1)
        ) != int(frame_number):
            continue

        label_id = tag.get(
            "label_id"
        )

        tags.append({
            "label": label_map.get(
                int(label_id),
                f"class_{label_id}"
            ),
            "group": tag.get(
                "group"
            ),
            "attributes": attributes_to_dict(
                tag.get("attributes")
            )
        })

    return tags
