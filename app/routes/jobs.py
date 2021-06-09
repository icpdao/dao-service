from collections import defaultdict

from graphene import ObjectType, List, Int, Float, String, Field, Mutation

import settings
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.user import User

from app.common.schema.icpdao import JobSchema, JobPRSchema
from app.common.utils.github_app.client import GithubAppClient
from app.common.utils.route_helper import get_current_user_by_graphql
from app.common.utils import check_size
from app.routes.schema import SortedTypeEnum


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
            dao_name=dao.name
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
