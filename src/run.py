from fastapi import Depends, FastAPI

from src.api import include_routers
from src.api.deps import check_api_key
from src.api.v1 import routers as v1_routers
from src.middleware import include_middlewares, middlewares

app = FastAPI(title='Payments service')
include_middlewares(app, *middlewares)
include_routers(
    app,
    *v1_routers,
    prefix='/api/v1',
    dependencies=[Depends(check_api_key)],
)


@app.get('/health', include_in_schema=False)
async def health() -> dict[str, str]:
    return {'status': 'ok'}