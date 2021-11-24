import decimal
import os
import time
from functools import reduce
from collections import defaultdict
from graphene import ObjectType, Field, List, Int, Decimal, Boolean, Mutation, String, Float
from mongoengine import Q

import settings
from app.common.models.extension.decimal128_field import any_to_decimal
from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat, CycleVote, CycleVoteType, CycleVotePairTask, \
    CycleVotePairTaskStatus, CycleVoteResultStatTask, CycleVoteResultStatTaskStatus, CycleVoteResultPublishTask, \
    CycleVoteResultPublishTaskStatus, CycleVoteConfirm, CycleVoteConfirmStatus
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum
from app.common.models.icpdao.user import User
from app.common.schema import BaseObjectType, BaseObjectArgs
from app.common.schema.icpdao import CycleSchema, CycleIcpperStatSchema, UserSchema, JobSchema, CycleVoteSchema
from app.common.schema.incomes import TokenIncomeSchema
from app.common.utils.access import check_is_dao_owner
from app.common.utils.errors import CYCLE_VOTE_CONFIRM_INVALID_ERROR, CYCLE_VOTE_NOT_FOUND_ERROR, COMMON_NOT_AUTH_ERROR, \
    CYCLE_ICPPER_STAT_NOT_FOUND_ERROR, CYCLE_TOKEN_RELEASED_CHECK_ERROR, CYCLE_NOT_FOUND_ERROR, \
    COMMON_NOT_FOUND_DAO_ERROR, COMMON_NOT_PERMISSION_ERROR, CYCLE_PAIR_TIME_ERROR, CYCLE_VOTE_RESULT_STAT_TIME_ERROR, \
    CYCLE_VOTE_RESULT_PUBLISH_TIME_ERROR, CYCLE_VOTE_RESULT_PUBLISH_INVALID_ERROR, COMMON_PARAMS_INVALID
from app.common.utils.route_helper import get_custom_attr_by_graphql, set_custom_attr_by_graphql, \
    get_current_user_by_graphql
from app.controllers.pair import run_pair_task
from app.controllers.vote_result_publish import run_vote_result_publish_task
from app.controllers.vote_result_stat import run_vote_result_stat_task
from app.routes.data_loaders import UserLoader, JobLoader, CycleLoader
from app.routes.schema import CycleIcpperStatSortedTypeEnum, CycleIcpperStatSortedEnum, JobsQuerySortedEnum, \
    JobsQuerySortedTypeEnum, JobsQueryPairTypeEnum, CycleVotePairTaskStatusEnum, \
    CreateCycleVotePairTaskByOwnerStatusEnum, CycleFilterEnum, CreateCycleVoteResultStatTaskByOwnerStatusEnum, \
    CycleVoteResultStatTaskStatusEnum, CycleVoteResultTypeAllResultTypeEnum, \
    CreateCycleVoteResultPublishTaskByOwnerStatusEnum, CycleVoteResultPublishTaskStatusEnum, CommonPaginationArgs, \
    CycleVoteFilterEnum, UpdateDaoLastCycleStepEnum, CycleStepEnum


class IcpperStatQuery(ObjectType):
    datum = Field(CycleIcpperStatSchema)
    last_ei = Decimal()
    icpper = Field(lambda: UserSchema)
    cycle = Field(lambda: CycleSchema)
    be_reviewer_has_warning_users = List(lambda: UserSchema)

    def resolve_last_ei(self, info):
        if self.datum.last_id:
            last_item = CycleIcpperStat.objects(id=self.datum.last_id).first()
            return last_item.ei
        return None

    def resolve_icpper(self, info):
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        return user_loader.load(self.datum.user_id)

    def resolve_cycle(self, info):
        cycle_loader = get_custom_attr_by_graphql(info, 'cycle_loader')
        return cycle_loader.load(self.datum.cycle_id)

    def resolve_be_reviewer_has_warning_users(self, info):
        if self.datum.be_reviewer_has_warning_user_ids:
            user_loader = get_custom_attr_by_graphql(info, 'user_loader')
            return user_loader.load_many(self.datum.be_reviewer_has_warning_user_ids)
        return []


class IcpperStatsQuery(ObjectType):
    nodes = List(IcpperStatQuery)
    total = Int()

    @property
    def cycle_id(self):
        return getattr(self, '_cycle_id')

    @cycle_id.setter
    def cycle_id(self, cycle_id):
        setattr(self, '_cycle_id', cycle_id)

    @property
    def sorted(self):
        return getattr(self, '_sorted')

    @sorted.setter
    def sorted(self, _sorted):
        setattr(self, '_sorted', _sorted)

    @property
    def sorted_type(self):
        return getattr(self, '_sorted_type')

    @sorted_type.setter
    def sorted_type(self, sorted_type):
        setattr(self, '_sorted_type', sorted_type)

    @property
    def first(self):
        return getattr(self, '_first')

    @first.setter
    def first(self, first):
        setattr(self, '_first', first)

    @property
    def offset(self):
        return getattr(self, '_offset')

    @offset.setter
    def offset(self, offset):
        setattr(self, '_offset', offset)

    def resolve_total(self, info):
        return CycleIcpperStat.objects(cycle_id=self.cycle_id).count()

    def resolve_nodes(self, info):
        query = CycleIcpperStat.objects(cycle_id=self.cycle_id)
        if self.sorted is not None:
            sort_string = CycleIcpperStatSortedEnum.get(self.sorted).name
            if sort_string == 'jobCount':
                sort_string = 'job_count'
            if self.sorted_type == CycleIcpperStatSortedTypeEnum.desc:
                sort_string = '-{}'.format(sort_string)
            query = query.order_by(sort_string)

        cycle = Cycle.objects(id=self.cycle_id).first()
        dao_owner_id = DAO.objects(id=cycle.dao_id).first().owner_id

        set_custom_attr_by_graphql(info, 'dao_owner_id', dao_owner_id)
        set_custom_attr_by_graphql(info, 'user_loader', UserLoader())
        set_custom_attr_by_graphql(info, 'cycle_loader', CycleLoader())

        return [IcpperStatQuery(datum=item) for item in query.limit(self.first).skip(self.offset)]


class JobQuery(ObjectType):
    datum = Field(JobSchema)
    user = Field(lambda: UserSchema)

    def resolve_user(self, info):
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        return user_loader.load(self.datum.user_id)


class JobStatQuery(ObjectType):
    icpper_count = Int()
    job_count = Int()
    size = Decimal()
    incomes = List(TokenIncomeSchema)


class JobsQuery(BaseObjectType):
    nodes = List(JobQuery)
    stat = Field(JobStatQuery, token_chain_id=String(default_value=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID))
    total = Int()

    def resolve_total(self, info):
        query = self._args.get('query')
        return query.count()

    def resolve_nodes(self, info):
        query = self._args.get('query')
        set_custom_attr_by_graphql(info, 'user_loader', UserLoader())
        return [JobQuery(datum=item) for item in query.limit(self._args.get('first')).skip(self._args.get('offset'))]

    def resolve_stat(self, info, token_chain_id):
        query = self._args.get('query')
        return JobStatQuery(
            icpper_count=len(query.distinct('user_id')), job_count=query.count(),
            size=any_to_decimal(query.sum('size')), incomes=query.group_incomes(token_chain_id=token_chain_id))


class UserIcpperStatsQuery(ObjectType):
    nodes = List(IcpperStatQuery)
    total = Int()

    @property
    def dao_name(self):
        return getattr(self, '_dao_name')

    @dao_name.setter
    def dao_name(self, dao_name):
        setattr(self, '_dao_name', dao_name)

    @property
    def user_name(self):
        return getattr(self, '_user_name')

    @user_name.setter
    def user_name(self, user_name):
        setattr(self, '_user_name', user_name)

    @property
    def first(self):
        return getattr(self, '_first')

    @first.setter
    def first(self, first):
        setattr(self, '_first', first)

    @property
    def offset(self):
        return getattr(self, '_offset')

    @offset.setter
    def offset(self, offset):
        setattr(self, '_offset', offset)

    def _get_info_from_db(self):
        _info = getattr(self, '_get_info_from_db_cache', None)
        if _info:
            return _info
        else:
            dao = DAO.objects(github_owner_name=self.dao_name).first()
            user = User.objects(github_login=self.user_name).first()
            un_show_cycle_list = Cycle.objects(dao_id=str(dao.id), vote_result_published_at__exists=False)
            un_showw_cycle_id_list = []
            for cycle in un_show_cycle_list:
                un_showw_cycle_id_list.append(str(cycle.id))
            _info = {
                "dao": dao,
                "user": user,
                "un_showw_cycle_id_list": un_showw_cycle_id_list
            }
            setattr(self, '_get_info_from_db_cache', _info)
            return _info

    def resolve_total(self, info):
        _db_info = self._get_info_from_db()
        return CycleIcpperStat.objects(
            dao_id=str(_db_info["dao"].id),
            user_id=str(_db_info["user"].id),
            cycle_id__nin=_db_info["un_showw_cycle_id_list"]
        ).count()

    def resolve_nodes(self, info):
        _db_info = self._get_info_from_db()
        dao = _db_info["dao"]
        user = _db_info["user"]
        un_showw_cycle_id_list = _db_info["un_showw_cycle_id_list"]
        query = CycleIcpperStat.objects(
            dao_id=str(dao.id),
            user_id=str(user.id),
            cycle_id__nin=un_showw_cycle_id_list
        ).order_by("-create_at")

        set_custom_attr_by_graphql(info, 'dao_owner_id', dao.owner_id)
        set_custom_attr_by_graphql(info, 'user_loader', UserLoader())
        set_custom_attr_by_graphql(info, 'cycle_loader', CycleLoader())

        return [IcpperStatQuery(datum=item) for item in query.limit(self.first).skip(self.offset)]


class JobItemQuery(ObjectType):
    datum = Field(lambda: JobSchema)
    user = Field(lambda: UserSchema)

    @property
    def job_id(self):
        return getattr(self, '_job_id')

    @job_id.setter
    def job_id(self, job_id):
        setattr(self, '_job_id', job_id)

    def resolve_datum(self, info):
        job_loader = get_custom_attr_by_graphql(info, 'job_loader')
        return job_loader.load(self.job_id)

    def resolve_user(self, info):
        job_loader = get_custom_attr_by_graphql(info, 'job_loader')
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        return job_loader.load(self.job_id).then(lambda item: user_loader.load(item.user_id))


class CycleVoteQuery(ObjectType):
    datum = Field(CycleVoteSchema)
    left_job = Field(JobItemQuery)
    right_job = Field(JobItemQuery)
    vote_job = Field(JobItemQuery)
    voter = Field(lambda: UserSchema)
    self_vote_result_type_all = Field(CycleVoteResultTypeAllResultTypeEnum)

    def resolve_left_job(self, info):
        return JobItemQuery(job_id=self.datum.left_job_id)

    def resolve_right_job(self, info):
        return JobItemQuery(job_id=self.datum.right_job_id)

    def resolve_vote_job(self, info):
        if CycleVoteSchema.have_view_vote_job_id_role(info, self.datum) and self.datum.vote_job_id:
            return JobItemQuery(job_id=self.datum.vote_job_id)
        return None

    def resolve_voter(self, info):
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        if CycleVoteSchema.have_view_voter_id_role(info, self.datum) and self.datum.voter_id:
            return user_loader.load(self.datum.voter_id)
        return None

    def resolve_self_vote_result_type_all(self, info):
        if self.datum.vote_type == CycleVoteType.PAIR.value:
            return None

        current_user = get_current_user_by_graphql(info)
        if not current_user:
            return None

        for result in self.datum.vote_result_type_all:
            if result.voter_id == str(current_user.id):
                return result.result
        return None


class CycleVotesQuery(ObjectType):
    nodes = List(CycleVoteQuery)
    confirm = Boolean()
    user_un_vote_total = Int()
    user_voted_total = Int()
    total = Int()

    @property
    def cycle_id(self):
        return getattr(self, '_cycle_id')

    @cycle_id.setter
    def cycle_id(self, cycle_id):
        setattr(self, '_cycle_id', cycle_id)

    @property
    def first(self):
        return getattr(self, '_first')

    @first.setter
    def first(self, first):
        setattr(self, '_first', first)

    @property
    def offset(self):
        return getattr(self, '_offset')

    @offset.setter
    def offset(self, offset):
        setattr(self, '_offset', offset)

    @property
    def is_public(self):
        return getattr(self, '_is_public')

    @is_public.setter
    def is_public(self, is_public):
        setattr(self, '_is_public', is_public)

    @property
    def is_myself(self):
        return getattr(self, '_is_myself')

    @is_myself.setter
    def is_myself(self, is_myself):
        setattr(self, '_is_myself', is_myself)

    @property
    def is_repeat(self):
        return getattr(self, '_is_repeat')

    @is_repeat.setter
    def is_repeat(self, is_repeat):
        setattr(self, '_is_repeat', is_repeat)

    @property
    def filter(self):
        return getattr(self, '_filter')

    @filter.setter
    def filter(self, filter):
        setattr(self, '_filter', filter)

    def _base_queryset(self, info):
        query = CycleVote.objects.filter(cycle_id=self.cycle_id)
        current_user = get_current_user_by_graphql(info)
        if self.is_myself:
            query = query.filter(Q(voter_id=str(current_user.id)) | Q(vote_type=CycleVoteType.ALL.value))
        if self.is_public is not None:
            if self.is_public:
                query = query.filter(Q(is_result_public=self.is_public) | Q(vote_type=CycleVoteType.ALL.value))
            else:
                query = query.filter(is_result_public=self.is_public, vote_type=CycleVoteType.PAIR.value)
        if self.is_repeat:
            query = query.filter(is_repeat=True)
        # NOTICE: filter all type belongs current_user.id
        if self.filter == CycleVoteFilterEnum.un_vote:
            query = query.filter(
                Q(voter_id=str(current_user.id), vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=False) |
                Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id__ne=str(current_user.id))
            )
        if self.filter == CycleVoteFilterEnum.voted:
            query = query.filter(
                Q(voter_id=str(current_user.id), vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=True) |
                Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id=str(current_user.id))
            )
        query = query.order_by('-vote_type', '_id')
        return query

    def resolve_nodes(self, info):
        query = self._base_queryset(info)

        cycle = Cycle.objects(id=self.cycle_id).first()
        dao_owner_id = DAO.objects(id=cycle.dao_id).first().owner_id
        set_custom_attr_by_graphql(info, 'dao_owner_id', dao_owner_id)

        set_custom_attr_by_graphql(info, 'user_loader', UserLoader())
        set_custom_attr_by_graphql(info, 'job_loader', JobLoader())

        return [CycleVoteQuery(datum=item) for item in query.limit(self.first).skip(self.offset)]

    def resolve_total(self, info):
        query = self._base_queryset(info)
        return query.count()

    def resolve_user_un_vote_total(self, info):
        current_user = get_current_user_by_graphql(info)
        return CycleVote.objects(
            Q(cycle_id=self.cycle_id) &
            (
                Q(voter_id=str(current_user.id), vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=False) |
                Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id__ne=str(current_user.id))
            )
        ).count()

    def resolve_user_voted_total(self, info):
        current_user = get_current_user_by_graphql(info)
        return CycleVote.objects(
            Q(cycle_id=self.cycle_id) &
            (
                Q(voter_id=str(current_user.id), vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=True) |
                Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id=str(current_user.id))
            )
        ).count()

    def resolve_confirm(self, info):
        cycle = Cycle.objects(id=self.cycle_id).first()
        if self.is_myself:
            current_user = get_current_user_by_graphql(info)
            assert current_user, CYCLE_VOTE_CONFIRM_INVALID_ERROR
            cvc = CycleVoteConfirm.objects(
                dao_id=cycle.dao_id, cycle_id=self.cycle_id, voter_id=str(current_user.id)).first()
            assert cvc, CYCLE_VOTE_NOT_FOUND_ERROR
            return cvc.status == CycleVoteConfirmStatus.CONFIRM.value
        all_status = set(CycleVoteConfirm.objects(dao_id=cycle.dao_id, cycle_id=self.cycle_id).distinct('status'))
        return len(all_status) == 1 and all_status == {CycleVoteConfirmStatus.CONFIRM.value}


class CycleStatQuery(ObjectType):
    icpper_count = Int()
    job_count = Int()
    size = Decimal()
    incomes = Field(List(TokenIncomeSchema), token_chain_id=String(default_value=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID))

    @property
    def cycle_id(self):
        return getattr(self, '_cycle_id')

    @cycle_id.setter
    def cycle_id(self, cycle_id):
        setattr(self, '_cycle_id', cycle_id)

    def _get_icpper_stats(self, info):
        cache = getattr(self, '_get_icpper_stats_cache', None)
        if cache is None:
            cache = [item for item in CycleIcpperStat.objects(cycle_id=self.cycle_id)]
            setattr(self, '_get_icpper_stats_cache', cache)
        return cache

    def resolve_icpper_count(self, info):
        icpper_stat_list = self._get_icpper_stats(info)
        return len(icpper_stat_list)

    def resolve_job_count(self, info):
        count = 0
        icpper_stat_list = self._get_icpper_stats(info)
        for item in icpper_stat_list:
            count += item.job_count
        return count

    def resolve_size(self, info):
        size = decimal.Decimal('0')
        icpper_stat_list = self._get_icpper_stats(info)
        for item in icpper_stat_list:
            size += item.size
        return size

    def resolve_incomes(self, info, token_chain_id):
        return CycleIcpperStat.objects(cycle_id=self.cycle_id).group_incomes(token_chain_id=token_chain_id)


class CycleVotePairTaskQuery(ObjectType):
    status = Field(CycleVotePairTaskStatusEnum)


class CycleVoteResultStatTaskQuery(ObjectType):
    status = Field(CycleVoteResultStatTaskStatusEnum)


class CycleVoteResultPublishTaskQuery(ObjectType):
    status = Field(CycleVoteResultPublishTaskStatusEnum)


class CycleStepQuery(ObjectType):
    status = Field(CycleStepEnum)


class CycleQuery(ObjectType):
    datum = Field(CycleSchema)
    stat = Field(CycleStatQuery)
    icpper_stats = Field(
        IcpperStatsQuery,
        sorted=CycleIcpperStatSortedEnum(),
        sorted_type=CycleIcpperStatSortedTypeEnum(default_value=0),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )
    icpper_stat = Field(IcpperStatQuery)
    jobs = Field(
        JobsQuery,
        pair_type=JobsQueryPairTypeEnum(),
        sorted=JobsQuerySortedEnum(),
        sorted_type=JobsQuerySortedTypeEnum(default_value=0),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )
    votes = Field(
        CycleVotesQuery,
        is_public=Boolean(),
        is_myself=Boolean(),
        is_repeat=Boolean(),
        filter=CycleVoteFilterEnum(default_value=0),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )
    pair_task = Field(CycleVotePairTaskQuery)
    vote_result_stat_task = Field(CycleVoteResultStatTaskQuery)
    vote_result_publish_task = Field(CycleVoteResultPublishTaskQuery)
    step = Field(CycleStepQuery)

    @property
    def cycle_id(self):
        return getattr(self, '_cycle_id')

    @cycle_id.setter
    def cycle_id(self, cycle_id):
        setattr(self, '_cycle_id', cycle_id)

    def resolve_datum(self, info):
        if not self.datum:
            return Cycle.objects(id=self.cycle_id).first()
        return self.datum

    def resolve_stat(self, info):
        return CycleStatQuery(cycle_id=self.cycle_id)

    def resolve_icpper_stats(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        _sorted = kwargs.get('sorted', None)
        sorted_type = kwargs.get('sorted_type', None)
        return IcpperStatsQuery(cycle_id=self.cycle_id, first=first, offset=offset, sorted=_sorted, sorted_type=sorted_type)

    def resolve_icpper_stat(self, info):
        current_user = get_current_user_by_graphql(info)
        assert current_user, COMMON_NOT_AUTH_ERROR
        record = CycleIcpperStat.objects(cycle_id=self.cycle_id, user_id=str(current_user.id)).first()
        assert record, CYCLE_ICPPER_STAT_NOT_FOUND_ERROR
        return IcpperStatQuery(datum=record)

    @staticmethod
    def _jobs_base_queryset(cycle_id, sorted, sorted_type, pair_type):
        query = Job.objects.filter(cycle_id=cycle_id, status__nin=[JobStatusEnum.AWAITING_MERGER.value])

        if pair_type is not None:
            query = query.filter(pair_type=pair_type)

        if sorted is not None:
            sort_string = JobsQuerySortedEnum.get(sorted).value
            if sorted_type == JobsQuerySortedTypeEnum.desc:
                sort_string = '-{}'.format(sort_string)
            query = query.order_by(sort_string)
        return query

    def resolve_jobs(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        _sorted = kwargs.get('sorted', JobsQuerySortedEnum.updateAt)
        sorted_type = kwargs.get('sorted_type', JobsQuerySortedTypeEnum.desc)
        pair_type = kwargs.get('pair_type', None)

        query = self._jobs_base_queryset(cycle_id=self.cycle_id, sorted=_sorted, sorted_type=sorted_type, pair_type=pair_type)
        return JobsQuery(_args=CommonPaginationArgs(query=query, first=first, offset=offset))

    def resolve_votes(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        is_public = kwargs.get('is_public', None)
        is_myself = kwargs.get('is_myself', None)
        is_repeat = kwargs.get('is_repeat', None)
        _filter = kwargs.get('filter')
        return CycleVotesQuery(
            cycle_id=self.cycle_id, first=first, offset=offset,
            is_public=is_public, is_myself=is_myself, is_repeat=is_repeat, filter=_filter)

    def resolve_pair_task(self, info):
        cycle = Cycle.objects(id=self.cycle_id).first()
        dao_id = cycle.dao_id
        task = CycleVotePairTask.objects(dao_id=dao_id, cycle_id=str(cycle.id)).order_by('-id').first()
        if not task:
            return None
        return CycleVotePairTaskQuery(status=task.status)

    def resolve_vote_result_stat_task(self, info):
        cycle = Cycle.objects(id=self.cycle_id).first()
        dao_id = cycle.dao_id
        task = CycleVoteResultStatTask.objects(dao_id=dao_id, cycle_id=str(cycle.id)).order_by('-id').first()
        if not task:
            return None
        return CycleVoteResultStatTaskQuery(status=task.status)

    def resolve_vote_result_publish_task(self, info):
        cycle = Cycle.objects(id=self.cycle_id).first()
        dao_id = cycle.dao_id
        task = CycleVoteResultPublishTask.objects(dao_id=dao_id, cycle_id=str(cycle.id)).order_by('-id').first()
        if not task:
            return None
        return CycleVoteResultPublishTaskQuery(status=task.status)

    def resolve_step(self, info):
        cycle = Cycle.objects(id=self.cycle_id).first()
        current_at = int(time.time())
        if cycle.begin_at < current_at and cycle.end_at > current_at:
            return CycleStepQuery(status=CycleStepEnum.JOB)
        if cycle.pair_begin_at <= current_at and cycle.pair_end_at > current_at:
            return CycleStepQuery(status=CycleStepEnum.PAIR)
        if cycle.vote_begin_at <= current_at and cycle.vote_end_at > current_at:
            return CycleStepQuery(status=CycleStepEnum.VOTE)
        if cycle.vote_end_at <= current_at:
            return CycleStepQuery(status=CycleStepEnum.VOTE_END)


class CyclesQuery(BaseObjectType):
    nodes = List(CycleQuery)

    def resolve_nodes(self, info):
        query = Q(dao_id=self._args.dao_id)
        now_time = int(time.time())

        if self._args.get('filter'):
            filter_query_list = []
            for item in self._args.get('filter'):
                if item == CycleFilterEnum.processing:
                    filter_query_list.append(Q(
                        begin_at__lte=now_time,
                        end_at__gt=now_time
                    ))
                if item == CycleFilterEnum.pairing:
                    filter_query_list.append(Q(
                        pair_begin_at__lte=now_time,
                        pair_end_at__gt=now_time
                    ))
                if item == CycleFilterEnum.voting:
                    filter_query_list.append(Q(
                        vote_begin_at__lte=now_time,
                        vote_end_at__gt=now_time,
                        paired_at__gt=0
                    ))
                if item == CycleFilterEnum.un_vote_end:
                    filter_query_list.append(Q(
                        vote_end_at__gt=now_time
                    ))
            filter_query = reduce(lambda x, y: x | y, filter_query_list)
            query = query & filter_query

        cycle_list = Cycle.objects(query).order_by('-begin_at')
        return [CycleQuery(datum=i, cycle_id=str(i.id)) for i in cycle_list]


class CycleByTokenUnreleasedQuery(BaseObjectType):
    nodes = List(CycleQuery)

    def resolve_nodes(self, info):
        last_timestamp = int(self._args.get('last_timestamp'))
        dao_id = self._args.get('dao_id')
        token_chain_id = self._args.get('token_chain_id')
        token_address = self._args.get('token_address')
        last_token_mint = TokenMintRecord.objects(
            dao_id=dao_id,
            chain_id=token_chain_id,
            token_contract_address=token_address,
            status__in=[
                MintRecordStatusEnum.INIT.value, MintRecordStatusEnum.PENDING.value, MintRecordStatusEnum.SUCCESS.value]
        ).order_by('-end_timestamp').first()
        if last_token_mint:
            last_cycle = Cycle.objects(id=last_token_mint.end_cycle_id).first()
            assert last_cycle, COMMON_PARAMS_INVALID
            assert last_timestamp == last_cycle.end_at
            # last_timestamp = last_timestamp if last_timestamp > last_cycle.end_at else last_cycle.end_at
        cycle_list = Cycle.objects(dao_id=dao_id, end_at__gt=last_timestamp, vote_result_published_at__exists=True).order_by('-begin_at')
        return [CycleQuery(datum=i, cycle_id=str(i.id)) for i in cycle_list]


class VotingCycleQuery(BaseObjectType):
    datum = Field(CycleSchema)

    def get(self, info):
        current_user = get_current_user_by_graphql(info)
        assert current_user, 'NOT LOGIN'

        now_at = int(time.time())
        dao_id_list = Job.objects(user_id=str(current_user.id)).distinct('dao_id')
        self.datum = Cycle.objects(
            vote_begin_at__lte=now_at,
            vote_end_at__gt=now_at,
            dao_id__in=dao_id_list
        ).order_by("vote_end_at").first()
        return self


class ChangeVoteResultPublic(Mutation):
    class Arguments:
        id = String(required=True)
        public = Boolean(required=True)

    ok = Boolean()

    def mutate(self, info, id, public):
        cv = CycleVote.objects(id=id).first()
        if cv.vote_type != CycleVoteType.PAIR.value:
            raise ValueError('NOT SUPPORT')

        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != cv.voter_id:
            raise ValueError(COMMON_NOT_AUTH_ERROR)

        cv.is_result_public = public
        cv.save()
        return ChangeVoteResultPublic(ok=True)


class CreateCycleVotePairTaskByOwner(Mutation):
    class Arguments:
        cycle_id = String(required=True)

    status = CreateCycleVoteResultStatTaskByOwnerStatusEnum()

    def mutate(self, info, cycle_id):
        cycle = Cycle.objects(id=cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        dao = DAO.objects(id=cycle.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        # not owner
        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)

        # time range
        if cycle.pair_begin_at >= time.time() or cycle.pair_end_at <= time.time():
            raise ValueError(CYCLE_PAIR_TIME_ERROR)

        old_task = CycleVotePairTask.objects(cycle_id=str(cycle.id)).order_by('-id').first()
        # have old task sttatus is init pairing
        if old_task and old_task.status in [CycleVotePairTaskStatus.INIT.value, CycleVotePairTaskStatus.PAIRING.value]:
            return CreateCycleVotePairTaskByOwner(status=old_task.status)

        task = CycleVotePairTask(
            dao_id=cycle.dao_id,
            cycle_id=str(cycle.id)
        ).save()

        # TODO PAIR
        if os.environ.get('IS_UNITEST') != 'yes':
            background_tasks = info.context['background']
            background_tasks.add_task(run_pair_task, str(task.id))
        return CreateCycleVotePairTaskByOwner(status=task.status)


class CreateCycleVoteResultStatTaskByOwner(Mutation):
    class Arguments:
        cycle_id = String(required=True)

    status = CreateCycleVoteResultStatTaskByOwnerStatusEnum()

    def mutate(self, info, cycle_id):
        cycle = Cycle.objects(id=cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        dao = DAO.objects(id=cycle.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        # not owner
        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)

        # time range
        if cycle.vote_end_at >= time.time():
            raise ValueError(CYCLE_VOTE_RESULT_STAT_TIME_ERROR)

        old_task = CycleVoteResultStatTask.objects(cycle_id=str(cycle.id)).order_by('-id').first()
        # have old task sttatus is init stating
        if old_task and old_task.status in [CycleVoteResultStatTaskStatus.INIT.value, CycleVoteResultStatTaskStatus.STATING.value]:
            return CreateCycleVoteResultStatTaskByOwner(status=old_task.status)

        task = CycleVoteResultStatTask(
            dao_id=cycle.dao_id,
            cycle_id=str(cycle.id)
        ).save()

        # TODO 优化 task 运行方式
        if os.environ.get('IS_UNITEST') != 'yes':
            background_tasks = info.context['background']
            background_tasks.add_task(run_vote_result_stat_task, str(task.id))
        return CreateCycleVoteResultStatTaskByOwner(status=task.status)


class CreateCycleVoteResultPublishTaskByOwner(Mutation):
    class Arguments:
        cycle_id = String(required=True)

    status = CreateCycleVoteResultPublishTaskByOwnerStatusEnum()

    def mutate(self, info, cycle_id):
        cycle = Cycle.objects(id=cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        dao = DAO.objects(id=cycle.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        # not owner
        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)

        # time range
        if cycle.vote_end_at >= time.time():
            raise ValueError(CYCLE_VOTE_RESULT_PUBLISH_TIME_ERROR)
        if not cycle.vote_result_stat_at:
            raise ValueError(CYCLE_VOTE_RESULT_PUBLISH_INVALID_ERROR)

        old_task = CycleVoteResultPublishTask.objects(cycle_id=str(cycle.id)).order_by('-id').first()
        # have old task sttatus is init running
        if old_task and old_task.status in [CycleVoteResultPublishTaskStatus.INIT.value, CycleVoteResultPublishTaskStatus.RUNNING.value]:
            return CreateCycleVoteResultPublishTaskByOwner(status=old_task.status)

        task = CycleVoteResultPublishTask(
            dao_id=cycle.dao_id,
            cycle_id=str(cycle.id)
        ).save()

        # TODO 优化 task 运行方式
        if os.environ.get('IS_UNITEST') != 'yes':
            background_tasks = info.context['background']
            background_tasks.add_task(run_vote_result_publish_task, str(task.id))
        return CreateCycleVoteResultPublishTaskByOwner(status=task.status)


class MarkCyclesTokenReleased(Mutation):
    class Arguments:
        dao_id = String(required=True)
        cycle_ids = List(String, required=True)
        unit_size_value = String(required=True)

    ok = Boolean()

    def mutate(self, info, dao_id, cycle_ids, unit_size_value):
        # DEPRECATION
        raise DeprecationWarning
