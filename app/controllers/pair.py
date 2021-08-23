import time
from mongoengine import Q

from app.common.models.icpdao.cycle import CycleVotePairTask, CycleVotePairTaskStatus, Cycle, CycleVote, CycleVoteType, \
    CycleVoteConfirm, CycleVoteConfirmStatus
from app.common.models.icpdao.job import JobPairTypeEnum, Job, JobStatusEnum, JobPR, JobPRStatusEnum
from app.common.models.icpdao.user import User
from app.ei.logic.ei_processor import EiProcessor
from app.ei.models.ei_issue import EiIssue
from app.ei.models.ei_user import EiUser


def filter_job_lables(job):
    res = []
    for label in job.labels:
        if label.startswith("ICP_"):
            res.append(label)
    return res


def get_data_by_cycle(cycle):
    # 找到所有 job
    job_list = list(Job.objects(cycle_id=str(cycle.id), status__in=[
        JobStatusEnum.MERGED.value, JobStatusEnum.AWAITING_VOTING.value]))
    job_id_list = [str(job.id) for job in job_list]
    # 找到所有 job pr
    job_pr_list = list(JobPR.objects(job_id__in=job_id_list, status=JobPRStatusEnum.MERGED.value))

    jobid_2_job_pr_list = {}
    for job_pr in job_pr_list:
        jobid_2_job_pr_list.setdefault(job_pr.job_id, [])
        jobid_2_job_pr_list[job_pr.job_id].append(job_pr)
    # 找到 jobid to pr
    jobid_2_job_pr = {}
    for jobid in jobid_2_job_pr_list:
        job_pr_list = jobid_2_job_pr_list[jobid]
        job_pr_list = sorted(job_pr_list, key=lambda job_pr: job_pr.merged_at, reverse=True)
        jobid_2_job_pr[jobid] = job_pr_list[0]

    # 找到所有用户
    user_ids = set()
    github_user_id_list = set()
    for job in job_list:
        user_ids.add(job.user_id)
    for job_pr in job_pr_list:
        user_ids.add(job_pr.user_id)
        github_user_id_list.add(job_pr.merged_user_github_user_id)

    userid_2_user = {}
    for user in User.objects(
            Q(id__in=list(user_ids)) | Q(github_user_id__in=list(github_user_id_list))):
        userid_2_user[str(user.id)] = user

    type_all_jobs = []
    type_pair_jobs = []
    for job in job_list:
        if job.pair_type == JobPairTypeEnum.PAIR.value:
            type_pair_jobs.append(job)
        if job.pair_type == JobPairTypeEnum.ALL.value:
            type_all_jobs.append(job)

    ei_issue_list = []
    for job in type_pair_jobs:
        job_pr = jobid_2_job_pr[str(job.id)]

        user_id = job.user_id
        user = userid_2_user[user_id]

        # TODO LABLES
        contributer = EiUser(
            id=str(user.id),
            name=str(user.id),
            labels=[],
        )

        # TODO LABLES
        reviewer = EiUser(
            id=job_pr.merged_user_github_user_id,
            name=job_pr.merged_user_github_user_id,
            labels=[],
        )

        # TODO labes
        ei_issue = EiIssue(
            id=str(job.id),
            _type='issue',
            org=job.github_repo_owner,
            repo=job.github_repo_name,
            number=job.github_issue_number,
            title=job.title,
            contributer=contributer,
            labels=filter_job_lables(job),
            size=str(job.size),
            reviewer=reviewer,
            pr_org=job_pr.github_repo_owner,
            pr_repo=job_pr.github_repo_name
        )
        ei_issue_list.append(ei_issue)

    return ei_issue_list, type_all_jobs, type_pair_jobs, user_ids


def run_pair_task(task_id):
    # TODO PAIR
    print("run_pair_task begin")
    print(task_id)
    task = CycleVotePairTask.objects(id=task_id).first()
    if not task:
        print("task not fount")
        return

    if task.status != CycleVotePairTaskStatus.INIT.value:
        print("task do not Repeat run")
        return

    cycle = Cycle.objects(id=task.cycle_id).first()

    if not cycle:
        print("cycle not found")
        return
    if time.time() >= cycle.pair_end_at or time.time() <= cycle.pair_begin_at:
        print("current time not in range cycle pair_begin_at pair_end_at")
        return

    dao_id = cycle.dao_id

    task.status = CycleVotePairTaskStatus.PAIRING.value
    task.update_at = int(time.time())
    task.save()

    try:
        ei_issue_list, type_all_jobs, type_pair_jobs, user_ids = get_data_by_cycle(cycle)
        ep = EiProcessor('first', ei_issue_list)
        ep.process()
        success = ep.pair_success()
        if not success:
            raise ValueError("FAIL")

        # 生成 vote
        vote_list = []
        ei_issue_pair_list = ep.assignees_info["pair_voter_info"]["ei_issue_pair_list"]
        for ei_issue_pair in ei_issue_pair_list:
            left_job_id = ei_issue_pair["left"]["id"]
            right_job_id = ei_issue_pair["right"]["id"]
            voter_id = ei_issue_pair["user"]["id"]

            vote_list.append(CycleVote(
                dao_id=dao_id,
                cycle_id=str(cycle.id),
                left_job_id=left_job_id,
                right_job_id=right_job_id,
                vote_type=CycleVoteType.PAIR.value,
                voter_id=voter_id,
                is_result_public=False
            ))

        # 找到所有 all job 生成 vote
        for job in type_all_jobs:
            vote_list.append(CycleVote(
                dao_id=dao_id,
                cycle_id=str(cycle.id),
                left_job_id=str(job.id),
                right_job_id=str(job.id),
                vote_type=CycleVoteType.ALL.value,
                is_result_public=True
            ))

        # 没有问题，清空现在 vote, 生成所有 vote
        CycleVote.objects(cycle_id=str(cycle.id), dao_id=dao_id).delete()
        for vote in vote_list:
            vote.save()
        # generate voter confirm data
        for uid in user_ids:
            CycleVoteConfirm.objects(
                dao_id=dao_id, cycle_id=str(cycle.id), voter_id=uid
            ).update(
                upsert=True, create_at=int(time.time()), status=CycleVoteConfirmStatus.WAITING.value)

        # 所有 job 更改状态
        for job in type_all_jobs:
            job.status = JobStatusEnum.AWAITING_VOTING.value
            job.update_at = int(time.time())
            job.save()
        for job in type_pair_jobs:
            job.status = JobStatusEnum.AWAITING_VOTING.value
            job.update_at = int(time.time())
            job.save()

        cycle.paired_at = int(time.time())
        cycle.update_at = int(time.time())
        cycle.save()

        task.status = CycleVotePairTaskStatus.SUCCESS.value
        task.update_at = int(time.time())
        task.save()

    except Exception as ex:
        import traceback
        msg = traceback.format_exc()
        print('exception log_exception' + str(ex))
        print(msg)
        # 出现任何错误回滚
        task.status = CycleVotePairTaskStatus.FAIL.value
        task.update_at = int(time.time())
        task.save()

    print("run_pair_task end")
