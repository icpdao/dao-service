from graphene import ObjectType, Field, List, Int, Decimal, Boolean
from mongoengine import Q

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat, CycleVote, CycleVoteType
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.common.models.icpdao.user import User
from app.common.schema.icpdao import CycleSchema, CycleIcpperStatSchema, UserSchema, JobSchema, CycleVoteSchema
from app.common.utils.route_helper import get_custom_attr_by_graphql, set_custom_attr_by_graphql, get_current_user, \
    get_current_user_by_graphql
from app.routes.data_loaders import UserLoader, JobLoader
from app.routes.schema import CycleIcpperStatSortedTypeEnum, CycleIcpperStatSortedEnum, JobsQuerySortedEnum, \
    JobsQuerySortedTypeEnum, JobsQueryPairTypeEnum


class IcpperStatQuery(ObjectType):
    datum = Field(CycleIcpperStatSchema)
    last_ei = Decimal()
    icpper = Field(lambda: UserSchema)

    def resolve_last_ei(self, info):
        dao_id = self.datum.dao_id
        user_id = self.datum.user_id
        create_at = self.datum.create_at
        last_item = CycleIcpperStat.objects(dao_id=dao_id, user_id=user_id, create_at__lt=create_at).order_by('-create_at').first()
        if last_item:
            return last_item.ei
        return None

    def resolve_icpper(self, info):
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        return user_loader.load(self.datum.user_id)


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

        return [IcpperStatQuery(datum=item) for item in query.limit(self.first).skip(self.offset)]


class JobQuery(ObjectType):
    datum = Field(JobSchema)
    user = Field(lambda: UserSchema)

    def resolve_user(self, info):
        user_loader = get_custom_attr_by_graphql(info, 'user_loader')
        return user_loader.load(self.datum.user_id)


class JobsQuery(ObjectType):
    nodes = List(JobQuery)
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
    def pair_type(self):
        return getattr(self, '_pair_type')

    @pair_type.setter
    def pair_type(self, pair_type):
        setattr(self, '_pair_type', pair_type)

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

    def _base_queryset(self):
        query = Job.objects.filter(cycle_id=self.cycle_id, status__nin=[JobStatusEnum.AWAITING_MERGER.value])

        if self.pair_type is not None:
            query = query.filter(pair_type=self.pair_type)

        if self.sorted is not None:
            sort_string = JobsQuerySortedEnum.get(self.sorted).name
            if self.sorted_type == JobsQuerySortedTypeEnum.desc:
                sort_string = '-{}'.format(sort_string)
            query = query.order_by(sort_string)
        return query

    def resolve_total(self, info):
        query = self._base_queryset()
        return query.count()

    def resolve_nodes(self, info):
        query = self._base_queryset()
        set_custom_attr_by_graphql(info, 'user_loader', UserLoader())

        return [JobQuery(datum=item) for item in query.limit(self.first).skip(self.offset)]


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


class CycleVotesQuery(ObjectType):
    nodes = List(CycleVoteQuery)
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

    def _base_queryset(self, info):
        query = CycleVote.objects.filter(cycle_id=self.cycle_id)
        if self.is_myself:
            current_user = get_current_user_by_graphql(info)
            query = query.filter(Q(voter_id=str(current_user.id)) | Q(vote_type=CycleVoteType.ALL.value))
        if self.is_public is not None:
            if self.is_public:
                query = query.filter(Q(is_result_public=self.is_public) | Q(vote_type=CycleVoteType.ALL.value))
            else:
                query = query.filter(is_result_public=self.is_public, vote_type=CycleVoteType.PAIR.value)
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

        return query.limit(self.first).skip(self.offset).count()


class CycleQuery(ObjectType):
    datum = Field(CycleSchema)
    icpper_stats = Field(
        IcpperStatsQuery,
        sorted=CycleIcpperStatSortedEnum(),
        sorted_type=CycleIcpperStatSortedTypeEnum(default_value=0),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )
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
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )

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

    def resolve_icpper_stats(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        _sorted = kwargs.get('sorted', None)
        sorted_type = kwargs.get('sorted_type', None)
        return IcpperStatsQuery(cycle_id=self.cycle_id, first=first, offset=offset, sorted=_sorted, sorted_type=sorted_type)

    def resolve_jobs(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        _sorted = kwargs.get('sorted', None)
        sorted_type = kwargs.get('sorted_type', None)
        pair_type = kwargs.get('pair_type', None)
        return JobsQuery(cycle_id=self.cycle_id, first=first, offset=offset, sorted=_sorted, sorted_type=sorted_type, pair_type=pair_type)

    def resolve_votes(self, info, **kwargs):
        first = kwargs.get('first')
        offset = kwargs.get('offset')
        is_public = kwargs.get('is_public', None)
        is_myself = kwargs.get('is_myself', None)
        return CycleVotesQuery(cycle_id=self.cycle_id, first=first, offset=offset, is_public=is_public, is_myself=is_myself)


class CyclesQuery(ObjectType):
    nodes = List(CycleQuery)

    @property
    def dao_id(self):
        return getattr(self, '_dao_id')

    @dao_id.setter
    def dao_id(self, dao_id):
        setattr(self, '_dao_id', dao_id)

    def resolve_nodes(self, info):
        cycle_list = Cycle.objects(dao_id=self.dao_id).order_by('-begin_at')
        return [CycleQuery(datum=i, cycle_id=str(i.id)) for i in cycle_list]