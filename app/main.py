from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import get_db
from .health import classify_supabase_error
from .routers import auth, me, progress, sync

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()  # gagal cepat bila konfigurasi belum lengkap
    app = FastAPI(
        title="Kenali Batikmu API",
        version="1.0.0",
        description=(
            "Backend online untuk aplikasi Kenali Batikmu: login dan sinkronisasi progres modul, "
            "nilai kuis teori, dan hasil praktikum. Modul, soal kuis, dan pemindai batik tetap offline di aplikasi."
        ),
    )
    if settings.cors_origins:  # hanya perlu untuk build Flutter Web
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    prefix = "/api/v1"
    for r in (auth.router, me.router, progress.router, sync.router):
        app.include_router(r, prefix=prefix)

    @app.get("/health", tags=["sistem"])
    def health():
        return {"status": "ok"}

    @app.get("/health/db", tags=["sistem"])
    def health_db():
        try:
            rows = get_db().table("modules").select("id").limit(1).execute().data or []
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("kenali.health").exception("Cek Supabase gagal")
            reason, hint = classify_supabase_error(exc)
            return JSONResponse(
                status_code=503,
                content={"status": "error", "reason": reason, "detail": hint, "error_type": type(exc).__name__},
            )
        if not rows:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "error",
                    "reason": "seed_kosong",
                    "detail": "Terhubung ke Supabase, tetapi tabel modules kosong. Jalankan db/seed_reference_data.sql.",
                },
            )
        return {"status": "ok"}

    return app


app = create_app()
