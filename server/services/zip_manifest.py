"""Build media ZIPs with an explicit alarm-to-file manifest."""
from __future__ import annotations

import copy
import json
import shutil
import zipfile
from pathlib import Path
from tempfile import SpooledTemporaryFile

from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool

from server.services import timeutil


def alarm_entry(alarm_id: str, alarm=None) -> dict:
    return {
        "alarm_id": alarm_id,
        "alarm_time": timeutil.to_iso_local(alarm.alarm_time) if alarm else None,
        "workshop": alarm.workshop if alarm else None,
        "files": [],
        "skipped_files": [],
        "reason": None if alarm else "alarm_not_found",
    }


def build_archive(items: list[tuple[str, Path]], entries: list[dict], media_type: str):
    """Stage each source before writing so read failures cannot leave partial members."""
    archive = SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    entries = copy.deepcopy(entries)
    outcomes: dict[str, str | None] = {}
    sources: dict[str, Path] = {}
    compression = zipfile.ZIP_STORED if media_type == "videos" else zipfile.ZIP_DEFLATED
    try:
        with zipfile.ZipFile(archive, "w", compression=compression) as zf:
            for name, path in items:
                if name in sources:
                    if sources[name] != path.resolve():
                        raise ValueError(f"Conflicting ZIP member: {name}")
                    continue
                sources[name] = path.resolve()
                with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as staged:
                    try:
                        with path.open("rb") as source:
                            shutil.copyfileobj(source, staged, length=512 * 1024)
                    except OSError:
                        outcomes[name] = "file_read_error"
                        continue
                    staged.seek(0)
                    with zf.open(name, "w", force_zip64=True) as destination:
                        shutil.copyfileobj(staged, destination, length=512 * 1024)
                outcomes[name] = None

            for entry in entries:
                included = []
                for file in entry["files"]:
                    reason = outcomes.get(file["path"], "file_read_error")
                    if reason is None:
                        included.append(file)
                    else:
                        entry["skipped_files"].append({"seq": file.get("seq"), "reason": reason})
                entry["files"] = included
                if included:
                    entry["status"] = "partial" if entry["skipped_files"] else "included"
                    entry["reason"] = "some_files_unavailable" if entry["skipped_files"] else None
                else:
                    entry["status"] = "skipped"
                    if not entry["reason"]:
                        entry["reason"] = (entry["skipped_files"][0]["reason"]
                                           if entry["skipped_files"] else "no_files")

            manifest = {
                "schema_version": 1,
                "media_type": media_type,
                "generated_at": timeutil.to_iso_local(timeutil.now_local()),
                "requested_alarm_ids": [entry["alarm_id"] for entry in entries],
                "file_count": sum(reason is None for reason in outcomes.values()),
                "items": entries,
            }
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.seek(0)
        return archive, manifest
    except BaseException:
        archive.close()
        raise


async def zip_response(items, entries, media_type, filename, headers=None):
    # Disk-backed spooling avoids holding a large video batch in memory.
    archive, manifest = await run_in_threadpool(build_archive, items, entries, media_type)

    def chunks():
        try:
            while chunk := archive.read(512 * 1024):
                yield chunk
        finally:
            archive.close()

    response_headers = dict(headers or {})
    response_headers.update({
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Item-Count": str(manifest["file_count"]),
        "X-Manifest-File": "manifest.json",
    })
    if "X-Image-Count" in response_headers:
        response_headers["X-Image-Count"] = str(manifest["file_count"])
    return StreamingResponse(
        chunks(), media_type="application/zip", headers=response_headers,
        background=BackgroundTask(archive.close),
    )
