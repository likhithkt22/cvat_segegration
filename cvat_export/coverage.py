"""Annotation completeness: how much of the image is covered by polygons/rectangles."""


from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from .config import COVERAGE_THRESHOLD


def _labelme_shape_to_polygon(shape):
    """
    Convert a LabelMe-style polygon/rectangle shape into a Shapely polygon.
    Only area-bearing shapes are used for coverage.
    Points and lines do not contribute area.
    """
    shape_type = str(shape.get("shape_type", "")).lower()
    points = shape.get("points") or []

    try:
        if shape_type == "polygon" and len(points) >= 3:
            polygon = Polygon(
                [(float(p[0]), float(p[1])) for p in points]
            )

        elif shape_type == "rectangle" and len(points) >= 2:
            x1, y1 = float(points[0][0]), float(points[0][1])
            x2, y2 = float(points[1][0]), float(points[1][1])

            polygon = box(
                min(x1, x2),
                min(y1, y2),
                max(x1, x2),
                max(y1, y2)
            )

        else:
            return None

        if polygon.is_empty:
            return None

        # Repair small self-intersections / invalid polygon geometry.
        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty:
            return None

        return polygon

    except (TypeError, ValueError, IndexError):
        return None


def calculate_annotation_coverage(shapes, image_width, image_height):
    """
    Calculate how much of the image is covered by annotation geometry.

    IMPORTANT:
      - void is treated like every other area-bearing polygon.
      - void is NOT itself a completion flag.
      - overlapping polygons are counted only once.
      - polygons are clipped to the image boundaries.
      - points and lines do not contribute area.

    Returns:
        coverage_percent, covered_area, image_area, complete
    """
    width = float(image_width or 0)
    height = float(image_height or 0)

    if width <= 0 or height <= 0:
        return 0.0, 0.0, 0.0, False

    image_polygon = box(0, 0, width, height)
    image_area = image_polygon.area

    polygons = []

    for shape in shapes:
        polygon = _labelme_shape_to_polygon(shape)

        if polygon is None:
            continue

        clipped = polygon.intersection(image_polygon)

        if not clipped.is_empty and clipped.area > 0:
            polygons.append(clipped)

    if not polygons:
        return 0.0, 0.0, image_area, False

    covered_geometry = unary_union(polygons)
    covered_area = min(
        float(covered_geometry.area),
        float(image_area)
    )

    coverage_percent = (
        covered_area / image_area
    ) * 100.0

    complete = coverage_percent >= COVERAGE_THRESHOLD

    return (
        coverage_percent,
        covered_area,
        image_area,
        complete
    )
