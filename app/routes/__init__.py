from graphene import ObjectType, String, Field, Int

from app.common.models.icpdao.dao import DAOJobConfig as DAOJobConfigModel
from app.common.schema.icpdao import DAOJobConfigSchema
from app.common.utils.route_helper import get_current_user_by_graphql
from app.routes.config import UpdateDAOJobConfig
from app.routes.cycles import CycleQuery, PublishCycleVoteResultByOwner, CreateCycleVotePairTaskByOwner, \
    ChangeVoteResultPublic
from app.routes.daos import DAOs, CreateDAO, DAO, UpdateDAOBaseInfo, DAOGithubAppStatus
from app.routes.follow import UpdateDAOFollow
from app.routes.jobs import Jobs, CreateJob, UpdateJob, UpdateJobVoteTypeByOwner, UpdateIcpperStatOwnerEi
from app.routes.mock import CreateMock
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum, JobSortedEnum, SortedTypeEnum
from app.routes.vote import UpdatePairVote, UpdateALLVote


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
        id=String(),
        name=String()
    )

    dao_job_config = Field(
        DAOJobConfigSchema,
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

    @staticmethod
    def resolve_daos(root, info, **kwargs):
        return DAOs().get_query_dao_list(info, **kwargs)

    @staticmethod
    def resolve_jobs(root, info, **kwargs):
        return Jobs().get_query_job_list(info, **kwargs)

    @staticmethod
    def resolve_dao_job_config(root, info, dao_id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        record = DAOJobConfigModel.objects(dao_id=dao_id).first()
        return record

    @staticmethod
    def resolve_dao(root, info, id=None, name=None):
        return DAO().get_query(info, id, name)

    @staticmethod
    def resolve_dao_github_app_status(root, info, name):
        return DAOGithubAppStatus().get(info, name)

    @staticmethod
    def resolve_cycle(root, info, id):
        return CycleQuery(cycle_id=id)


class Mutations(ObjectType):
    create_dao = CreateDAO.Field()
    update_dao_job_config = UpdateDAOJobConfig.Field()
    update_dao_follow = UpdateDAOFollow.Field()
    update_dao_base_info = UpdateDAOBaseInfo.Field()
    create_job = CreateJob.Field()
    update_job = UpdateJob.Field()
    update_job_vote_type_by_owner = UpdateJobVoteTypeByOwner.Field()
    update_icpper_stat_owner_ei = UpdateIcpperStatOwnerEi.Field()
    publish_cycle_vote_result_by_owner = PublishCycleVoteResultByOwner.Field()
    update_pair_vote = UpdatePairVote.Field()
    update_all_vote = UpdateALLVote.Field()
    create_cycle_vote_pair_task_by_owner = CreateCycleVotePairTaskByOwner.Field()
    change_vote_result_public = ChangeVoteResultPublic.Field()
    create_mock = CreateMock.Field()
