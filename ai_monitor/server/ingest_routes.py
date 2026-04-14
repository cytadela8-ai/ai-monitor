from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from ai_monitor.ingestion.snapshots import SnapshotPayload
from ai_monitor.machines import authenticate_machine_key

router = APIRouter(prefix="/api/ingest")


def _require_machine(request: Request) -> int:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    auth = authenticate_machine_key(
        request.app.state.config.database_path,
        header.removeprefix("Bearer ").strip(),
    )
    if auth.status == "missing":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid machine key")
    if auth.status == "inactive" or auth.machine is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Machine key revoked")
    return auth.machine.id


@router.post("/snapshot")
def post_snapshot(request: Request, payload: dict[str, object]) -> dict[str, object]:
    machine_id = _require_machine(request)
    try:
        snapshot_payload = SnapshotPayload.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc
    report = request.app.state.ingestion_service.replace_snapshot(
        machine_id=machine_id,
        snapshot=snapshot_payload.to_snapshot(),
        refresh_source="remote_push",
    )
    return {
        "last_refreshed_at": report.refreshed_at.isoformat(),
        "machine_id": report.machine_id,
        "provider_count": report.provider_count,
        "conversation_count": report.conversation_count,
        "prompt_event_count": report.prompt_event_count,
    }
