from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from .request_id import RequestIdMiddleware

middlewares = (
    RequestIdMiddleware,
)


def include_middlewares(app: FastAPI, *middlewares: type[BaseHTTPMiddleware]) -> None:
    for middleware in middlewares:
        app.add_middleware(middleware)
