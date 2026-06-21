"""Wikitor — POC. Backend FastAPI: markdown local + Ollama, sem auth/Azure.

Composition root: monta a app, liga o lifespan e registra as rotas. As camadas
(domain/application/infrastructure/presentation) vivem em seus próprios pacotes.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .application import index_service
from .infrastructure import config
from .presentation.api import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    index_service.rebuild_indices()  # garante índices consistentes ao subir
    yield


app = FastAPI(title="Wikitor POC", lifespan=lifespan)
app.include_router(router)


# ---------- Front-end React (build de produção do Vite) ----------
# Servido só se `webapp/dist` existir (rode `npm run build` no webapp).
# As rotas /api acima têm precedência; o mount em "/" cobre index.html + assets.

if config.WEB_DIR.exists():
    @app.get("/")
    def root():
        return FileResponse(config.WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
