"""Downloads individual frames from CVAT and names the output images."""


import mimetypes
from pathlib import Path

import requests

from .config import CVAT_TOKEN, CONNECT_TIMEOUT, READ_TIMEOUT, IMAGE_QUALITY
from .http_client import session, api_url
from .utils import safe_name


def get_extension_from_response(
    response,
    original_name=""
):
    """
    Determine image extension.
    """
    original_suffix = Path(
        original_name
    ).suffix

    if original_suffix:
        return original_suffix

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).split(";")[0].strip()

    extension = mimetypes.guess_extension(
        content_type
    )

    return extension or ".jpg"


def make_output_image_name(
    job_id,
    frame_number,
    original_name,
    extension
):
    """
    Create a deterministic image name.

    Example:

        frame_000409_camera01.jpg
    """
    original_base = Path(
        original_name
    ).stem

    if original_base:
        original_base = safe_name(
            original_base
        )

        return (
            f"job_{job_id}_frame_{frame_number:06d}_"
            f"{original_base}{extension}"
        )

    return (
        f"job_{job_id}_frame_{frame_number:06d}"
        f"{extension}"
    )


def download_frame(
    job_id,
    frame_number,
    frame_metadata,
    output_file
):
    """
    Download one exact frame from CVAT.
    """

    url = api_url(
        f"/api/jobs/{job_id}/data"
    )

    headers = {
        "Authorization": f"Bearer {CVAT_TOKEN}",
        "Accept": "*/*",
    }

    try:
        response = session.get(
            url,
            params={
                "type": "frame",
                "number": frame_number,
                "quality": IMAGE_QUALITY
            },
            headers=headers,
            stream=True,
            timeout=(
                CONNECT_TIMEOUT,
                READ_TIMEOUT
            )
        )

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Failed to download Job {job_id}, "
            f"Frame {frame_number}: {exc}"
        ) from exc

    if not response.ok:
        raise RuntimeError(
            f"Failed to download Job {job_id}, "
            f"Frame {frame_number}\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text[:1000]}"
        )

    extension = get_extension_from_response(
        response,
        frame_metadata.get("name", "")
    )

    image_name = make_output_image_name(
        job_id,
        frame_number,
        frame_metadata.get("name", ""),
        extension
    )

    output_file = Path(output_file)

    with output_file.open("wb") as file:
        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if chunk:
                file.write(chunk)

    return image_name
