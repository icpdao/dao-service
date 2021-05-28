from graphene import ObjectType, String, Field, Int, \
    Float, List, Boolean, Mutation
from graphql.execution.executor import ResolveInfo
from app.common.models.icpdao.dao import DAO as DAOModel, DAOJobConfig
from app.common.schema.icpdao import DAOSchema
from app.common.utils.access import check_is_icpper
from app.common.utils.route_helper import get_current_user_by_graphql
from app.routes.follow import DAOFollowUDSchema


class DAOStat(ObjectType):
    following = Int()
    job = Int()
    size = Float()
    token = String()


class DAOsStat(ObjectType):
    icpper = Int()
    size = Float()
    income = Float()


class DAOItem(ObjectType):
    datum = Field(DAOSchema)
    stat = Field(DAOStat)
    is_following = Boolean(required=True)
    is_owner = Boolean(required=True)


class DAO(ObjectType):
    datum = Field(DAOSchema)
    following = Field(DAOFollowUDSchema)

    @staticmethod
    def resolve_datum(parent, info):
        dao = DAOModel.objects(id=parent.datum['id']).first()
        if not dao:
            raise ValueError('NOT FOUND DAO')
        return dao

    @staticmethod
    def resolve_following(parent, info):
        return DAOFollowUDSchema(parent.datum)


class DAOs(ObjectType):
    dao = List(DAOItem)
    stat = Field(DAOsStat)
    total = Int()

    @staticmethod
    def resolve_dao(parent):
        # TODO
        return list()


class CreateDAO(Mutation):
    """
    example: https://docs.graphene-python.org/en/latest/types/mutations/
    """
    class Arguments:
        name = String(required=True)
        desc = String(required=True)
        logo = String(required=True)
        time_zone = Int(required=True)

    dao = Field(DAOSchema)

    @staticmethod
    def mutate(root, info: ResolveInfo, **kwargs):
        current_user = get_current_user_by_graphql(info)
        check_is_icpper(current_user)
        # TODO: check github app installed ?
        record = DAOModel(
            name=kwargs['name'], logo=kwargs['logo'],
            desc=kwargs['desc'], owner_id=str(current_user.id)
        )
        record.save()
        DAOJobConfig(
            dao_id=str(record.id), time_zone=kwargs['time_zone']).save()
        return CreateDAO(dao=record)
