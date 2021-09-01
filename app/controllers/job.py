import os

import settings
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.job import JobPRStatusEnum
from app.common.models.icpdao.user import User as UserModel, UserStatus
from app.common.models.icpdao.user_github_token import UserGithubToken
from app.common.models.logic.user_helper import user_auth_follow_dao, check_user_access_token
from app.common.utils.github_app.client import GithubAppClient
from app.common.utils.github_app.utils import parse_pr, LinkType, parse_issue
from app.common.utils.github_rest_api import get_github_org_id
from app.common.utils.route_helper import get_current_user_by_graphql
from app.controllers.task import update_issue_comment, sync_job_pr, sync_job_prs
from app.common.models.icpdao.dao import DAO as DAOModel
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, \
    JobStatusEnum
from settings import (
    ICPDAO_GITHUB_APP_CLIENT_ID,
    ICPDAO_GITHUB_APP_CLIENT_SECRET
)


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
        prs = JobPRModel.objects(
            job_id=str(job.id), status=JobPRStatusEnum.MERGED.value
        ).distinct('merged_user_github_user_id')
        is_merged_user = current_user.github_user_id in prs
        is_job_owner = str(current_user.id) == job.user_id
        if is_job_owner and not is_merged_user:
            if size < job.size:
                job.size = size
                job.save()
                tasks.add_task(
                    update_issue_comment, app_client=app_client, job=job)
                return job
            raise PermissionError('error.update_job_size.only_reduce')
        if is_merged_user:
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


def create_auto_pr(current_user, job_user, app_client, job):
    if str(current_user.id) != str(job_user.id):
        raise ValueError('ONLY JOB USER CAN PUSH LINK')
    success, ret = app_client.create_pr(
        f'https://github.com/{job.github_repo_owner}/{job.github_repo_name}/issues/{job.github_issue_number}',
        job.github_repo_name,
        job.github_issue_number,
        job_user.github_login
    )
    if success is False:
        raise ValueError(ret)
    # Github has two ids for PR: Issue and pull. Here is the unified universal issue ID
    success, pr_issue_info = app_client.get_issue(job.github_repo_name, ret['number'])
    if success is False:
        raise ValueError(ret)
    pr_record = JobPRModel(
        job_id=str(job.id),
        title=ret['title'],
        user_id=job.user_id,
        github_repo_owner=job.github_repo_owner,
        github_repo_name=job.github_repo_name,
        github_repo_owner_id=job.github_repo_owner_id,
        github_repo_id=job.github_repo_id,
        github_pr_number=ret['number'],
        github_pr_id=pr_issue_info['id'],
        status=ret['state'],
        is_auto_create_pr=True
    )
    job.had_auto_create_pr = True
    job.save()
    pr_record.save()
    return pr_record


def update_job_pr(info, app_client: GithubAppClient, current_user, job, auto_create_pr: bool, prs: dict):
    job_user = UserModel.objects(id=job.user_id).first()
    ugt = UserGithubToken.objects(github_user_id=current_user.github_user_id).first()
    if os.environ.get('IS_UNITEST') != 'yes':
        check_user_access_token(current_user, ICPDAO_GITHUB_APP_CLIENT_ID, ICPDAO_GITHUB_APP_CLIENT_SECRET)
    exists_job_prs = JobPRModel.objects(job_id=str(job.id)).all()
    exists_job_prs_dict = {}
    exists_job_github_pr_ids = []
    need_sync_job_prs = []
    ret_prs = []
    for pr in exists_job_prs:
        if prs.get(pr.github_pr_id) is None:
            need_sync_job_prs.append(pr)
            pr.delete()
            continue
        exists_job_github_pr_ids.append(pr.github_pr_id)
        exists_job_prs_dict[pr.github_pr_id] = pr

    for pid in prs:
        if pid in exists_job_github_pr_ids:
            ret_prs.append(exists_job_prs_dict[pid])
            continue

        pr_link = prs[pid]
        link_info = parse_pr(pr_link)
        if link_info['success'] is False:
            raise ValueError(link_info['msg'])

        github_org_id = get_github_org_id(ugt.access_token, link_info["parse"]["github_repo_owner"])
        if github_org_id != job.github_repo_owner_id:
            raise ValueError("job and job pr not one org")

        parse_info = link_info['parse']

        repo = app_client.get_repo(parse_info['github_repo_name'])

        success, ret = app_client.get_pr(
            parse_info['github_repo_name'],
            parse_info['github_pr_number'],
        )
        if success is False:
            raise ValueError('NOT GET PR')
        if ret['closed_at'] and not ret['merged_at']:
            raise ValueError('PR ALREADY CLOSED')
        if ret['state'] == JobPRStatusEnum.MERGED.value and \
                current_user.github_user_id != ret['merged_user_github_user_id']:
            raise ValueError('ONLY MERGED LOGIN CAN OP MERGED PR')
        if ret['state'] == JobPRStatusEnum.AWAITING_MERGER.value:
            if current_user.github_user_id not in ret[
                'can_link_github_user_id_list'] or job_user.github_user_id not in ret[
                  'can_link_github_user_id_list']:
                raise ValueError('CURRENT USER OR JOB USER NOT IN PR')

        success, pr_issue_info = app_client.get_issue(
            parse_info['github_repo_name'],
            parse_info['github_pr_number'],
        )
        assert success, 'error.update_job.not_get_pr'
        assert pr_issue_info['id'] == pid, 'error.update_job.pid'

        pr_record = JobPRModel(
            job_id=str(job.id),
            user_id=job.user_id,
            title=ret['title'],
            github_repo_owner=repo['owner']['login'],
            github_repo_name=repo['name'],
            github_repo_owner_id=repo['owner']['id'],
            github_repo_id=repo['id'],
            github_pr_number=parse_info['github_pr_number'],
            github_pr_id=pid,
            status=ret['state'],
            merged_user_github_user_id=ret['merged_user_github_user_id'],
            merged_at=ret['merged_at'],
        )
        pr_record.save()
        need_sync_job_prs.append(pr_record)
        ret_prs.append(pr_record)
    if auto_create_pr:
        pr_record = create_auto_pr(current_user, job_user, app_client, job)
        need_sync_job_prs.append(pr_record)
        ret_prs.append(pr_record)

    info.context["background"].add_task(
        sync_job_prs, app_client=app_client, job_prs=need_sync_job_prs)
    return ret_prs


def create_job(info, issue_link, size, auto_create_pr, prs):
    current_user = get_current_user_by_graphql(info)
    if not current_user:
        raise PermissionError('NOT LOGIN')
    if current_user.status == UserStatus.NORMAL.value:
        raise PermissionError('ONLY PRE-ICPPER AND ICPPER CAN MARK JOB')

    if os.environ.get('IS_UNITEST') != 'yes':
        check_user_access_token(current_user, ICPDAO_GITHUB_APP_CLIENT_ID, ICPDAO_GITHUB_APP_CLIENT_SECRET)

    issue_info = parse_issue(issue_link)
    if issue_info is False:
        raise ValueError('error.mark_job.error_link')

    github_repo_owner = issue_info['parse']['github_repo_owner']
    ugt = UserGithubToken.objects(github_user_id=current_user.github_user_id).first()
    github_org_id = get_github_org_id(ugt.access_token, github_repo_owner)
    dao = DAOModel.objects(
        github_owner_id=github_org_id).first()
    if not dao:
        raise ValueError('error.mark_job.unknown_dao')

    app_token = GithubAppToken.get_token(
        app_id=settings.ICPDAO_GITHUB_APP_ID,
        app_private_key=settings.ICPDAO_GITHUB_APP_RSA_PRIVATE_KEY,
        github_owner_name=github_repo_owner,
        github_owner_id=dao.github_owner_id,
    )
    if app_token is None:
        raise ValueError('NOT APP TOKEN')
    app_client = GithubAppClient(app_token, github_repo_owner)
    repo = app_client.get_repo(issue_info['parse']['github_repo_name'])

    exist = JobModel.objects(
        github_repo_id=repo['id'],
        github_issue_number=issue_info['parse']['github_issue_number'],
    ).first()
    if exist:
        raise ValueError('error.mark_job.same_link')

    success, issue = app_client.get_issue(
        issue_info['parse']['github_repo_name'],
        issue_info['parse']['github_issue_number'])
    if not success:
        raise ValueError('NOT GET ISSUE')
    if issue['user']['id'] != current_user.github_user_id:
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
        dao_id=str(dao.id),
        user_id=str(current_user.id),
        title=issue['title'],
        body_text=issue['body'],
        size=size,
        github_repo_owner=repo['owner']['login'],
        github_repo_name=issue_info['parse']['github_repo_name'],
        github_repo_owner_id=repo['owner']['id'],
        github_repo_id=repo['id'],
        github_issue_number=issue_info['parse']['github_issue_number'],
        status=JobStatusEnum.AWAITING_MERGER.value,
        bot_comment_database_id=res['id'],
        had_auto_create_pr=auto_create_pr
    )
    record.save()
    ret_prs = update_job_pr(info, app_client, current_user, record, auto_create_pr, prs)
    user_auth_follow_dao(str(current_user.id), str(dao.id))
    return record, ret_prs
