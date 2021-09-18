import decimal

from graphene import ObjectType, String, Field, Int, List

import settings
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import Job
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.utils.errors import COMMON_NOT_AUTH_ERROR, COMMON_NOT_FOUND_DAO_ERROR, OPEN_GITHUB_PARAMETER_ERROR, \
    OPEN_GITHUB_RUN_ERROR
from app.common.utils.github_app import GithubAppClient
from app.common.utils.route_helper import get_current_user_by_graphql
from app.routes.config import UpdateDAOJobConfig, DAOJobConfig, DAOTokenConfig
from app.routes.cycles import CycleQuery, CreateCycleVotePairTaskByOwner, \
    ChangeVoteResultPublic, CreateCycleVoteResultStatTaskByOwner, CreateCycleVoteResultPublishTaskByOwner, \
    UserIcpperStatsQuery, CycleByTokenUnreleasedQuery, MarkCyclesTokenReleased, VotingCycleQuery
from app.routes.daos import DAOs, CreateDAO, DAO, UpdateDAOBaseInfo, DAOGithubAppStatus, DAOsStat, DAOItem, DAOStat, \
    get_query_dao_list, HomeStats
from app.routes.follow import UpdateDAOFollow
from app.routes.jobs import Jobs, CreateJob, UpdateJob, UpdateJobVoteTypeByOwner, UpdateIcpperStatOwnerEi, DeleteJob
from app.routes.mock import CreateMock
from app.routes.open_github import OpenGithubQuery
from app.routes.schema import DAOsFilterEnum, DAOsSortedEnum, \
    DAOsSortedTypeEnum, JobSortedEnum, SortedTypeEnum, DAOJobConfigQueryArgs, CyclesTokenUnreleasedQueryArgs, \
    DAOQueryArgs, OpenGithubWayEnum
from app.routes.token_mint_records import CreateTokenMintRecord, LinkTxHashForTokenMintRecord, DropTokenMintRecord, \
    SyncTokenMintRecordEvent, FindLostTxForInitTokenMintRecord, FindLostTxForDropTokenMintRecord, \
    FindLostTxForDropTokenMintRecord
from app.routes.vote import UpdatePairVote, UpdateALLVote, UpdateVoteConfirm


class Query(ObjectType):
    stats = Field(HomeStats)

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

    open_github = Field(
        OpenGithubQuery,
        dao_name=String(required=True),
        way=OpenGithubWayEnum(required=True),
        parameter=List(String)
    )

    @staticmethod
    def resolve_stats(root, info):
        all_dao_ids = DAOModel.objects().distinct('_id')
        all_dao_ids_str = [str(i) for i in all_dao_ids]
        icpper = Job.objects(dao_id__in=all_dao_ids_str).distinct('user_id')
        size = Job.objects(dao_id__in=all_dao_ids_str).sum('size')
        income = Job.objects(dao_id__in=all_dao_ids_str).sum('income')
        return HomeStats(
            dao=len(all_dao_ids_str), icpper=len(icpper), size=decimal.Decimal(size), income=decimal.Decimal(income))

    @staticmethod
    def resolve_daos(root, info, **kwargs):
        query_dao_list, all_dao_ids = get_query_dao_list(info, **kwargs)
        all_dao_ids_str = [str(i) for i in all_dao_ids]
        icpper = Job.objects(dao_id__in=all_dao_ids_str).distinct('user_id')
        size = Job.objects(dao_id__in=all_dao_ids_str).sum('size')
        income = Job.objects(dao_id__in=all_dao_ids_str).sum('income')
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

    @staticmethod
    def resolve_open_github(root, info, dao_name, way, parameter=None):
        current_user = get_current_user_by_graphql(info)
        assert current_user, COMMON_NOT_AUTH_ERROR

        dao = DAOModel.objects(github_owner_name=dao_name).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        app_token = GithubAppToken.get_token(
            app_id=settings.ICPDAO_GITHUB_APP_ID,
            app_private_key=settings.ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY,
            github_owner_name=dao.github_owner_name,
            github_owner_id=dao.github_owner_id,
        )
        if app_token is None:
            raise ValueError('NOT APP TOKEN')
        app_client = GithubAppClient(app_token, dao.github_owner_name)
        if way == OpenGithubWayEnum.ISSUE_TIMELINE.value:
            assert (parameter is not None) and (len(parameter) == 2), OPEN_GITHUB_PARAMETER_ERROR
            success, ret = app_client.get_issue_timeline(parameter[0], parameter[1])
            assert success is True, OPEN_GITHUB_RUN_ERROR
            return OpenGithubQuery(way=way, data=ret)
        if way == OpenGithubWayEnum.ISSUE_INFO.value:
            assert (parameter is not None) and (len(parameter) == 2), OPEN_GITHUB_PARAMETER_ERROR
            success, ret = app_client.get_issue(parameter[0], parameter[1])
            assert success is True, OPEN_GITHUB_RUN_ERROR
            return OpenGithubQuery(way=way, data=ret)
        if way == OpenGithubWayEnum.OPEN_PR.value:
            assert (parameter is not None) and (len(parameter) == 1), OPEN_GITHUB_PARAMETER_ERROR
            success, ret = app_client.get_user_open_pr(parameter[0])
            assert success is True, OPEN_GITHUB_RUN_ERROR
            return OpenGithubQuery(way=way, data=ret)
        raise ValueError('')


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
    create_token_mint_record = CreateTokenMintRecord.Field()
    link_tx_hash_for_token_mint_record = LinkTxHashForTokenMintRecord.Field()
    drop_token_mint_record = DropTokenMintRecord.Field()
    sync_token_mint_record_event = SyncTokenMintRecordEvent.Field()
    find_lost_tx_for_init_token_mint_record = FindLostTxForInitTokenMintRecord.Field()
    find_lost_tx_for_drop_token_mint_record = FindLostTxForDropTokenMintRecord.Field()
