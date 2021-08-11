import time
import os
import random

from graphene import ObjectType, String, Field, Int, \
    Float, List, Boolean, Mutation
from graphql.execution.executor import ResolveInfo
from mongoengine import Q

from app.common.models.icpdao.user import UserStatus, User
from app.common.models.logic.user_helper import pre_icpper_to_icpper
from settings import ICPDAO_GITHUB_APP_ID, ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY, ICPDAO_GITHUB_APP_NAME

from app.routes.cycles import CyclesQuery
from app.common.models.icpdao.dao import DAO as DAOModel, DAOJobConfig
from app.common.models.icpdao.dao import DAOFollow as DAOFollowModel
from app.common.models.icpdao.job import Job as JobModel
from app.common.schema.icpdao import DAOSchema
from app.common.models.icpdao.user_github_token import UserGithubToken
from app.common.utils.access import check_is_icpper, check_is_dao_owner
from app.common.utils.route_helper import get_current_user_by_graphql
from app.common.utils.github_rest_api import org_member_role_is_admin, check_icp_app_installed_status_of_org, get_icp_app_jwt, get_github_org_id
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum, CycleFilterEnum, CyclesQueryArgs
from app.routes.follow import DAOFollowUDSchema


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


def get_github_owner_app_info(user, github_owner_name):
    github_org_id = None
    is_icp_app_installed = False
    is_github_org_owner = False

    ugt = UserGithubToken.objects(github_user_id=user.github_user_id).first()
    access_token = ugt.access_token
    github_login = user.github_login

    github_org_id = get_github_org_id(access_token, github_owner_name)
    jwt = get_icp_app_jwt(ICPDAO_GITHUB_APP_ID, ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY)
    is_icp_app_installed = check_icp_app_installed_status_of_org(jwt, github_owner_name)

    if is_icp_app_installed:
        is_github_org_owner = org_member_role_is_admin(access_token, github_owner_name, github_login)
    else:
        # 当 app 没有安装时，查不多用户信息，干脆直接设置为 false
        is_github_org_owner = False

    return github_org_id, is_icp_app_installed, is_github_org_owner


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

    @staticmethod
    def resolve_datum(parent, info):
        return parent.datum

    @staticmethod
    def resolve_stat(parent, info):
        # TODO:is mock
        return DAOStat(following=0, job=0, size=0, token=0)

    @staticmethod
    def resolve_is_following(parent, info):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')

        obj = DAOFollowModel.objects(dao_id=str(parent.datum.id), user_id=str(current_user.id)).first()
        return not not obj

    @staticmethod
    def resolve_is_owner(parent, info):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        return str(current_user.id) == parent.datum.owner_id


class DAO(ObjectType):
    datum = Field(DAOSchema)
    following = Field(DAOFollowUDSchema)
    cycles = Field(CyclesQuery, filter=CycleFilterEnum())

    def get_query(self, info, id=None, name=None):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        if not id and not name:
            raise ValueError('NO FILTER')
        _filter = {}
        if id:
            _filter['id'] = id
        if name:
            _filter['name'] = name

        query = DAOModel.objects(**_filter).first()
        setattr(self, 'query', query)
        return self

    @staticmethod
    def resolve_datum(parent, info):
        dao = getattr(parent, 'query')
        if not dao:
            raise ValueError('NOT FOUND DAO')
        return dao

    @staticmethod
    def resolve_following(parent, info):
        dao = getattr(parent, 'query')
        return DAOFollowUDSchema(dao_id=str(dao.id))

    @staticmethod
    def resolve_cycles(parent, info, filter=None):
        dao = getattr(parent, 'query')

        return CyclesQuery(_args=CyclesQueryArgs(
          dao_id=str(dao.id), filter=filter))


class DAOs(ObjectType):
    dao = List(DAOItem)
    stat = Field(DAOsStat)
    total = Int()

    def get_query_dao_list(self, info, **kwargs):
        current_user = get_current_user_by_graphql(info)
        query_user = current_user
        query_user_name = kwargs.get('user_name')
        if query_user_name:
            user = User.objects(github_login=query_user_name).first()
            if not user:
                raise PermissionError("userName'USER NOT FOUND")
            query_user = user

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
                if not query_user:
                    raise PermissionError('NOT LOGIN')
            if _filter == DAOsFilterEnum.owner:
                query = Q(owner_id=str(query_user.id))
            if _filter == DAOsFilterEnum.following:
                dao_id_list = [item.dao_id for item in DAOFollowModel.objects(user_id=str(query_user.id))]
                query = Q(id__in=dao_id_list)
            if _filter == DAOsFilterEnum.following_and_owner:
                dao_id_list = [item.dao_id for item in DAOFollowModel.objects(user_id=str(query_user.id))]
                query = (Q(owner_id=str(query_user.id)) | Q(id__in=dao_id_list))
            if _filter == DAOsFilterEnum.member:
                dao_id_list = JobModel.objects(user_id=str(query_user.id)).distinct('dao_id')
                query = Q(id__in=dao_id_list)

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
        setattr(self, 'query_list', query_dao_list)
        return self

    def resolve_dao(self, info):
        return [DAOItem(datum=item) for item in self.query_list]

    def resolve_stat(self, info):
        # TODO is mock
        dao_ids = {str(item.id) for item in self.query_list}

        icpper = JobModel.objects(dao_id__in=dao_ids).distinct('user_id')
        size = JobModel.objects(dao_id__in=dao_ids).sum('size')
        return DAOsStat(icpper=len(icpper), size=size, income=0)

    def resolve_total(self, info):
        return self.query_list.count()


class CreateDAO(Mutation):
    """
    example: https://docs.graphene-python.org/en/latest/types/mutations/
    """
    class Arguments:
        name = String(required=True)
        desc = String(required=True)
        logo = String(required=True)
        time_zone = Int(required=True)
        time_zone_region = String(required=True)

    dao = Field(DAOSchema)

    @staticmethod
    def mutate(root, info: ResolveInfo, **kwargs):
        current_user = get_current_user_by_graphql(info)
        if not current_user or current_user.status == UserStatus.NORMAL.value:
            raise PermissionError('NO ROLE')

        # TODO: mock test data
        if os.environ.get('IS_UNITEST') != 'yes':
            github_org_id, is_icp_app_installed, is_github_org_owner = get_github_owner_app_info(current_user, kwargs['name'])

            if not is_icp_app_installed or not is_github_org_owner:
                raise ValueError("NOT ROLE")
        else:
            github_org_id = _get_github_user_id(kwargs['name'])

        record = DAOModel(
            github_owner_id=github_org_id,
            github_owner_name=kwargs['name'],
            name=kwargs['name'], logo=kwargs['logo'],
            desc=kwargs['desc'], owner_id=str(current_user.id)
        )
        record.save()
        DAOJobConfig(
            dao_id=str(record.id), time_zone=kwargs['time_zone'],
            time_zone_region=kwargs['time_zone_region']
        ).save()
        pre_icpper_to_icpper(str(current_user.id))
        return CreateDAO(dao=record)


class UpdateDAOBaseInfo(Mutation):
    class Arguments:
        id = String(required=True)
        desc = String()
        logo = String()

    dao = Field(DAOSchema)

    @staticmethod
    def mutate(root, info, id, **kwargs):
        current_user = get_current_user_by_graphql(info)
        dao = DAOModel.objects(id=id).first()
        check_is_dao_owner(current_user, dao=dao)
        for field, value in kwargs.items():
            setattr(dao, field, value)
        if len(kwargs) > 0:
            dao.update_at = int(time.time())
        dao.save()
        return UpdateDAOBaseInfo(dao=dao)


class DAOGithubAppStatus(ObjectType):
    github_app_name = String()
    github_org_id = Int()
    is_exists = Boolean()
    is_github_org_owner = Boolean()
    is_icp_app_installed = Boolean()

    def get(self, info, name):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')

        if os.environ.get('IS_UNITEST') == 'yes':
            self.github_app_name = "icpdao-test"
            self.github_org_id = 0
            self.is_exists = True
            self.is_github_org_owner = True
            self.is_icp_app_installed = True
            return self

        self.github_app_name = ICPDAO_GITHUB_APP_NAME

        ugt = UserGithubToken.objects(github_user_id=current_user.github_user_id).first()

        github_org_id, is_icp_app_installed, is_github_org_owner = get_github_owner_app_info(current_user, name)

        dao = DAOModel.objects(name=name).first()
        self.is_exists = not not dao

        self.github_org_id = github_org_id
        self.is_icp_app_installed = is_icp_app_installed
        self.is_github_org_owner = is_github_org_owner

        return self
