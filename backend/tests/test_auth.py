from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from auth import AdminSession, hash_password, require_admin, router
from config import get_settings


class AuthRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = SimpleNamespace(
            admin_username="admin",
            admin_password_hash=hash_password("supersecret"),
            session_secret="test-secret",
            session_ttl_seconds=3600,
            session_cookie_name="novellone_session",
            session_cookie_domain=None,
            session_cookie_secure=False,
            session_cookie_samesite="lax",
        )

        app = FastAPI()
        app.include_router(router)

        @app.get("/protected")
        async def protected(_: AdminSession = Depends(require_admin)) -> dict[str, bool]:
            return {"ok": True}

        app.dependency_overrides[get_settings] = lambda: self.settings

        self.client = TestClient(app)

    def test_login_logout_flow(self) -> None:
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)

        bad_login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        self.assertEqual(bad_login.status_code, 401)

        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "supersecret"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn(self.settings.session_cookie_name, login.cookies)

        protected = self.client.get("/protected")
        self.assertEqual(protected.status_code, 200)
        self.assertEqual(protected.json()["ok"], True)

        logout = self.client.post("/api/auth/logout")
        self.assertEqual(logout.status_code, 200)

        after_logout = self.client.get("/protected")
        self.assertEqual(after_logout.status_code, 401)

    def test_invalid_session_cookie_rejected(self) -> None:
        self.client.cookies.set(self.settings.session_cookie_name, "not-a-valid-token")
        response = self.client.get("/protected")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()

