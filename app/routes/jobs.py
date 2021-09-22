import decimal
import os
import time
from collections import defaultdict

from graphene import ObjectType, List, Int, Float, String, Field, Mutation, Boolean, Decimal, InputObjectType

import settings
from app.common.models.icpdao.cycle import CycleIcpperStat, Cycle
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, JobStatusEnum, JobPRComment
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.user import User

from app.common.schema.icpdao import JobSchema, JobPRSchema
from app.common.utils.errors import JOB_UPDATE_STATUS_INVALID_ERROR, JOB_QUERY_NOT_USER_ERROR, COMMON_NOT_AUTH_ERROR, \
    COMMON_NOT_FOUND_DAO_ERROR, JOB_QUERY_NOT_FOUND_ERROR, COMMON_NOT_PERMISSION_ERROR, JOB_DELETE_INVALID_ERROR, \
    CYCLE_NOT_FOUND_ERROR, CYCLE_PAIR_UPDATE_TYPE_ERROR, CYCLE_ICPPER_STAT_NOT_FOUND_ERROR, \
    CYCLE_UPDATE_EI_VALUE_INVALID_ERROR, CYCLE_UPDATE_EI_TIME_ERROR
from app.common.utils.github_app.client import GithubAppClient
from app.common.utils.route_helper import get_current_user_by_graphql
from app.common.utils import check_size
from app.controllers.task import delete_issue_comment, sync_job_pr
from app.routes.schema import SortedTypeEnum, UpdateJobVoteTypeByOwnerArgumentPairTypeEnum

from app.controllers.job import update_job_by_size, create_job, update_job_pr, create_auto_pr


class JobsStat(ObjectType):
    size = Float()
    token_name = String()
    token_count = Float()


class Job(ObjectType):
    node = Field(JobSchema)
    prs = List(JobPRSchema)


class Jobs(ObjectType):
    job = List(Job)
    stat = Field(JobsStat)
    total = Int()

    def get_query_job_list(self, info, dao_name=None, begin_time=None,
                           end_time=None, sorted=None, sorted_type=None,
                           first=20, offset=0, user_name=None):
        query_user_id = None
        current_user = get_current_user_by_graphql(info)
        if current_user:
            query_user_id = str(current_user.id)
        if user_name is not None:
            user = User.objects(github_login=user_name).first()
            if not user:
                raise ValueError(JOB_QUERY_NOT_USER_ERROR)
            query_user_id = str(user.id)

        if not query_user_id:
            raise ValueError(JOB_QUERY_NOT_USER_ERROR)

        _filter = {'user_id': query_user_id}
        if dao_name:
            dao = DAOModel.objects(name=dao_name).first()
            if dao:
                _filter['dao_id'] = str(dao.id)

        if begin_time:
            _filter['create_at__gte'] = begin_time
        if end_time:
            _filter['create_at__lte'] = end_time

        _sorted = '-create_at'
        if sorted:
            if sorted_type == SortedTypeEnum.desc:
                _sorted = f'-{sorted}'
            else:
                _sorted = sorted

        total = JobModel.objects(**_filter).order_by(_sorted).count()
        job_list = JobModel.objects(**_filter).order_by(_sorted).skip(
            offset).limit(first)

        setattr(self, 'query_list', job_list)
        setattr(self, 'total', total)
        return self

    def resolve_job(self, info):
        query_list = getattr(self, 'query_list')
        job_ids = {str(job.id) for job in query_list}
        job_prs_data = JobPRModel.objects(job_id__in=job_ids).all()
        job_prs = defaultdict(list)
        for pr in job_prs_data:
            job_prs[pr.job_id].append(pr)

        results = []
        for job in query_list:
            results.append(Job(
                node=job,
                prs=job_prs[str(job.id)]
            ))
        return results

    def resolve_stat(self, info):
        query_list = getattr(self, 'query_list')
        size = query_list.sum('size')
        return JobsStat(size=size, token_name='', token_count=0)

    def resolve_total(self, info):
        return getattr(self, 'total', 0)


class RequestPR(InputObjectType):
    id = Int(required=True)
    html_url = String(required=True)


class CreateJob(Mutation):
    class Arguments:
        issue_link = String(required=True)
        size = Float(required=True)
        auto_create_pr = Boolean(required=True)
        prs = List(RequestPR)

    job = Field(Job)

    def mutate(self, info, issue_link, size, auto_create_pr, prs: List(RequestPR) = None):
        check_size(size)
        prs_dict = {}
        if prs is not None:
            for pr in prs:
                prs_dict[pr.id] = pr.html_url
        record, ret_prs = create_job(info, issue_link, size, auto_create_pr, prs_dict)
        return CreateJob(job=Job(node=record, prs=ret_prs))


class UpdateJob(Mutation):
    class Arguments:
        id = String(required=True)
        size = Float(required=True)
        auto_create_pr = Boolean(required=True)
        prs = List(RequestPR)

    job = Field(Job)

    def mutate(root, info, id, size, auto_create_pr, prs: List(RequestPR) = None):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError(COMMON_NOT_AUTH_ERROR)
        job = JobModel.objects(id=id).first()
        if not job:
            raise FileNotFoundError(JOB_QUERY_NOT_FOUND_ERROR)
        assert job.status in [JobStatusEnum.AWAITING_MERGER.value, JobStatusEnum.MERGED.value], JOB_UPDATE_STATUS_INVALID_ERROR
        dao = DAOModel.objects(id=job.dao_id).first()
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
        app_client = GithubAppClient(app_token, job.github_repo_owner)
        if decimal.Decimal(size) != job.size:
            check_size(size)
            update_job_by_size(info, app_client, current_user, job, size)
        prs_dict = {}
        if prs is not None:
            for pr in prs:
                prs_dict[pr.id] = pr.html_url
        if job.had_auto_create_pr is False and auto_create_pr is True:
            ret_prs = update_job_pr(info, app_client, current_user, job, True, prs_dict)
        else:
            ret_prs = update_job_pr(info, app_client, current_user, job, False, prs_dict)
        return UpdateJob(job=Job(node=job, prs=list(ret_prs)))


class DeleteJob(Mutation):
    class Arguments:
        id = String(required=True)

    ok = Boolean()

    def mutate(root, info, id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError(COMMON_NOT_AUTH_ERROR)
        job = JobModel.objects(id=id).first()
        if not job:
            raise FileNotFoundError(JOB_QUERY_NOT_FOUND_ERROR)
        dao = DAOModel.objects(id=job.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_AUTH_ERROR)
        if job.user_id != str(current_user.id):
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)
        if job.status != JobStatusEnum.AWAITING_MERGER.value:
            raise ValueError(JOB_DELETE_INVALID_ERROR)

        need_delete_bot_comment_info_list = []
        github_repo_owner = job.github_repo_owner
        need_delete_bot_comment_info_list.append({
            "repo_name": job.github_repo_name,
            "comment_id": job.bot_comment_database_id
        })
        prs = JobPRModel.objects(job_id=id).all()
        for pr in prs:
            for job_pr_comment in JobPRComment.objects(
                github_repo_id=pr.github_repo_id,
                github_pr_number=pr.github_pr_number
            ):
                need_delete_bot_comment_info_list.append({
                    "repo_name": pr.github_repo_name,
                    "comment_id": job_pr_comment.bot_comment_database_id
                })

            JobPRComment.objects(
                github_repo_id=pr.github_repo_id,
                github_pr_number=pr.github_pr_number
            ).delete()
        JobPRModel.objects(job_id=id).delete()
        job.delete()

        if os.environ.get('IS_UNITEST') != 'yes':
            info.context["background"].add_task(
                delete_issue_comment, dao_id=str(dao.id),
                github_repo_owner=github_repo_owner,
                need_delete_bot_comment_info_list=need_delete_bot_comment_info_list)

        return DeleteJob(ok=True)


class UpdateJobVoteTypeByOwner(Mutation):
    class Arguments:
        id = String(required=True)
        vote_type = UpdateJobVoteTypeByOwnerArgumentPairTypeEnum()

    ok = Boolean()

    def mutate(self, info, id, vote_type):
        job = JobModel.objects(id=id).first()
        if not job:
            raise ValueError(JOB_QUERY_NOT_FOUND_ERROR)

        if not job.cycle_id:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        cycle = Cycle.objects(id=job.cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        dao = DAOModel.objects(id=job.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)

        current_time = int(time.time())
        if current_time > cycle.pair_end_at or current_time < cycle.pair_begin_at:
            raise ValueError(CYCLE_PAIR_UPDATE_TYPE_ERROR)

        job.pair_type = vote_type
        job.save()
        return UpdateJobVoteTypeByOwner(ok=True)


class UpdateIcpperStatOwnerEi(Mutation):
    class Arguments:
        id = String(required=True)
        owner_ei = Decimal()

    ei = Decimal()
    vote_ei = Decimal()
    owner_ei = Decimal()

    def mutate(self, info, id, owner_ei):
        icpper_stat = CycleIcpperStat.objects(id=id).first()
        if not icpper_stat:
            raise ValueError(CYCLE_ICPPER_STAT_NOT_FOUND_ERROR)

        cycle = Cycle.objects(id=icpper_stat.cycle_id).first()
        if not cycle:
            raise ValueError(CYCLE_NOT_FOUND_ERROR)

        dao = DAOModel.objects(id=icpper_stat.dao_id).first()
        if not dao:
            raise ValueError(COMMON_NOT_FOUND_DAO_ERROR)

        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError(COMMON_NOT_PERMISSION_ERROR)

        if not cycle.vote_result_stat_at or cycle.vote_result_published_at:
            raise ValueError(CYCLE_UPDATE_EI_TIME_ERROR)

        if owner_ei < decimal.Decimal('-0.2') or owner_ei > decimal.Decimal('0.2'):
            raise ValueError(CYCLE_UPDATE_EI_VALUE_INVALID_ERROR)

        icpper_stat.owner_ei = owner_ei
        icpper_stat.ei = icpper_stat.vote_ei + icpper_stat.owner_ei
        icpper_stat.save()

        return UpdateIcpperStatOwnerEi(
            ei=icpper_stat.ei,
            vote_ei=icpper_stat.vote_ei,
            owner_ei=icpper_stat.owner_ei
        )
