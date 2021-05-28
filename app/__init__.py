import os

import graphene
import settings

from fastapi import FastAPI, Request
from mangum import Mangum
from fastapi.responses import PlainTextResponse, JSONResponse

from app.common.utils.base_graphql import BaseGraphQLApp
from app.common.utils.route_helper import find_current_user, path_join
from app.common.models.icpdao import init_mongo
from app.routes import Query, Mutations
from app.common.schema.icpdao import UserSchema, DAOSchema, DAOJobConfigSchema


prefix = ''
if os.environ.get('IS_UNITEST') != 'yes':
    prefix = settings.API_GATEWAY_BASE_PATH
graph_route = path_join(prefix, '/graph')
graph_schema_route = path_join(prefix, '/graph/schema')

graph_schema = graphene.Schema(
    query=Query, mutation=Mutations,
    types=[UserSchema, DAOSchema, DAOJobConfigSchema])

app = FastAPI()

app.add_route(graph_route, BaseGraphQLApp(
    schema=graph_schema
))

app.add_route(graph_schema_route, PlainTextResponse(
    status_code=200, content=str(graph_schema)
), methods=['GET'])


class UNAUTHError(Exception):
    pass


def set_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent"
    response.headers["Access-Control-Allow-Methods"] = "OPTIONS,DELETE,GET,HEAD,PATCH,POST,PUT"


def build_response(status_code, content):
    response = JSONResponse(
        status_code=status_code,
        content=content
    )
    set_cors(response)
    return response


@app.middleware("http")
async def add_global_process(request: Request, call_next):
    user = find_current_user(request)

    if request.method == 'POST' and not user:
        return build_response(200, {
            "success": False,
            "errorCode": "401",
            "errorMessage": 'UNAUTHError',
        })

    try:
        response = await call_next(request)
    except Exception as ex:
        if os.environ.get('IS_UNITEST') == 'yes':
            raise ex

        return build_response(200, {
            "success": False,
            "errorCode": "500",
            "errorMessage": str(ex),
        })

    set_cors(response)
    return response

handler = Mangum(app)

init_mongo({
    'icpdao': {
        'host': settings.ICPDAO_MONGODB_ICPDAO_HOST,
        'alias': 'icpdao',
    }
})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app='app:app', port=8087, reload=True)
