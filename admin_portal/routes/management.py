"""
Admin-facing management routes that proxy to the core and portal services.
"""
from typing import Any, Dict, Optional
from uuid import UUID
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from admin_portal.config import admin_settings
from admin_portal.dependencies import get_current_admin


router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_current_admin)])


async def _request_core(method: str, path: str, params: Dict[str, Any] | None = None, json: Dict[str, Any] | None = None):
    """
    Helper to call the core service with API key and bubble up errors.
    """
    url = f"{admin_settings.CORE_API_BASE}{path}"
    headers = {"X-API-Key": admin_settings.SERVICE_API_KEY}
    cleaned_params = {k: v for k, v in (params or {}).items() if v is not None}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.request(method, url, params=cleaned_params, json=json, headers=headers)
    return _handle_response(resp)


async def _request_portal(method: str, path: str, json: Dict[str, Any] | None = None):
    """
    Helper to call the doctor portal service with API key (for account provisioning).
    """
    url = f"{admin_settings.PORTAL_API_BASE}{path}"
    headers = {"X-API-Key": admin_settings.SERVICE_API_KEY}
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.request(method, url, json=json, headers=headers)
    return _handle_response(resp)


def _handle_response(resp: httpx.Response):
    if resp.status_code >= 400:
        # Try to preserve detail when possible
        detail = None
        try:
            payload = resp.json()
            detail = payload.get("detail") if isinstance(payload, dict) else payload
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail or "Upstream error")
    if resp.status_code == status.HTTP_204_NO_CONTENT:
        return None
    try:
        return resp.json()
    except Exception:
        return resp.text


# Clinics
@router.get("/clinics")
async def list_clinics(is_active: Optional[bool] = None, skip: int = 0, limit: int = 100):
    return await _request_core("GET", "/api/v1/clinics", params={"is_active": is_active, "skip": skip, "limit": limit})


@router.post("/clinics", status_code=status.HTTP_201_CREATED)
async def create_clinic(payload: Dict[str, Any]):
    return await _request_core("POST", "/api/v1/clinics", json=payload)


@router.put("/clinics/{clinic_id}")
async def update_clinic(clinic_id: UUID, payload: Dict[str, Any]):
    return await _request_core("PUT", f"/api/v1/clinics/{clinic_id}", json=payload)


@router.delete("/clinics/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clinic(clinic_id: UUID, force: bool = False):
    await _request_core("DELETE", f"/api/v1/clinics/{clinic_id}", params={"force": force})
    return None


# Doctors
@router.get("/doctors")
async def list_doctors(clinic_id: Optional[UUID] = None, is_active: Optional[bool] = None, skip: int = 0, limit: int = 100):
    params: Dict[str, Any] = {"clinic_id": str(clinic_id) if clinic_id else None, "is_active": is_active, "skip": skip, "limit": limit}
    return await _request_core("GET", "/api/v1/doctors", params=params)


@router.get("/doctors/{doctor_email}")
async def get_doctor(doctor_email: str):
    return await _request_core("GET", f"/api/v1/doctors/{doctor_email}")


@router.post("/doctors", status_code=status.HTTP_201_CREATED)
async def create_doctor(payload: Dict[str, Any]):
    """
    Create doctor through core API (ensures RAG + calendar watch hooks).
    """
    return await _request_core("POST", "/api/v1/doctors", json=payload)


@router.put("/doctors/{doctor_email}")
async def update_doctor(doctor_email: str, payload: Dict[str, Any]):
    return await _request_core("PUT", f"/api/v1/doctors/{doctor_email}", json=payload)


@router.delete("/doctors/{doctor_email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(doctor_email: str):
    await _request_core("DELETE", f"/api/v1/doctors/{doctor_email}")
    return None


@router.post("/doctors/{doctor_email}/portal-account", status_code=status.HTTP_201_CREATED)
async def provision_portal_account(doctor_email: str, password: Optional[str] = None):
    """
    Provision a doctor portal account via the portal service.
    If password not provided, generate a secure random one and return it to the caller.
    """
    generated = password or secrets.token_urlsafe(14)
    payload = {"email": doctor_email, "password": generated}
    resp = await _request_portal("POST", "/auth/register", json=payload)
    return {"portal_response": resp, "password": generated}
