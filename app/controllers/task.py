import time
from collections import defaultdict

from app.common.models.icpdao.cycle import Cycle
from app.common.models.icpdao.dao import DAOJobConfig
from app.common.models.icpdao.user import User as UserModel
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, \
    JobStatusEnum, JobPRComment, JobPRStatusEnum
from app.common.utils import get_next_time


def update_issue_comment(app_client, job):
    job_user = UserModel.objects(id=job.user_id).first()
    comment = """Job Status: **%s**
Job User: @%s
Job Size: %.1f
by @icpdao
""" % (JobStatusEnum(job.status).name, job_user.github_login, job.size)
    success, res = app_client.update_comment(
        job.github_repo_name, job.bot_comment_database_id, comment
    )


def get_or_create_dao_cycle(dao_id, job_last_merged_at):
    query = Cycle.objects(
        dao_id=dao_id,
        begin_at__lte=job_last_merged_at,
        end_at__gt=job_last_merged_at
    ).first()
    if query and query.is_paired is False:
        return query
    last = Cycle.objects(dao_id=dao_id).order_by('-create_at').first()
    if not last:
        begin_at = job_last_merged_at
    else:
        begin_at = last.end_at

    config = DAOJobConfig.objects(dao_id=dao_id).first()
    end_at = get_next_time(
        config.time_zone, job_last_merged_at,
        config.deadline_day, config.deadline_time)

    pair_begin_at = get_next_time(
        config.time_zone, begin_at,
        config.pair_begin_day, config.pair_begin_hour)
    pair_end_at = get_next_time(
        config.time_zone, begin_at,
        config.pair_end_day, config.pair_end_hour)

    vote_begin_at = get_next_time(
        config.time_zone, begin_at,
        config.voting_begin_day, config.voting_begin_hour)
    vote_end_at = get_next_time(
        config.time_zone, begin_at,
        config.voting_end_day, config.voting_end_hour)

    cycle = Cycle(
        dao_id=dao_id,
        time_zone=config.time_zone,
        begin_at=last.end_at, end_at=end_at,
        pair_begin_at=pair_begin_at, pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at, vote_end_at=vote_end_at)

    cycle.save()
    return cycle


def sync_job_issue_status_comment(app_client, job_ids):
    print(f"job issue status comment, job_ids={''.join(job_ids)}")
    jobs = JobModel.objects(id__in=list(job_ids)).all()
    job_prs = JobPRModel.objects(job_id__in=list(job_ids)).all()
    job_pr_dict = defaultdict(list)
    need_update_comment_jobs = []
    for job_pr in job_prs:
        job_pr_dict[job_pr.job_id].append(job_pr)
    for job in jobs:
        tmp_prs = job_pr_dict[str(job.id)]
        check_status = {i.status for i in tmp_prs}
        if job.status == JobStatusEnum.AWAITING_MERGER.value:
            if check_status == {JobPRStatusEnum.MERGED.value}:
                job.status = JobStatusEnum.MERGED.value
                job.update_at = int(time.time())
                merged_at_list = sorted([i.merged_at for i in tmp_prs])
                if not job.cycle_id:
                    cycle = get_or_create_dao_cycle(
                        job.dao_id, merged_at_list[-1])
                    job.cycle_id = str(cycle.id)

                job.save()

                need_update_comment_jobs.append(job)
        else:
            if not job.cycle_id:
                raise ValueError("NOT AWAITING MERGED JOB NOT CYCLE")
            cycle = Cycle.objects(id=job.cycle_id).first()
            create_at_list = sorted([i.create_at for i in tmp_prs])
            if (len(create_at_list) == 0 and int(time.time()) < cycle.pair_begin_at) or (
                len(create_at_list) > 0 and create_at_list[-1] < cycle.pair_begin_at and check_status != {JobPRStatusEnum.MERGED.value}):
                job.status = JobStatusEnum.AWAITING_MERGER.value
                job.update_at = int(time.time())
                job.cycle_id = None
                job.save()
                need_update_comment_jobs.append(job)
    for update_job in need_update_comment_jobs:
        update_issue_comment(app_client, update_job)


def sync_job_pr_comment(app_client, job_pr, job_ids):
    print(f"job pr comment job_pr: {str(job_pr.id)}, job_ids: {', '.join(job_ids)}")
    jobs = JobModel.objects(id__in=list(job_ids)).order_by('create_at').all()
    comment = []
    for i, job in enumerate(jobs):
        user = UserModel.objects(id=job.user_id).first()
        comment.append(
            f'{i + 1}. for {job.github_repo_owner}/{job.github_repo_name}#'
            f'{job.github_issue_number} by @{user.github_login}')
    comment.append("comment by @icpdao")
    comment_body = '\n'.join(comment)
    pr_comment = JobPRComment.objects(
        github_repo_id=job_pr.github_repo_id,
        github_pr_number=job_pr.github_pr_number
    ).first()
    if not pr_comment:
        success, res = app_client.create_comment(
            job_pr.github_repo_name,
            job_pr.github_pr_number,
            comment_body
        )
        if not success:
            raise ValueError('CREATE COMMENT ERROR')
        pr_comment = JobPRComment(
            github_repo_id=job_pr.github_repo_id,
            github_pr_number=job_pr.github_pr_number,
            bot_comment_database_id=res['id']
        )
        pr_comment.save()
        return pr_comment
    success, res = app_client.update_comment(
        job_pr.github_repo_name,
        pr_comment.bot_comment_database_id, comment_body
    )
    pr_comment.updated_at = int(time.time())
    pr_comment.save()
    return pr_comment


def sync_job_pr(app_client, job_pr):
    print(f'job pr sync, job_pr: {str(job_pr.id)}')
    job_prs = JobPRModel.objects(
        github_repo_id=job_pr.github_repo_id,
        github_pr_number=job_pr.github_pr_number
    ).distinct('job_id')

    job_ids = set(job_prs)

    sync_job_pr_comment(app_client, job_pr, job_ids)
    sync_job_issue_status_comment(app_client, job_ids)