import decimal
import time

from app.common.models.icpdao.cycle import CycleVoteResultStatTask, CycleVoteResultStatTaskStatus, Cycle, CycleVote, \
    CycleVoteType, CycleIcpperStat
from app.common.models.icpdao.job import Job


def _stat_cycle_icpper_stat_size(cycle_icpper_stat_list):
    # TODO 公布 Ei 时，需要计算 ei 0.8 0.4 问题
    # TODO EI 和 SIZE 计算方法有多个地方需要确认
    pass


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
        cycle_icpper_stat_list_query = CycleIcpperStat.objects(dao_id=dao_id, cycle_id=str(cycle.id))
        cycle_icpper_stat_list = [cycle_icpper_stat for cycle_icpper_stat in cycle_icpper_stat_list_query]
        for cycle_icpper_stat in cycle_icpper_stat_list:
            all_user_id_set.add(cycle_icpper_stat.user_id)

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
        vote_job_list_query = Job.objects(id__in=vote_job_id_list)
        vote_job_list = [item for item in vote_job_list_query]

        # 统计 vote size
        userid_2_vote_size = {}
        for job in vote_job_list:
            userid_2_vote_size.setdefault(job.user_id, decimal.Decimal('0'))
            userid_2_vote_size[job.user_id] += job.size

        # 统计 ei
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
        cycle_icpper_stat_list = [cycle_icpper_stat for cycle_icpper_stat in cycle_icpper_stat_list_query]
        _stat_cycle_icpper_stat_size(cycle_icpper_stat_list)

        task.status = CycleVoteResultStatTaskStatus.SUCCESS.value
        task.update_at = time.time()
        task.save()
    except:
        task.status = CycleVoteResultStatTaskStatus.FAIL.value
        task.update_at = time.time()
        task.save()
