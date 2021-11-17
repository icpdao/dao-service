import os
import traceback
import graphene
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

import settings
import sentry_sdk

from fastapi import FastAPI, Request
from mangum import Mangum
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.aws_lambda import AwsLambdaIntegration

from app.common.utils.base_graphql import BaseGraphQLApp
from app.common.utils.route_helper import find_current_user, path_join
from app.common.models.icpdao import init_mongo
from app.routes import Query, Mutations
from app.common.schema.icpdao import UserSchema, DAOSchema, DAOJobConfigSchema
from app.routes.webhooks import GithubWebhooksApp

prefix = ''
if os.environ.get('IS_UNITEST') != 'yes':
    prefix = settings.API_GATEWAY_BASE_PATH
graph_route = path_join(prefix, '/graph')
webhooks_route = path_join(prefix, '/github/webhooks')

graph_schema = graphene.Schema(
    query=Query, mutation=Mutations,
    types=[UserSchema, DAOSchema, DAOJobConfigSchema])

app = FastAPI()

app.add_route(graph_route, BaseGraphQLApp(
    schema=graph_schema
))

app.add_route(webhooks_route, GithubWebhooksApp())

if settings.ICPDAO_APP_ENV != "TEST":
    sentry_sdk.init(
        dsn=settings.ICPDAO_SENTRY_DSN,
        environment=settings.ICPDAO_APP_ENV,
        integrations=[AwsLambdaIntegration()],
        traces_sample_rate=1.0
    )
    app.add_middleware(SentryAsgiMiddleware)


class UNAUTHError(Exception):
    pass


def set_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers[
        "Access-Control-Allow-Headers"] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Amz-User-Agent"
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
    find_current_user(request)
    try:
        response = await call_next(request)
    except Exception as ex:
        if os.environ.get('IS_UNITEST') == 'yes':
            raise ex

        msg = traceback.format_exc()
        print('exception log_exception' + str(ex))
        print(msg)

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
