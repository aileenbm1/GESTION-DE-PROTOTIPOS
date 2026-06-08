from __future__ import annotations

import os

os.environ.setdefault("AI_PROTO_MAX_UPLOAD_MB", "20")

from fastapi.testclient import TestClient

from api.routes import store
from main import app
from storage.file_store import MAX_UPLOAD_MB


def create_project(client: TestClient, name: str) -> str:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_valid_large_multipart(client: TestClient) -> None:
    project_id = create_project(client, "upload-validacion-large")
    try:
        payload = b"\0" * (5 * 1024 * 1024)
        response = client.post(
            f"/api/projects/{project_id}/upload",
            files={"file": ("validacion.mp4", payload, "video/mp4")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "uploaded"
        assert body["upload_path"].endswith(".mp4")
        assert body["logs"]
        print(f"OK valid multipart upload: {len(payload)} bytes")
    finally:
        store.delete_project(project_id)


def test_broken_manual_content_type(client: TestClient) -> None:
    project_id = create_project(client, "upload-content-type-roto")
    try:
        response = client.post(
            f"/api/projects/{project_id}/upload",
            content=b"not-a-valid-multipart-body",
            headers={"content-type": "multipart/form-data"},
        )
        assert response.status_code == 400, response.text
        detail = response.json()["detail"]
        assert "multipart/form-data" in detail
        assert "Content-Type" in detail
        print("OK broken manual Content-Type returns actionable 400")
    finally:
        store.delete_project(project_id)


def test_request_too_large(client: TestClient) -> None:
    project_id = create_project(client, "upload-too-large")
    try:
        declared_size = (MAX_UPLOAD_MB + 1) * 1024 * 1024
        response = client.post(
            f"/api/projects/{project_id}/upload",
            content=b"",
            headers={
                "content-type": "multipart/form-data; boundary=x",
                "content-length": str(declared_size),
            },
        )
        assert response.status_code == 413, response.text
        print(f"OK oversized request rejected: {declared_size} bytes")
    finally:
        store.delete_project(project_id)


def main() -> None:
    client = TestClient(app)
    test_valid_large_multipart(client)
    test_broken_manual_content_type(client)
    test_request_too_large(client)


if __name__ == "__main__":
    main()
