import settings
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import JobPRStatusEnum
from app.common.models.icpdao.user import User as UserModel, UserStatus
from app.common.utils.github_app.client import GithubAppClient
from app.common.utils.github_app.utils import parse_pr, LinkType, parse_issue
from app.common.utils.route_helper import get_current_user_by_graphql
from app.controllers.task import update_issue_comment, sync_job_pr
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, \
    JobStatusEnum


def update_job_by_size(info, app_client: GithubAppClient, current_user, job, size):
    tasks = info.context["background"]
    if job.status == JobStatusEnum.AWAITING_MERGER.value:
        if str(current_user.id) == job.user_id:
            job.size = size
            job.save()
            tasks.add_task(
                update_issue_comment, app_client=app_client, job=job)
            return job
        raise PermissionError('JOB NOT MERGED, ONLY USER CAN UPDATE SIZE')
    if job.status == JobStatusEnum.MERGED.value:
        if str(current_user.id) == job.user_id:
            if size < job.size:
                job.size = size
                job.save()
                tasks.add_task(
                    update_issue_comment, app_client=app_client, job=job)
                return job
            raise PermissionError('JOB MERGED, USER ONLY CAN REDUCE SIZE')
        prs = JobPRModel.objects(
            job_id=id, status=JobPRStatusEnum.MERGED.value
        ).distinct('merged_user_github_login')
        if current_user.github_login in prs:
            if size > job.size:
                job.size = size
                job.save()
                tasks.add_task(
                    update_issue_comment, app_client=app_client, job=job)
                return job
            raise PermissionError(
                'JOB MERGED, REVIEWER ONLY CAN ADJUST SIZE')
        raise PermissionError('NOT RIGHT PERMISSION')
    raise PermissionError('JOB NOT IN MERGED OR MERGING STATUS')


def delete_job_pr(info, app_client, del_pr):
    job_pr = JobPRModel.objects(id=del_pr).first()
    if job_pr:
        job_pr.delete()
    info.context["background"].add_task(
        sync_job_pr, app_client=app_client, job_pr=job_pr)


def add_job_pr(info, app_client: GithubAppClient, current_user, job, pr_link):
    job_user = UserModel.objects(id=job.user_id).first()
    link_info = parse_pr(pr_link, job.github_repo_owner)
    if link_info['success'] is False:
        raise ValueError(link_info['msg'])
    pr_record = JobPRModel(job_id=str(job.id))
    if link_info['type'] == LinkType.pr:
        parse_info = link_info['parse']
        success, ret = app_client.get_pr(
            parse_info['github_repo_name'],
            parse_info['github_pr_number'],
        )
        if success is False:
            raise ValueError('NOT GET PR')
        if ret['closed_at']:
            raise ValueError('PR ALREADY CLOSED')
        if ret['state'] == JobPRStatusEnum.MERGED.value and str(
                current_user.github_login) != ret['merged_login']:
            raise ValueError('ONLY MERGED LOGIN CAN OP MERGED PR')
        if ret['state'] == JobPRStatusEnum.AWAITING_MERGER.value:
            if current_user.github_login not in ret[
                'can_link_logins'] or job_user.github_login not in ret[
                  'can_link_logins']:
                raise ValueError('CURRENT USER OR JOB USER NOT IN PR')
        pr_record = JobPRModel(
            job_id=str(job.id),
            user_id=job.user_id,
            title=ret['title'],
            github_repo_owner=job.github_repo_owner,
            github_repo_name=parse_info['github_repo_name'],
            github_repo_id=job.github_repo_id,
            github_pr_number=parse_info['github_pr_number'],
            status=ret['state'],
            merged_user_github_login=ret['merged_login'],
            merged_at=ret['merged_at'],
        )
        pr_record.save()
    if link_info['type'] == LinkType.other:
        if str(current_user.id) != str(job_user.id):
            raise ValueError('ONLY JOB USER CAN PUSH LINK')
        success, ret = app_client.create_pr(
            pr_link,
            job.github_repo_name,
            job.github_issue_number,
            job_user.github_login
        )
        if success is False:
            raise ValueError(ret)

        pr_record = JobPRModel(
            job_id=str(job.id),
            title=ret['title'],
            user_id=job.user_id,
            github_repo_owner=job.github_repo_owner,
            github_repo_name=job.github_repo_name,
            github_repo_id=job.github_repo_id,
            github_pr_number=ret['number'],
            status=ret['state'],
        )
        pr_record.save()
    info.context["background"].add_task(
        sync_job_pr, app_client=app_client, job_pr=pr_record)


def create_job(info, dao_id, issue_link, size):
    current_user = get_current_user_by_graphql(info)
    if not current_user:
        raise PermissionError('NOT LOGIN')
    if current_user.status != UserStatus.ICPPER.value:
        raise PermissionError('ONLY ICPPER CAN MARK JOB')
    dao = DAOModel.objects(id=dao_id).first()
    if not dao:
        raise ValueError('NOT DAO')

    issue_info = parse_issue(issue_link, dao.name)
    if issue_info is False:
        raise ValueError('ILLEGAL ISSUE LINK')

    app_token = GithubAppToken.get_token(
        app_id=settings.ICPDAO_GITHUB_APP_ID,
        app_private_key=settings.ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY,
        dao_name=dao.name
    )
    if app_token is None:
        raise ValueError('NOT APP TOKEN')
    app_client = GithubAppClient(app_token, dao.name)
    repo = app_client.get_repo(issue_info['parse']['github_repo_name'])

    exist = JobModel.objects(
        github_repo_id=repo['id'],
        github_issue_number=issue_info['parse']['github_issue_number'],
    ).first()
    if exist:
        raise ValueError('THIS ISSUE HAD EXIST')

    success, issue = app_client.get_issue(
        issue_info['parse']['github_repo_name'],
        issue_info['parse']['github_issue_number'])
    if not success:
        raise ValueError('NOT GET ISSUE')
    if issue['user']['login'] != current_user.github_login:
        raise ValueError('ONLY ISSUE USER CAN MARK THIS ISSUE')
    if issue['state'] != 'open':
        raise ValueError('ONLY OPEN ISSUE CAN MARK')

    comment = """Job Status: **%s**
Job User: @%s
Job Size: %.1f
by @icpdao
""" % (JobStatusEnum(JobStatusEnum.AWAITING_MERGER.value).name, current_user.github_login, size)
    success, res = app_client.create_comment(
        issue_info['parse']['github_repo_name'],
        issue_info['parse']['github_issue_number'],
        comment
    )
    if not success:
        raise ValueError('CREATE COMMENT ERROR')
    record = JobModel(
        dao_id=dao_id,
        user_id=str(current_user.id),
        title=issue['title'],
        body_text=issue['body'],
        size=size,
        github_repo_owner=dao.name,
        github_repo_name=issue_info['parse']['github_repo_name'],
        github_repo_id=repo['id'],
        github_issue_number=issue_info['parse']['github_issue_number'],
        status=JobStatusEnum.AWAITING_MERGER.value,
        bot_comment_database_id=res['id']
    )
    record.save()
    return record
