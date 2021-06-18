import time

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat, CycleVoteResultPublishTask, \
    CycleVoteResultPublishTaskStatus
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.controllers.vote_result_stat import stat_cycle_icpper_stat_size


def run_vote_result_publish_task(task_id):
    # TODO 增加单元测试
    print("run_vote_result_publish_task begin")
    print(task_id)
    task = CycleVoteResultPublishTask.objects(id=task_id).first()
    if not task:
        print("task not fount")
        return

    if task.status != CycleVoteResultPublishTaskStatus.INIT.value:
        print("task do not Repeat run")
        return

    cycle = Cycle.objects(id=task.cycle_id).first()

    if not cycle:
        print("cycle not found")
        return
    if time.time() <= cycle.vote_end_at:
        print("current time <= cycle vote_end_at")
        return
    if not cycle.vote_result_stat_at:
        print("not cycle.vote_result_stat_at")
        return

    cycle = Cycle.objects(id=str(cycle.id)).first()
    dao_id = cycle.dao_id

    task.status = CycleVoteResultPublishTaskStatus.RUNNING.value
    task.update_at = time.time()
    task.save()

    try:
        for item in CycleIcpperStat.objects(cycle_id=str(cycle.id)):
            item.ei = item.vote_ei + item.owner_ei
            item.save()

        stat_cycle_icpper_stat_size(
            dao_id=dao_id,
            cycle_id=str(cycle.id)
        )

        for item in Job.objects(dao_id=dao_id, cycle_id=str(cycle.id), status__nin=[JobStatusEnum.AWAITING_MERGER.value]):
            item.status = JobStatusEnum.WAITING_FOR_TOKEN.value
            item.save()

        cycle.vote_result_published_at = time.time()
        cycle.update_at = time.time()
        cycle.save()

        task.status = CycleVoteResultPublishTaskStatus.SUCCESS.value
        task.update_at = time.time()
        task.save()
    except:
        task.status = CycleVoteResultPublishTaskStatus.FAIL.value
        task.update_at = time.time()
        task.save()
    print("run_vote_result_publish_task end")
