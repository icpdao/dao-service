from graphene import ObjectType, String, Field, Int
from mongoengine import Q

from app.common.models.icpdao.dao import DAOJobConfig as DAOJobConfigModel
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.dao import DAOFollow as DAOFollowModel
from app.common.schema.icpdao import DAOJobConfigSchema
from app.common.utils.access import check_is_dao_owner
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
        current_user = get_current_user_by_graphql(info)

        _filter = kwargs.get('filter')
        _sorted = kwargs.get('sorted')
        _sorted_type = kwargs.get('sorted_type')
        _search = kwargs.get('search')
        _offset = kwargs.get('offset')
        _first = kwargs.get('first')

        query = None
        sort_string = None
        search = None
        if _filter:
            if _filter != DAOsFilterEnum.all:
                if not current_user:
                    raise PermissionError('NOT LOGIN')
            if _filter == DAOsFilterEnum.owner:
                query = Q(owner_id=str(current_user.id))
            if _filter == DAOsFilterEnum.following:
                dao_id_list = [item.dao_id for item in DAOFollowModel.objects(user_id=str(current_user.id))]
                query = Q(id__in=dao_id_list)
            if _filter == DAOsFilterEnum.following_and_owner:
                dao_id_list = [item.dao_id for item in DAOFollowModel.objects(user_id=str(current_user.id))]
                query = (Q(owner_id=str(current_user.id)) | Q(id__in=dao_id_list))

        if _search:
            if query:
                query = query & Q(name__contains=_search)
            else:
                query = Q(name__contains=_search)

        if _sorted is not None or _sorted_type is not None:
            if _sorted is None:
                _sorted = DAOsSortedEnum.number
            if _sorted_type is None:
                _sorted_type = DAOsSortedTypeEnum.asc

            # TODO 目前只支持 number 排序
            if _sorted == DAOsSortedEnum.number:
                sort_string = 'number'
            if _sorted_type == DAOsSortedTypeEnum.desc:
                sort_string = '-{}'.format(sort_string)

        if query:
            query_dao_list = DAOModel.objects(query)
        else:
            query_dao_list = DAOModel.objects
        if sort_string:
            query_dao_list = query_dao_list.order_by(sort_string)

        query_dao_list = query_dao_list.limit(_first).skip(_offset)
        return DAOs(dao=query_dao_list)

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

