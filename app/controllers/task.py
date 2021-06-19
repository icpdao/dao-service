import time
from collections import defaultdict

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.dao import DAOJobConfig
from app.common.models.icpdao.user import User as UserModel
from app.common.models.icpdao.job import Job as JobModel, JobPR as JobPRModel, \
    JobStatusEnum, JobPRComment, JobPRStatusEnum
from app.common.utils import get_next_time
from app.controllers.sync_cycle_icppper_stat import sync_one_cycle_icppper_stat


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


def create_cycle_by_params(dao_id, begin_at):
    config = DAOJobConfig.objects(dao_id=dao_id).first()
    end_at = get_next_time(
        config.time_zone, int(time.time()),
        config.deadline_day, config.deadline_time)
    pair_begin_at = get_next_time(
        config.time_zone, end_at,
        config.pair_begin_day, config.pair_begin_hour)
    pair_end_at = get_next_time(
        config.time_zone, pair_begin_at,
        config.pair_end_day, config.pair_end_hour)
    vote_begin_at = get_next_time(
        config.time_zone, pair_end_at,
        config.voting_begin_day, config.voting_begin_hour)
    vote_end_at = get_next_time(
        config.time_zone, vote_begin_at,
        config.voting_end_day, config.voting_end_hour)

    cycle = Cycle(
        dao_id=dao_id,
        time_zone=config.time_zone,
        begin_at=begin_at, end_at=end_at,
        pair_begin_at=pair_begin_at, pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at, vote_end_at=vote_end_at)

    cycle.save()
    return cycle


def sync_cycle_icppper_stat_by_job_ids(job_ids):
    jobs = JobModel.objects(id__in=list(job_ids)).all()
    tmp = []
    for job in jobs:
        if job.cycle_id:
            value = [job.dao_id, job.cycle_id, job.user_id]
            if value not in tmp:
                tmp.append(value)

    for value in tmp:
        dao_id, cycle_id, user_id = value
        sync_one_cycle_icppper_stat(
            dao_id=dao_id,
            cycle_id=cycle_id,
            user_id=user_id
        )


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
                    link_cycle = None
                    merged_at = merged_at_list[-1]
                    newest_cycle = Cycle.objects(dao_id=job.dao_id).order_by("-begin_at").first()
                    if not newest_cycle:
                        begin_at = merged_at
                        link_cycle = create_cycle_by_params(job.dao_id, begin_at)
                    elif newest_cycle and newest_cycle.begin_at <= merged_at and merged_at < newest_cycle.end_at:
                        link_cycle = newest_cycle
                    elif newest_cycle and merged_at >= newest_cycle.end_at:
                        begin_at = newest_cycle.end_at
                        link_cycle = create_cycle_by_params(job.dao_id, begin_at)
                    else:
                        # 如果找不到 link_cycle 就不保存
                        print("job id:{} 找不到 link_cycle，所以不更新".format(job.id))
                        continue

                    job.cycle_id = str(link_cycle.id)
                job.save()
                need_update_comment_jobs.append(job)
        else:
            if not job.cycle_id:
                raise ValueError("NOT AWAITING MERGED JOB NOT CYCLE")
            cycle = Cycle.objects(id=job.cycle_id).first()
            create_at_list = sorted([i.create_at for i in tmp_prs])
            if (len(create_at_list) == 0 and int(time.time()) < cycle.end_at) or (
                len(create_at_list) > 0 and create_at_list[-1] < cycle.end_at and check_status != {JobPRStatusEnum.MERGED.value}):
                job.status = JobStatusEnum.AWAITING_MERGER.value
                job.update_at = int(time.time())
                job.cycle_id = None
                job.save()
                need_update_comment_jobs.append(job)
    for update_job in need_update_comment_jobs:
        update_issue_comment(app_client, update_job)
    sync_cycle_icppper_stat_by_job_ids(list(job_ids))


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


def sync_job_pr(app_client, job_pr, job_ids):
    print(f'job pr sync, job_ids: {job_ids}')

    job_ids = set(job_ids)

    sync_job_pr_comment(app_client, job_pr, job_ids)
    sync_job_issue_status_comment(app_client, job_ids)
