import decimal
import os
import time
from collections import defaultdict

from graphene import ObjectType, List, Int, Float, String, Field, Mutation, Boolean, Decimal

import settings
from app.common.models.icpdao.cycle import CycleIcpperStat, Cycle
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, JobStatusEnum, JobPRComment
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.user import User

from app.common.schema.icpdao import JobSchema, JobPRSchema
from app.common.utils.github_app.client import GithubAppClient
from app.common.utils.route_helper import get_current_user_by_graphql
from app.common.utils import check_size
from app.controllers.task import delete_issue_comment
from app.routes.schema import SortedTypeEnum, UpdateJobVoteTypeByOwnerArgumentPairTypeEnum

from app.controllers.job import delete_job_pr, update_job_by_size, add_job_pr, \
    create_job


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
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        user_id = str(current_user.id)
        if user_name is not None:
            user = User.objects(github_login=user_name).first()
            if not user:
                raise ValueError("NOT FIND QUERY USER NAME")
            user_id = str(user.id)

        _filter = {'user_id': user_id}
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

        job_list = JobModel.objects(**_filter).order_by(_sorted).skip(
            offset).limit(first)

        setattr(self, 'query_list', job_list)
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
        query_list = getattr(self, 'query_list')
        return query_list.count()


class CreateJob(Mutation):
    class Arguments:
        issue_link = String(required=True)
        size = Float(required=True)

    job = Field(Job)

    def mutate(self, info, issue_link, size):
        check_size(size)
        record = create_job(info, issue_link, size)
        return CreateJob(job=Job(node=record, prs=[]))


class UpdateJob(Mutation):
    class Arguments:
        id = String(required=True)
        size = Float()
        # github pr link or file link
        add_pr = String()
        # job pr id
        delete_pr = String()

    job = Field(Job)

    def mutate(root, info, id, size=None, add_pr=None, delete_pr=None):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        job = JobModel.objects(id=id).first()
        if not job:
            raise FileNotFoundError('NOT JOB')
        dao = DAOModel.objects(id=job.dao_id).first()
        if not dao:
            raise ValueError('NOT DAO')
        app_token = GithubAppToken.get_token(
            app_id=settings.ICPDAO_GITHUB_APP_ID,
            app_private_key=settings.ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY,
            github_owner_name=dao.github_owner_name,
            github_owner_id=dao.github_owner_id,
        )
        if app_token is None:
            raise ValueError('NOT APP TOKEN')
        app_client = GithubAppClient(app_token, job.github_repo_owner)
        if size:
            check_size(size)
            update_job_by_size(info, app_client, current_user, job, size)
        if delete_pr:
            delete_job_pr(info, app_client, delete_pr)
        if add_pr:
            add_job_pr(info, app_client, current_user, job, add_pr)

        prs = JobPRModel.objects(job_id=id).all()

        return UpdateJob(job=Job(node=job, prs=list(prs)))


class DeleteJob(Mutation):
    class Arguments:
        id = String(required=True)

    ok = Boolean()

    def mutate(root, info, id):
        current_user = get_current_user_by_graphql(info)
        if not current_user:
            raise PermissionError('NOT LOGIN')
        job = JobModel.objects(id=id).first()
        if not job:
            raise FileNotFoundError('NOT JOB')
        dao = DAOModel.objects(id=job.dao_id).first()
        if not dao:
            raise ValueError('NOT DAO')
        if job.user_id != str(current_user.id):
            raise ValueError('NOT ROLE')
        if job.status != JobStatusEnum.AWAITING_MERGER.value:
            raise ValueError('NOT SUPPORT')

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
            raise ValueError('NOT JOB')

        if not job.cycle_id:
            raise ValueError('NOT CYCLE')

        cycle = Cycle.objects(id=job.cycle_id).first()
        if not cycle:
            raise ValueError('NOT CYCLE')

        dao = DAOModel.objects(id=job.dao_id).first()
        if not dao:
            raise ValueError('NOT DAO')

        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError('NOT ROLE')

        current_time = int(time.time())
        if current_time > cycle.pair_end_at or current_time < cycle.pair_begin_at:
            raise ValueError('CURRENT TIME NOT IN CHANGE CYCLE')

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
            raise ValueError('NOT ICPPER_STAT')

        cycle = Cycle.objects(id=icpper_stat.cycle_id).first()
        if not cycle:
            raise ValueError('NOT CYCLE')

        dao = DAOModel.objects(id=icpper_stat.dao_id).first()
        if not dao:
            raise ValueError('NOT DAO')

        current_user = get_current_user_by_graphql(info)
        if str(current_user.id) != dao.owner_id:
            raise ValueError('NOT ROLE')

        if not cycle.vote_result_stat_at or cycle.vote_result_published_at:
            raise ValueError('CURRENT TIME NO IN CHANGE CYCLE')

        if owner_ei < decimal.Decimal('-0.2') or owner_ei > decimal.Decimal('0.2'):
            raise ValueError('OWNER_EI MUST IN -0.2 TO 0.2 RANGE')

        icpper_stat.owner_ei = owner_ei
        icpper_stat.ei = icpper_stat.vote_ei + icpper_stat.owner_ei
        icpper_stat.save()

        return UpdateIcpperStatOwnerEi(
            ei=icpper_stat.ei,
            vote_ei=icpper_stat.vote_ei,
            owner_ei=icpper_stat.owner_ei
        )
