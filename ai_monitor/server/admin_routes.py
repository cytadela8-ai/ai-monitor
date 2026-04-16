from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from ai_monitor.auth import require_admin_session
from ai_monitor.machines import MachineRecord, create_machine, list_machines, revoke_machine
from ai_monitor.server.client_setup import build_client_setup

router = APIRouter(prefix="/api/admin")


class CreateMachineRequest(BaseModel):
    label: str

    model_config = ConfigDict(extra="forbid")


def _machine_response(
    request: Request,
    machine: MachineRecord,
    api_key: str | None = None,
) -> dict[str, object]:
    server_url = str(request.base_url).rstrip("/")
    setup = None
    if not machine.is_local:
        setup = build_client_setup(
            server_url=server_url,
            client_image=request.app.state.config.client_image,
            api_key=api_key,
        ).to_dict()
    return {
        "machine": machine.__dict__,
        "setup": setup,
    }


@router.get("/machines")
def get_machines(request: Request) -> dict[str, object]:
    require_admin_session(request)
    machines = list_machines(request.app.state.config.database_path)
    return {"machines": [_machine_response(request, machine) for machine in machines]}


@router.post("/machines", status_code=status.HTTP_201_CREATED)
def post_machine(request: Request, payload: CreateMachineRequest) -> dict[str, object]:
    require_admin_session(request)
    machine, api_key = create_machine(request.app.state.config.database_path, payload.label)
    response = _machine_response(request, machine, api_key)
    response["api_key"] = api_key
    return response


@router.post("/machines/{machine_id}/revoke")
def post_revoke_machine(request: Request, machine_id: int) -> dict[str, object]:
    require_admin_session(request)
    machine = revoke_machine(request.app.state.config.database_path, machine_id)
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return _machine_response(request, machine)
