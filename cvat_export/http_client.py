"""Shared HTTP session and low-level CVAT API helpers."""


import requests

from .config import CVAT_URL, CVAT_TOKEN, CONNECT_TIMEOUT, READ_TIMEOUT


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update({
    "Authorization": f"Bearer {CVAT_TOKEN}",
    "Accept": "application/vnd.cvat+json",
})


def api_url(path):
    return f"{CVAT_URL.rstrip('/')}/{path.lstrip('/')}"


def request_json(method, path, **kwargs):
    """
    Send a CVAT API request and return JSON.
    """
    url = api_url(path)

    try:
        response = session.request(
            method,
            url,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            **kwargs
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"CVAT request failed: {method} {url}\n{exc}"
        ) from exc

    if not response.ok:
        raise RuntimeError(
            f"CVAT API error: {response.status_code}\n"
            f"URL: {url}\n"
            f"Response: {response.text[:2000]}"
        )

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"CVAT returned non-JSON response for {url}"
        ) from exc


def get_paginated(path, params=None):
    """
    Retrieve all pages from a CVAT paginated endpoint.
    """
    params = dict(params or {})
    params.setdefault("page", 1)
    params.setdefault("page_size", 100)

    results = []

    while True:
        data = request_json("GET", path, params=params)

        page_results = data.get("results", [])

        if not page_results:
            break

        results.extend(page_results)

        if not data.get("next"):
            break

        params["page"] += 1

    return results
