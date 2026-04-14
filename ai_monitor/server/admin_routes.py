from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from ai_monitor.machines import create_machine, list_machines, revoke_machine

router = APIRouter(prefix="/api/admin")


class CreateMachineRequest(BaseModel):
    label: str

    model_config = ConfigDict(extra="forbid")


def _require_admin(request: Request) -> None:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    if header.removeprefix("Bearer ").strip() != request.app.state.config.admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


@router.get("/machines")
def get_machines(request: Request) -> dict[str, object]:
    _require_admin(request)
    machines = list_machines(request.app.state.config.database_path)
    return {"machines": [machine.__dict__ for machine in machines]}


@router.post("/machines", status_code=status.HTTP_201_CREATED)
def post_machine(request: Request, payload: CreateMachineRequest) -> dict[str, object]:
    _require_admin(request)
    machine, api_key = create_machine(request.app.state.config.database_path, payload.label)
    return {"machine": machine.__dict__, "api_key": api_key}


@router.post("/machines/{machine_id}/revoke")
def post_revoke_machine(request: Request, machine_id: int) -> dict[str, object]:
    _require_admin(request)
    machine = revoke_machine(request.app.state.config.database_path, machine_id)
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return {"machine": machine.__dict__}
