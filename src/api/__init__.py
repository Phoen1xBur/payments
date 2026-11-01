from fastapi import APIRouter, FastAPI


def include_routers(
    parent: FastAPI | APIRouter,
    *routers: APIRouter,
    prefix: str = '',
    dependencies: list | None = None,
) -> None:
    for router in routers:
        parent.include_router(router, prefix=prefix, dependencies=dependencies or [])