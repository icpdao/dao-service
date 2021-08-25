import decimal

from graphene import ObjectType, String, Field, Int

from app.common.models.icpdao.job import Job
from app.routes.config import UpdateDAOJobConfig, DAOJobConfig, DAOTokenConfig
from app.routes.cycles import CycleQuery, CreateCycleVotePairTaskByOwner, \
    ChangeVoteResultPublic, CreateCycleVoteResultStatTaskByOwner, CreateCycleVoteResultPublishTaskByOwner, \
    UserIcpperStatsQuery, CycleByTokenUnreleasedQuery, MarkCyclesTokenReleased, VotingCycleQuery
from app.routes.daos import DAOs, CreateDAO, DAO, UpdateDAOBaseInfo, DAOGithubAppStatus, DAOsStat, DAOItem, DAOStat, \
    get_query_dao_list
from app.routes.follow import UpdateDAOFollow
from app.routes.jobs import Jobs, CreateJob, UpdateJob, UpdateJobVoteTypeByOwner, UpdateIcpperStatOwnerEi, DeleteJob
from app.routes.mock import CreateMock
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum, JobSortedEnum, SortedTypeEnum, DAOJobConfigQueryArgs, CyclesTokenUnreleasedQueryArgs, \
    DAOQueryArgs
from app.routes.vote import UpdatePairVote, UpdateALLVote, UpdateVoteConfirm


class Query(ObjectType):
    daos = Field(
        DAOs,
        filter=DAOsFilterEnum(),
        sorted=DAOsSortedEnum(),
        sorted_type=DAOsSortedTypeEnum(),
        search=String(),
        first=Int(default_value=20),
        offset=Int(default_value=0),
        user_name=String()
    )

    dao = Field(
        DAO,
        id=String(),
        name=String()
    )

    dao_job_config = Field(
        DAOJobConfig,
        dao_id=String(required=True)
    )

    dao_token_config = Field(
        DAOTokenConfig,
        dao_id=String(required=True)
    )

    dao_github_app_status = Field(
        DAOGithubAppStatus,
        name=String(required=True)
    )

    cycle = Field(
        CycleQuery,
        id=String(required=True)
    )

    cycles_by_token_unreleased = Field(
        CycleByTokenUnreleasedQuery,
        last_timestamp=Int(required=True)
    )

    voting_cycle = Field(VotingCycleQuery)

    jobs = Field(
        Jobs,
        dao_name=String(),
        begin_time=Int(),
        end_time=Int(),
        sorted=JobSortedEnum(),
        sorted_type=SortedTypeEnum(),
        first=Int(default_value=20),
        offset=Int(default_value=0),
        user_name=String(),
    )

    icpper_stats = Field(
        UserIcpperStatsQuery,
        dao_name=String(),
        user_name=String(),
        first=Int(default_value=20),
        offset=Int(default_value=0)
    )

    @staticmethod
    def resolve_daos(root, info, **kwargs):
        query_dao_list, all_dao_ids = get_query_dao_list(info, **kwargs)
        icpper = Job.objects(dao_id__in=all_dao_ids).distinct('user_id')
        size = Job.objects(dao_id__in=all_dao_ids).sum('size')
        income = Job.objects(dao_id__in=all_dao_ids).sum('income')
        stat = DAOsStat(icpper=len(icpper), size=decimal.Decimal(size), income=decimal.Decimal(income))
        return DAOs(_args=DAOQueryArgs(query=query_dao_list), stat=stat, total=len(all_dao_ids))

    @staticmethod
    def resolve_jobs(root, info, **kwargs):
        return Jobs().get_query_job_list(info, **kwargs)

    @staticmethod
    def resolve_dao_job_config(root, info, dao_id):
        return DAOJobConfig(_args=DAOJobConfigQueryArgs(dao_id=dao_id))

    @staticmethod
    def resolve_dao_token_config(root, info, dao_id):
        return DAOTokenConfig(_args=DAOJobConfigQueryArgs(dao_id=dao_id))

    @staticmethod
    def resolve_dao(root, info, id=None, name=None):
        return DAO().get_query(info, id, name)

    @staticmethod
    def resolve_dao_github_app_status(root, info, name):
        return DAOGithubAppStatus().get(info, name)

    @staticmethod
    def resolve_voting_cycle(root, info):
        return VotingCycleQuery().get(info)

    @staticmethod
    def resolve_cycle(root, info, id):
        return CycleQuery(cycle_id=id)

    @staticmethod
    def resolve_cycles_by_token_unreleased(root, info, last_timestamp):
        return CycleByTokenUnreleasedQuery(
            _args=CyclesTokenUnreleasedQueryArgs(last_timestamp=last_timestamp)
        )

    @staticmethod
    def resolve_icpper_stats(root, info, **kwargs):
        return UserIcpperStatsQuery(**kwargs)


class Mutations(ObjectType):
    create_dao = CreateDAO.Field()
    update_dao_job_config = UpdateDAOJobConfig.Field()
    update_dao_follow = UpdateDAOFollow.Field()
    update_dao_base_info = UpdateDAOBaseInfo.Field()
    create_job = CreateJob.Field()
    update_job = UpdateJob.Field()
    delete_job = DeleteJob.Field()
    update_job_vote_type_by_owner = UpdateJobVoteTypeByOwner.Field()
    update_icpper_stat_owner_ei = UpdateIcpperStatOwnerEi.Field()
    update_pair_vote = UpdatePairVote.Field()
    update_all_vote = UpdateALLVote.Field()
    update_vote_confirm = UpdateVoteConfirm.Field()
    create_cycle_vote_pair_task_by_owner = CreateCycleVotePairTaskByOwner.Field()
    change_vote_result_public = ChangeVoteResultPublic.Field()
    create_mock = CreateMock.Field()
    createCycleVoteResultStatTaskByOwner = CreateCycleVoteResultStatTaskByOwner.Field()
    createCycleVoteResultPublishTaskByOwner = CreateCycleVoteResultPublishTaskByOwner.Field()
    mark_cycles_token_released = MarkCyclesTokenReleased.Field()
