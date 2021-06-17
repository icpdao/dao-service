import decimal
import time

from app.common.models.icpdao.cycle import CycleVoteResultStatTask, CycleVoteResultStatTaskStatus, Cycle, CycleVote, \
    CycleVoteType, CycleIcpperStat
from app.common.models.icpdao.job import Job, JobStatusEnum, JobPR, JobPRStatusEnum
from app.common.models.icpdao.user import User
from app.controllers.sync_cycle_icppper_stat import sync_one_cycle_icppper_stat


EI_08 = decimal.Decimal('0.80')
EI_04 = decimal.Decimal('0.40')
SIZE_0 = decimal.Decimal('0')


def _process_warning_review_stat(cycle_icpper_stat):
    """
    cycle_icpper_stat 上次没有或者正常，本次低于 0.4，要警告相关 reviewer
    """
    dao_id = cycle_icpper_stat.dao_id
    cycle_id = cycle_icpper_stat.cycle_id
    user_id = cycle_icpper_stat.user_id

    job_list = Job.objects(
        dao_id=dao_id,
        cycle_id=cycle_id,
        user_id=user_id,
        status__nin=[JobStatusEnum.AWAITING_MERGER.value]
    )
    job_list = [item for item in job_list]
    job_id_list = [str(item.id) for item in job_list]
    job_pr_list = JobPR.objects(job_id__in=job_id_list, status=JobPRStatusEnum.MERGED.value)
    job_pr_list = [item for item in job_pr_list]
    reviewer_id_list = []
    merged_user_github_login_set = set()
    for job_pr in job_pr_list:
        merged_user_github_login_set.add(job_pr.merged_user_github_login)
    reviewer_list = User.objects(github_login__in=list(merged_user_github_login_set))
    for item in reviewer_list:
        reviewer_id_list.append(str(item.id))

    cycle_icpper_stat_list_query = CycleIcpperStat.objects(
        dao_id=dao_id, cycle_id=cycle_id,
        user_id__in=reviewer_id_list
    )
    for item in cycle_icpper_stat_list_query:
        if not item.has_warning_review_user_ids:
            item.has_warning_review_user_ids = []

        item.has_warning_review_user_ids.append(user_id)
        item.update_at = int(time.time())
        item.save()


def _process_04_reviewer_size(cycle_icpper_stat):
    """
    cycle_icpper_stat 连续两次低于0.4 需要处理相关 reviewer
    """
    dao_id = cycle_icpper_stat.dao_id
    cycle_id = cycle_icpper_stat.cycle_id
    user_id = cycle_icpper_stat.user_id

    job_list = Job.objects(
        dao_id=dao_id,
        cycle_id=cycle_id,
        user_id=user_id,
        status__nin=[JobStatusEnum.AWAITING_MERGER.value]
    )
    job_list = [item for item in job_list]
    job_id_list = [str(item.id) for item in job_list]
    job_id_2_size = {}
    for job in job_list:
        job_id_2_size[str(job.id)] = job.size

    job_pr_list = JobPR.objects(job_id__in=job_id_list, status=JobPRStatusEnum.MERGED.value)
    job_pr_list = [item for item in job_pr_list]
    github_login_2_user_id = {}
    merged_user_github_login_set = set()
    for job_pr in job_pr_list:
        merged_user_github_login_set.add(job_pr.merged_user_github_login)
    reviewer_list = User.objects(github_login__in=list(merged_user_github_login_set))
    for user in reviewer_list:
        github_login_2_user_id[user.github_login] = str(user.id)

    reviewer_id_2_merge_size = {}
    for job_pr in job_pr_list:
        reviewer_id = github_login_2_user_id.get(job_pr.merged_user_github_login, None)
        if not reviewer_id:
            continue

        size = job_id_2_size[str(job_pr.job_id)]
        reviewer_id_2_merge_size.setdefault(reviewer_id, SIZE_0)
        reviewer_id_2_merge_size[reviewer_id] += size

    cycle_icpper_stat_list_query = CycleIcpperStat.objects(
        dao_id=dao_id, cycle_id=cycle_id,
        user_id__in=list(reviewer_id_2_merge_size.keys())
    )
    for item in cycle_icpper_stat_list_query:
        if not item.has_deducted_review_size:
            item.has_deducted_review_size = SIZE_0
        deducted_review_size = round(reviewer_id_2_merge_size[str(item.user_id)]/2, 2)
        item.has_deducted_review_size += deducted_review_size

        size = item.job_size
        if item.un_voted_all_vote or item.have_two_times_lt_08 or item.have_two_times_lt_04:
            size = round(size/2, 2)
        item.size = size - item.has_deducted_review_size

        item.update_at = int(time.time())
        item.save()


def stat_cycle_icpper_stat_size(dao_id, cycle_id):
    """
    根据 ei 情况，统计 size 数据
    """
    cycle_icpper_stat_list_query = CycleIcpperStat.objects(dao_id=dao_id, cycle_id=cycle_id)

    for item in cycle_icpper_stat_list_query:
        item.size = item.job_size
        if item.un_voted_all_vote:
            # 没有投完，直接减半
            item.size = round(item.job_size/2, 2)
        item.update_at = int(time.time())
        item.save()

    # 找到小于0.8的 icpper 数据
    # 找到小于0.8的 icpper 的上一次贡献数据
    cycle_icpper_stat_list_lt_08 = []
    last_info__id_2_ei = {}
    need_query_last_cycle_icpper_stat_id_list = []
    for item in cycle_icpper_stat_list_query:
        if item.ei < EI_08:
            cycle_icpper_stat_list_lt_08.append(item)
            if item.last_id:
                need_query_last_cycle_icpper_stat_id_list.append(item.last_id)
    for item in CycleIcpperStat.objects(id__in=need_query_last_cycle_icpper_stat_id_list):
        last_info__id_2_ei[str(item.id)] = item.ei

    # 处理 has_warning_review_user_ids
    for item in cycle_icpper_stat_list_lt_08:
        ei = item.ei
        if ei >= EI_04:
            continue

        if not item.last_id or last_info__id_2_ei[item.last_id] >= EI_08:
            _process_warning_review_stat(item)

    # 处理 size
    for item in cycle_icpper_stat_list_lt_08:
        # 没有上一周期
        if not item.last_id:
            continue

        last_ei = last_info__id_2_ei[item.last_id]
        ei = item.ei
        # 不是都小于0.8
        if last_ei >= EI_08:
            continue

        # 不是都小于04，但是都小于0.8
        if last_ei >= EI_04 or ei >= EI_04:
            item.size = round(item.job_size/2, 2)
            item.have_two_times_lt_08 = True
            item.update_at = int(time.time())
            item.save()
            continue

        # 都小于 04
        item.size = round(item.job_size/2, 2)
        item.have_two_times_lt_04 = True
        item.update_at = int(time.time())
        item.save()
        _process_04_reviewer_size(item)


def run_vote_result_stat_task(task_id):
    # TODO 增加单元测试
    print("run_vote_result_stat_task begin")
    print(task_id)
    task = CycleVoteResultStatTask.objects(id=task_id).first()
    if not task:
        print("task not fount")
        return

    if task.status != CycleVoteResultStatTaskStatus.INIT.value:
        print("task do not Repeat run")
        return

    cycle = Cycle.objects(id=task.cycle_id).first()

    if not cycle:
        print("cycle not found")
        return
    if time.time() <= cycle.vote_end_at:
        print("current time <= cycle vote_end_at")
        return

    task.status = CycleVoteResultStatTaskStatus.STATING.value
    task.update_at = time.time()
    task.save()

    dao_id = cycle.dao_id

    try:
        # 找到所有 icpper
        all_user_id_set = set()
        job_list_query = Job.objects(
            dao_id=dao_id,
            cycle_id=str(cycle.id),
            status__nin=[JobStatusEnum.AWAITING_MERGER.value]
        )
        for job in job_list_query:
            all_user_id_set.add(job.user_id)

        # 同步一下所有 cycle icpper stat
        for user_id in list(all_user_id_set):
            sync_one_cycle_icppper_stat(
                dao_id=dao_id,
                cycle_id=str(cycle.id),
                user_id=user_id
            )

        # 查询所有投票
        cycle_vote_list_query = CycleVote.objects(dao_id=dao_id, cycle_id=str(cycle.id))
        cycle_vote_list = [item for item in cycle_vote_list_query]
        # 找到谁没有投完票
        un_voted_all_vote_user_id_set = set()
        for cycle_vote in cycle_vote_list:
            if cycle_vote.vote_type == CycleVoteType.PAIR.value:
                if not cycle_vote.vote_job_id:
                    un_voted_all_vote_user_id_set.add(cycle_vote.voter_id)
                    continue
            if cycle_vote.vote_type == CycleVoteType.ALL.value:
                tmp_user_id_set = set()
                for item in cycle_vote.vote_result_type_all:
                    tmp_user_id_set.add(item.voter_id)
                tmp_set = all_user_id_set - tmp_user_id_set
                for user_id in list(tmp_set):
                    un_voted_all_vote_user_id_set.add(user_id)

        # 找到所有获的投票的 job
        vote_job_id_list = []
        for cycle_vote in cycle_vote_list:
            if cycle_vote.vote_type == CycleVoteType.PAIR.value:
                if cycle_vote.vote_job_id:
                    vote_job_id_list.append(cycle_vote.vote_job_id)
                    continue
            if cycle_vote.vote_type == CycleVoteType.ALL.value:
                if cycle_vote.vote_result_stat_type_all >= 50:
                    vote_job_id_list.append(cycle_vote.left_job_id)
                    continue

        # 统计 vote size
        userid_2_vote_size = {}
        vote_job_list_query = Job.objects(id__in=vote_job_id_list)
        vote_job_list = [item for item in vote_job_list_query]
        for job in vote_job_list:
            userid_2_vote_size.setdefault(job.user_id, decimal.Decimal('0'))
            userid_2_vote_size[job.user_id] += job.size

        # 统计 ei
        cycle_icpper_stat_list_query = CycleIcpperStat.objects(dao_id=dao_id, cycle_id=str(cycle.id))
        cycle_icpper_stat_list = [cycle_icpper_stat for cycle_icpper_stat in cycle_icpper_stat_list_query]
        for cycle_icpper_stat in cycle_icpper_stat_list:
            userid_2_vote_size.setdefault(cycle_icpper_stat.user_id, decimal.Decimal('0'))
            vote_size = userid_2_vote_size[cycle_icpper_stat.user_id]
            job_size = cycle_icpper_stat.job_size
            un_voted_all_vote = cycle_icpper_stat.user_id in un_voted_all_vote_user_id_set

            # vote ei
            vote_ei = round(vote_size/job_size, 2)

            cycle_icpper_stat.vote_ei = vote_ei
            cycle_icpper_stat.owner_ei = decimal.Decimal('0')
            cycle_icpper_stat.ei = vote_ei
            cycle_icpper_stat.un_voted_all_vote = un_voted_all_vote
            cycle_icpper_stat.update_at = time.time()
            cycle_icpper_stat.save()

        # 统计 size
        stat_cycle_icpper_stat_size(
            dao_id=dao_id,
            cycle_id=str(cycle.id)
        )

        cycle.vote_result_stat_at = int(time.time())
        cycle.update_at = int(time.time())
        cycle.save()

        task.status = CycleVoteResultStatTaskStatus.SUCCESS.value
        task.update_at = time.time()
        task.save()
    except:
        task.status = CycleVoteResultStatTaskStatus.FAIL.value
        task.update_at = time.time()
        task.save()
