import decimal
import time
import os
import random

from graphene import ObjectType, String, Field, Int, \
    Float, List, Boolean, Mutation, Decimal
from graphql.execution.executor import ResolveInfo
from mongoengine import Q
from collections import defaultdict

from app.common.models.extension.decimal128_field import any_to_decimal
from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask, CycleVotePairTaskStatus
from app.common.models.icpdao.user import UserStatus, User
from app.common.models.logic.user_helper import pre_icpper_to_icpper, check_user_access_token
from app.common.schema import BaseObjectType, BaseObjectArgs
from app.common.schema.incomes import TokenIncomeSchema
from app.common.utils.errors import CYCLE_DAO_LIST_USER_NOT_FOUND_ERROR, DAO_LIST_QUERY_NOT_USER_ERROR, \
    COMMON_NOT_FOUND_DAO_ERROR, COMMON_NOT_PERMISSION_ERROR, COMMON_NOT_AUTH_ERROR, COMMON_PARAMS_INVALID
from app.routes.data_loaders import UserLoader
from app.routes.token_mint_records import TokenMintRecordsQuery, TokenMintSplitInfoQuery
from settings import ICPDAO_GITHUB_APP_ID, ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY, ICPDAO_GITHUB_APP_NAME, ICPDAO_MINT_TOKEN_ETH_CHAIN_ID

from app.routes.cycles import CyclesQuery, JobQuery, JobsQuery, JobStatQuery, CycleQuery
from app.common.models.icpdao.dao import DAO as DAOModel, DAOJobConfig, DAOToken
from app.common.models.icpdao.dao import DAOFollow as DAOFollowModel
from app.common.models.icpdao.job import Job as JobModel, JobStatusEnum, Job
from app.common.schema.icpdao import DAOSchema, UserSchema, DAOTokenSchema
from app.common.models.icpdao.user_github_token import UserGithubToken
from app.common.utils.access import check_is_icpper, check_is_dao_owner
from app.common.utils.route_helper import get_current_user_by_graphql, set_custom_attr_by_graphql
from app.common.utils.github_rest_api import org_member_role_is_admin, check_icp_app_installed_status_of_org, get_icp_app_jwt, get_github_org_id
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum, CycleFilterEnum, CyclesQueryArgs, IcppersQuerySortedEnum, IcppersQuerySortedTypeEnum, \
    JobsQuerySortedEnum, JobsQuerySortedTypeEnum, CommonPaginationArgs, TokenMintRecordStatusEnum, \
    UpdateDaoLastCycleStepEnum
from app.routes.follow import DAOFollowUDSchema
from settings import (
    ICPDAO_GITHUB_APP_CLIENT_ID,
    ICPDAO_GITHUB_APP_CLIENT_SECRET
)


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
        # ??? app ??????????????????????????????????????????????????????????????? false
        is_github_org_owner = False

    return github_org_id, is_icp_app_installed, is_github_org_owner


def get_query_dao_list(info, **kwargs):
    current_user = get_current_user_by_graphql(info)
    query_user = current_user
    query_user_name = kwargs.get('user_name')
    if query_user_name:
        user = User.objects(github_login=query_user_name).first()
        assert user, CYCLE_DAO_LIST_USER_NOT_FOUND_ERROR
        query_user = user

    _filter = kwargs.get('filter')
    _sorted = kwargs.get('sorted')
    _sorted_type = kwargs.get('sorted_type')
    _search = kwargs.get('search')
    _offset = kwargs.get('offset')
    _first = kwargs.get('first')

    token_chain_id = kwargs.get('token_chain_id')

    query = None
    if _filter:
        if _filter != DAOsFilterEnum.all:
            if not query_user:
                raise ValueError(DAO_LIST_QUERY_NOT_USER_ERROR)
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
            query = query & Q(name__icontains=_search)
        else:
            query = Q(name__icontains=_search)

    if query:
        query_dao_list = DAOModel.objects(query)
    else:
        query_dao_list = DAOModel.objects()

    dao_ids = query_dao_list.distinct('_id')

    dao_list = []
    for item in query_dao_list.all():
        following = DAOFollowModel.objects(dao_id=str(item.id)).count()
        job_query = JobModel.objects(dao_id=str(item.id), status__nin=[JobStatusEnum.AWAITING_MERGER.value])
        job = job_query.count()
        size = any_to_decimal(job_query.sum('size'))
        token = any_to_decimal(job_query.sum('incomes.income'))
        dao_list.append(dict(
            following=following, job=job, size=size, token=token, number=item.number, datum=item,
            stat=DAOStat(
                following=following, job=job, size=size, incomes=job_query.group_incomes(token_chain_id=token_chain_id))
        ))

    if _sorted is not None or _sorted_type is not None:
        if _sorted is None:
            _sorted = DAOsSortedEnum.number.value
        if _sorted_type is None:
            _sorted_type = DAOsSortedTypeEnum.asc.value

        dao_list.sort(
            key=lambda x: x[_sorted],
            reverse=False if _sorted_type == DAOsSortedTypeEnum.asc.value else True)

    return dao_list[_offset:_offset+_first], dao_ids


class HomeStats(ObjectType):
    dao = Int()
    icpper = Int()
    size = Decimal()
    income_sum = Field(
        Decimal,
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )
    incomes = Field(
        List(TokenIncomeSchema),
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )

    def get_query(self):
        all_dao_ids = DAOModel.objects().distinct('_id')
        all_dao_ids_str = [str(i) for i in all_dao_ids]
        setattr(self, 'all_dao_ids_str', all_dao_ids_str)
        return self

    @staticmethod
    def resolve_income_sum(parent, info, token_chain_id=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID):
        all_dao_ids_str = getattr(parent, 'all_dao_ids_str')
        return any_to_decimal(Job.objects(dao_id__in=all_dao_ids_str).sum_incomes(token_chain_id))

    @staticmethod
    def resolve_dao(parent, info):
        all_dao_ids_str = getattr(parent, 'all_dao_ids_str')
        return len(all_dao_ids_str)

    @staticmethod
    def resolve_icpper(parent, info):
        all_dao_ids_str = getattr(parent, 'all_dao_ids_str')
        return len(Job.objects(dao_id__in=all_dao_ids_str).distinct('user_id'))

    @staticmethod
    def resolve_size(parent, info):
        all_dao_ids_str = getattr(parent, 'all_dao_ids_str')
        return any_to_decimal(Job.objects(dao_id__in=all_dao_ids_str).sum('size'))

    @staticmethod
    def resolve_incomes(parent, info, token_chain_id):
        all_dao_ids_str = getattr(parent, 'all_dao_ids_str')
        return Job.objects(dao_id__in=all_dao_ids_str).group_incomes(token_chain_id=token_chain_id)


class DAOStat(ObjectType):
    following = Int()
    job = Int()
    size = Decimal()
    incomes = List(TokenIncomeSchema)


class DAOsStat(ObjectType):
    icpper = Int()
    size = Decimal()
    incomes = List(TokenIncomeSchema)


class DAOItem(ObjectType):
    datum = Field(DAOSchema)
    stat = Field(DAOStat, token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID))
    is_following = Boolean(required=True)
    is_owner = Boolean(required=True)
    token_info = Field(
        DAOTokenSchema,
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )

    @staticmethod
    def resolve_datum(parent, info):
        return parent.datum

    @staticmethod
    def resolve_stat(parent, info, token_chain_id):
        following = DAOFollowModel.objects(dao_id=str(parent.datum.id)).count()
        job_query = JobModel.objects(dao_id=str(parent.datum.id), status__nin=[JobStatusEnum.AWAITING_MERGER.value])
        job = job_query.count()
        size = any_to_decimal(job_query.sum('size'))
        return DAOStat(
            following=following, job=job, size=size,
            incomes=job_query.group_incomes(token_chain_id=token_chain_id)
        )

    @staticmethod
    def resolve_is_following(parent, info):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            return False

        obj = DAOFollowModel.objects(dao_id=str(parent.datum.id), user_id=str(current_user.id)).first()
        return not not obj

    @staticmethod
    def resolve_is_owner(parent, info):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            return False
        return str(current_user.id) == parent.datum.owner_id

    @staticmethod
    def resolve_token_info(parent, info, token_chain_id):
        dt = DAOToken.objects(dao_id=str(parent.datum.id), token_chain_id=token_chain_id).first()
        return dt


class IcppersStatQuery(ObjectType):
    icpper_count = Int()
    job_count = Int()
    size = Decimal()
    incomes = List(TokenIncomeSchema)


class ICPPERQuery(BaseObjectType):
    user = Field(lambda: UserSchema)
    job_count = Int()
    size = Decimal()
    income_sum = Decimal()
    incomes = List(TokenIncomeSchema)
    join_time = Int()


class IcppersQuery(BaseObjectType):
    nodes = List(ICPPERQuery)
    stat = Field(IcppersStatQuery)
    total = Int()


class DAO(ObjectType):
    datum = Field(DAOSchema)
    following = Field(DAOFollowUDSchema)
    cycles = Field(CyclesQuery, filter=List(CycleFilterEnum))
    last_cycle = Field(CycleQuery)
    token_info = Field(
        DAOTokenSchema,
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )
    icppers = Field(
        IcppersQuery,
        sorted=IcppersQuerySortedEnum(default_value=0),
        sorted_type=IcppersQuerySortedTypeEnum(default_value=1),
        first=Int(default_value=20),
        offset=Int(default_value=0),
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )
    jobs = Field(
        JobsQuery,
        sorted=JobsQuerySortedEnum(),
        sorted_type=JobsQuerySortedTypeEnum(default_value=0),
        first=Int(default_value=20),
        offset=Int(default_value=0),
        begin_time=Int(),
        end_time=Int(),
        token_chain_id=String(default_value=ICPDAO_MINT_TOKEN_ETH_CHAIN_ID)
    )
    token_mint_records = Field(
        TokenMintRecordsQuery,
        first=Int(default_value=20),
        offset=Int(default_value=0),
        status=List(TokenMintRecordStatusEnum),
        chain_id=String(),
        token_contract_address=String()
    )
    token_mint_split_info = Field(
        TokenMintSplitInfoQuery,
        start_cycle_id=String(required=True),
        end_cycle_id=String(required=True),
    )

    def get_query(self, info, id=None, name=None):
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
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)
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

    @staticmethod
    def resolve_last_cycle(parent, info):
        dao = getattr(parent, 'query')
        current_at = int(time.time())
        cycle = Cycle.objects(dao_id=str(dao.id), vote_end_at__gt=current_at).order_by("begin_at").first()
        if not cycle:
            return None
        return CycleQuery(datum=cycle, cycle_id=str(cycle.id))

    @staticmethod
    def resolve_token_info(parent, info, token_chain_id):
        dao = getattr(parent, 'query')
        dt = DAOToken.objects(dao_id=str(dao.id), token_chain_id=token_chain_id).first()
        return dt

    @staticmethod
    def resolve_icppers(parent, info, sorted_type, first, offset, sorted, token_chain_id):
        dao = getattr(parent, 'query')

        format_sorted_type = 1 if sorted_type == IcppersQuerySortedTypeEnum.asc.value else -1
        format_sorted = IcppersQuerySortedEnum.get(sorted).value

        origin_query = JobModel.objects(
            dao_id=str(dao.id),
            status__nin=[JobStatusEnum.AWAITING_MERGER.value]
        )

        all_icppers_count = len(origin_query.distinct('user_id'))
        all_job_count = origin_query.count()
        all_job_size = any_to_decimal(origin_query.sum('size'))
        all_incomes = origin_query.group_incomes(token_chain_id=token_chain_id)

        job_group_user = JobModel.objects(
            dao_id=str(dao.id),
            status__nin=[JobStatusEnum.AWAITING_MERGER.value]
        ).aggregate([
            {"$sort": {"create_at": 1}},
            {"$group": {
                "_id": "$user_id",
                "size_sum": {"$sum": "$size"},
                "job_count": {"$sum": 1},
                "join_time": {"$first": "$create_at"},
                "income_sum": {"$sum": "$incomes.income"}
            }},
            {"$sort": {format_sorted: format_sorted_type}},
            {"$skip": offset},
            {"$limit": first}
        ])
        job_group_user = list(job_group_user)
        icppers = [jgu['_id'] for jgu in job_group_user]

        user_incomes_query = JobModel.objects(
            dao_id=str(dao.id),
            status__nin=[JobStatusEnum.AWAITING_MERGER.value],
            user_id__in=icppers,
        ).aggregate([
            {"$unwind": "$incomes"},
            {"$match": {"incomes.token_chain_id": token_chain_id}},
            {"$group": {
                "_id": {
                    "user_id": "$user_id",
                    "token_chain_id": "$incomes.token_chain_id",
                    "token_address": "$incomes.token_address",
                    "token_symbol": "$incomes.token_symbol"
                },
                "income_sum": {"$sum": "$incomes.income"},
            }},
            {"$group": {
                "_id": "$_id.user_id",
                "incomes": {"$push": {
                    "token_chain_id": "$_id.token_chain_id",
                    "token_address": "$_id.token_address",
                    "token_symbol": "$_id.token_symbol",
                    "income": "$income_sum"
                }}
            }}
        ])
        user_incomes = {}
        for d in user_incomes_query:
            user_incomes[d['_id']] = d['incomes']

        nodes = []
        user_loader = UserLoader()
        for d in job_group_user:
            nodes.append(ICPPERQuery(
                user=user_loader.load(d['_id']),
                job_count=d['job_count'],
                size=any_to_decimal(d['size_sum']),
                join_time=d['join_time'],
                income_sum=any_to_decimal(d['income_sum']),
                incomes=[TokenIncomeSchema(
                    token_chain_id=r["token_chain_id"],
                    token_address=r["token_address"],
                    token_symbol=r["token_symbol"],
                    income=r["income"]
                ) for r in user_incomes.get(d['_id'], [])]
            ))

        return IcppersQuery(
            nodes=nodes,
            stat=IcppersStatQuery(
                icpper_count=all_icppers_count, job_count=all_job_count,
                size=all_job_size,
                incomes=all_incomes
            ),
            total=all_icppers_count
        )

    @staticmethod
    def _jobs_base_queryset(dao_id, sorted, sorted_type, begin_time, end_time):
        query_dict = {'dao_id': dao_id, 'status__nin': [JobStatusEnum.AWAITING_MERGER.value]}
        if begin_time is not None:
            query_dict['create_at__gte'] = begin_time
        if end_time is not None:
            query_dict['create_at__lte'] = end_time
        query = JobModel.objects.filter(**query_dict)
        if sorted is not None:
            sort_string = JobsQuerySortedEnum.get(sorted).value
            if sorted_type == JobsQuerySortedTypeEnum.desc:
                sort_string = '-{}'.format(sort_string)
            query = query.order_by(sort_string)
        return query

    def resolve_jobs(self, info, sorted_type, first, offset, sorted, token_chain_id, begin_time=None, end_time=None):
        dao = getattr(self, 'query')
        query = self._jobs_base_queryset(
            dao_id=str(dao.id), sorted=sorted, sorted_type=sorted_type, begin_time=begin_time, end_time=end_time)
        return JobsQuery(
            _args=CommonPaginationArgs(query=query, first=first, offset=offset),
            stat=JobStatQuery(
                icpper_count=len(query.distinct('user_id')), job_count=query.count(),
                size=any_to_decimal(query.sum('size')), incomes=query.group_incomes(token_chain_id=token_chain_id))
        )

    def resolve_token_mint_records(self, info, first, offset, status=None, chain_id=None, token_contract_address=None):
        dao = getattr(self, 'query')
        return TokenMintRecordsQuery().get_query(info, dao, first, offset, status, chain_id, token_contract_address)

    def resolve_token_mint_split_info(self, info, start_cycle_id, end_cycle_id):
        dao = getattr(self, 'query')
        return TokenMintSplitInfoQuery().get_query(info, dao, start_cycle_id, end_cycle_id)


class DAOs(BaseObjectType):
    dao = List(DAOItem)
    stat = Field(DAOsStat)
    total = Int()

    def resolve_dao(self, info):
        return [DAOItem(datum=item['datum'], stat=item['stat']) for item in self._args.get('query')]


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
        # NOTE: ??????????????????????????????????????????????????????????????????????????? dao
        # if not current_user or current_user.status == UserStatus.NORMAL.value:
        #     raise PermissionError(COMMON_NOT_PERMISSION_ERROR)
        if not current_user:
            raise PermissionError(COMMON_NOT_PERMISSION_ERROR)

        # TODO: mock test data
        if os.environ.get('IS_UNITEST') != 'yes':
            check_user_access_token(current_user, ICPDAO_GITHUB_APP_CLIENT_ID, ICPDAO_GITHUB_APP_CLIENT_SECRET)
            github_org_id, is_icp_app_installed, is_github_org_owner = get_github_owner_app_info(current_user, kwargs['name'])

            if not is_icp_app_installed or not is_github_org_owner:
                raise ValueError(COMMON_NOT_PERMISSION_ERROR)
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
        token_chain_id = String()
        token_address = String()
        token_name = String()
        token_symbol = String()

    dao = Field(DAOSchema)

    @staticmethod
    def mutate(root, info, id, **kwargs):
        current_user = get_current_user_by_graphql(info)
        dao = DAOModel.objects(id=id).first()
        check_is_dao_owner(current_user, dao=dao)
        base_info = {}
        token_info = {}
        for field, value in kwargs.items():
            if field in ['desc', 'logo']:
                base_info[field] = value
            if field in ['token_chain_id', 'token_address', 'token_name', 'token_symbol']:
                token_info[field] = value
        if base_info:
            for field, value in base_info.items():
                setattr(dao, field, value)
            dao.update_at = int(time.time())
            dao.save()
        if token_info:
            dt = DAOToken.objects(
                dao_id=str(dao.id),
                token_chain_id=token_info['token_chain_id']
            ).first()
            if dt:
                dt.token_address = token_info['token_address']
                dt.token_name = token_info['token_name']
                dt.token_symbol = token_info['token_symbol']
                dt.update_at = int(time.time())
                dt.save()
            else:
                DAOToken(
                    dao_id=str(dao.id),
                    token_chain_id=token_info['token_chain_id'],
                    token_address=token_info['token_address'],
                    token_name=token_info['token_name'],
                    token_symbol=token_info['token_symbol']
                ).save()
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
            raise PermissionError(COMMON_NOT_AUTH_ERROR)

        if os.environ.get('IS_UNITEST') == 'yes':
            self.github_app_name = "icpdao-test"
            self.github_org_id = 0
            self.is_exists = True
            self.is_github_org_owner = True
            self.is_icp_app_installed = True
            return self

        check_user_access_token(current_user, ICPDAO_GITHUB_APP_CLIENT_ID, ICPDAO_GITHUB_APP_CLIENT_SECRET)

        self.github_app_name = ICPDAO_GITHUB_APP_NAME

        ugt = UserGithubToken.objects(github_user_id=current_user.github_user_id).first()

        github_org_id, is_icp_app_installed, is_github_org_owner = get_github_owner_app_info(current_user, name)

        dao = DAOModel.objects(name=name).first()
        self.is_exists = not not dao

        self.github_org_id = github_org_id
        self.is_icp_app_installed = is_icp_app_installed
        self.is_github_org_owner = is_github_org_owner

        return self


class UpdateDaoLastCycleStep(Mutation):
    class Arguments:
        dao_id = String(required=True)
        next_step = UpdateDaoLastCycleStepEnum()

    dao = Field(DAO)

    def mutate(self, info, dao_id, next_step):
        dao = DAOModel.objects(id=dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        # not owner
        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)
        current_at = int(time.time())

        last_cycle = Cycle.objects(dao_id=str(dao.id), vote_end_at__gt=current_at).order_by("begin_at").first()

        if not last_cycle:
            raise ValueError(COMMON_PARAMS_INVALID)

        if next_step == UpdateDaoLastCycleStepEnum.PAIR:
            if not (last_cycle.begin_at < current_at and last_cycle.end_at > current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            job_count = Job.objects.filter(cycle_id=str(last_cycle.id), status__nin=[JobStatusEnum.AWAITING_MERGER.value]).count()
            if job_count == 0:
                raise ValueError(COMMON_PARAMS_INVALID)
            last_cycle.end_at = current_at
            last_cycle.pair_begin_at = current_at

        if next_step == UpdateDaoLastCycleStepEnum.VOTE:
            if not (last_cycle.begin_at < current_at and last_cycle.end_at < current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            if not (last_cycle.pair_begin_at < current_at and last_cycle.pair_end_at > current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            task = CycleVotePairTask.objects(dao_id=dao_id, cycle_id=str(last_cycle.id)).order_by('-id').first()
            if not task or task.status != CycleVotePairTaskStatus.SUCCESS.value:
                raise ValueError(COMMON_PARAMS_INVALID)
            last_cycle.pair_end_at = current_at
            last_cycle.vote_begin_at = current_at

        if next_step == UpdateDaoLastCycleStepEnum.VOTE_END:
            if not (last_cycle.begin_at < current_at and last_cycle.end_at < current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            if not (last_cycle.pair_begin_at < current_at and last_cycle.pair_end_at < current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            if not (last_cycle.vote_begin_at < current_at and last_cycle.vote_end_at > current_at):
                raise ValueError(COMMON_PARAMS_INVALID)
            last_cycle.vote_end_at = current_at

        last_cycle.save()

        result_dao = DAO().get_query(info, dao_id)
        return UpdateDaoLastCycleStep(dao=result_dao)
