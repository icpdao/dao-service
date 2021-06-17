import time

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.job import Job, JobStatusEnum
from app.controllers.vote_result_stat import stat_cycle_icpper_stat_size


def run_vote_result_publish_task(cycle_id):
    # TODO 单元测试
    cycle = Cycle.objects(id=cycle_id).first()
    dao_id = cycle.dao_id

    for item in CycleIcpperStat.objects(cycle_id=str(cycle.id)):
        item.ei = item.vote_ei + item.owner_ei
        item.save()

    stat_cycle_icpper_stat_size(
        dao_id=dao_id,
        cycle_id=str(cycle.id)
    )

    for item in Job.objects(dao_id=dao_id, cycle_id=str(cycle.id)):
        item.status = JobStatusEnum.WAITING_FOR_TOKEN.value
        item.save()

    cycle.vote_result_published_at = int(time.time())
    cycle.update_at = int(time.time())
    cycle.save()
