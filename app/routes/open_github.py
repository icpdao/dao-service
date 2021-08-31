from graphene import ObjectType, JSONString

from app.routes.schema import OpenGithubWayEnum


class OpenGithubQuery(ObjectType):
    way = OpenGithubWayEnum()
    data = JSONString()


