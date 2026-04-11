from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.minio_client import minio_client

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/browse")
async def browse_storage(
    prefix: str = "",
    current_user: User = Depends(get_current_user),
):
    """List objects in MinIO bucket with given prefix.

    Returns folders and files with metadata.
    """
    try:
        objects = minio_client.list_objects(prefix=prefix)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to list storage objects: {exc}",
        )

    # Separate folders and files
    folders: set[str] = set()
    files: list[dict] = []

    for obj in objects:
        name: str = obj["name"]
        # Determine if this is a "folder" (prefix-only, no real file)
        relative = name[len(prefix):] if name.startswith(prefix) else name
        if "/" in relative:
            folder = relative.split("/")[0] + "/"
            folders.add(prefix + folder if prefix else folder)
        else:
            files.append(
                {
                    "name": name,
                    "size": obj["size"],
                    "last_modified": obj["last_modified"].isoformat()
                    if obj["last_modified"]
                    else None,
                }
            )

    return {
        "prefix": prefix,
        "folders": sorted(folders),
        "files": files,
    }


@router.get("/download")
async def download_file(
    path: str,
    current_user: User = Depends(get_current_user),
):
    """Return a presigned download URL for the specified object."""
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path parameter is required",
        )

    if not minio_client.object_exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{path}' not found",
        )

    try:
        url = minio_client.presign_url(path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate download URL: {exc}",
        )

    return {"url": url, "path": path}


@router.delete("/")
async def delete_file(
    path: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a file from MinIO."""
    if not path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path parameter is required",
        )

    if not minio_client.object_exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Object '{path}' not found",
        )

    try:
        minio_client.delete_object(path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete object: {exc}",
        )

    return {"status": "deleted", "path": path}
