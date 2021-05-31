from graphene import ObjectType, String, Field, Int

from app.common.models.icpdao.dao import DAOJobConfig as DAOJobConfigModel
from app.common.schema.icpdao import DAOJobConfigSchema
from app.common.utils.route_helper import get_current_user_by_graphql
from app.routes.config import UpdateDAOJobConfig
from app.routes.daos import DAOs, CreateDAO, DAO, UpdateDAOBaseInfo
from app.routes.follow import UpdateDAOFollow
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum


class Query(ObjectType):
    daos = Field(
        DAOs,
        filter=DAOsFilterEnum(),
        sorted=DAOsSortedEnum(),
        sorted_type=DAOsSortedTypeEnum(),
        search=String(),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )

    dao = Field(
        DAO,
        id=String(required=True)
    )

    dao_job_config = Field(
        DAOJobConfigSchema,
        dao_id=String(required=True)
    )

    @staticmethod
    def resolve_daos(root, info, **kwargs):
        return DAOs().get_query_dao_list(info, **kwargs)

    @staticmethod
    def resolve_dao_job_config(root, info, dao_id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        record = DAOJobConfigModel.objects(dao_id=dao_id).first()
        return record

    @staticmethod
    def resolve_dao(root, info, id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        return DAO(datum={"id": id}, following={"dao_id": id})


class Mutations(ObjectType):
    create_dao = CreateDAO.Field()
    update_dao_job_config = UpdateDAOJobConfig.Field()
    update_dao_follow = UpdateDAOFollow.Field()
    update_dao_base_info = UpdateDAOBaseInfo.Field()

