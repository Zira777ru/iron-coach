"""Fitbit OAuth2 + data fetching."""
import json
import httpx
from datetime import date
from config import settings

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"
FITBIT_API = "https://api.fitbit.com/1"
SCOPE = "activity heartrate nutrition sleep weight"


def get_auth_url(redirect_uri: str, state: str = "") -> str:
    params = (
        f"response_type=code"
        f"&client_id={settings.fitbit_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={SCOPE.replace(' ', '%20')}"
        f"&state={state}"
    )
    return f"{FITBIT_AUTH_URL}?{params}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": settings.fitbit_client_id,
            },
            auth=(settings.fitbit_client_id, settings.fitbit_client_secret),
        )
        r.raise_for_status()
    return r.json()


async def refresh_token(token_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            FITBIT_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token_data["refresh_token"],
                "client_id": settings.fitbit_client_id,
            },
            auth=(settings.fitbit_client_id, settings.fitbit_client_secret),
        )
        r.raise_for_status()
    return r.json()


class FitbitClient:
    def __init__(self, token_data: dict):
        self.token = token_data

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token['access_token']}"}

    async def _get(self, path: str) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{FITBIT_API}{path}", headers=self._headers(), timeout=30)
            r.raise_for_status()
        return r.json()

    async def get_steps(self, target_date: str = "today") -> int:
        data = await self._get(f"/user/-/activities/steps/date/{target_date}/1d.json")
        return int(data["activities-steps"][0]["value"])

    async def get_daily_summary(self, target_date: str = "today") -> dict:
        data = await self._get(f"/user/-/activities/date/{target_date}.json")
        summary = data.get("summary", {})
        return {
            "steps": summary.get("steps", 0),
            "calories_out": summary.get("caloriesOut", 0),
            "active_minutes": summary.get("fairlyActiveMinutes", 0) + summary.get("veryActiveMinutes", 0),
        }

    async def get_sleep(self, target_date: str = "today") -> dict:
        data = await self._get(f"/user/-/sleep/date/{target_date}.json")
        summary = data.get("summary", {})
        return {
            "total_minutes": summary.get("totalMinutesAsleep", 0),
            "efficiency": summary.get("efficiency", 0),
        }

    async def get_heart_rate(self, target_date: str = "today") -> int | None:
        try:
            data = await self._get(f"/user/-/activities/heart/date/{target_date}/1d.json")
            return data["activities-heart"][0]["value"].get("restingHeartRate")
        except Exception:
            return None

    async def get_weight(self, target_date: str = "today") -> float | None:
        try:
            data = await self._get(f"/user/-/body/weight/date/{target_date}/1d.json")
            logs = data.get("body-weight", [])
            return float(logs[-1]["value"]) if logs else None
        except Exception:
            return None
