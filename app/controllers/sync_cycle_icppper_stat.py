import decimal

from app.common.models.icpdao.cycle import CycleIcpperStat
from app.common.models.icpdao.job import Job, JobStatusEnum


def create_or_update_cycle_icpper_stat(dao_id, cycle_id, user_id, job_count, job_size):
    update_result = CycleIcpperStat.objects(
        dao_id=dao_id, user_id=user_id, cycle_id=cycle_id
    ).update_one(full_result=True, upsert=True, job_size=job_size, size__=job_size, job_count=job_count)

    is_new = False
    is_dict = isinstance(update_result, dict)
    if is_dict and update_result.get('upserted_id'):
        is_new = True
    elif not is_dict and update_result.upserted_id:
        is_new = True

    if is_new:
        cis = CycleIcpperStat.objects(
            dao_id=dao_id, user_id=user_id, cycle_id=cycle_id
        ).first()

        last_item = CycleIcpperStat.objects(
            dao_id=cis.dao_id,
            user_id=cis.user_id,
            create_at__lt=cis.create_at
        ).order_by('-create_at').first()

        cis.income = decimal.Decimal('0')
        cis.vote_ei = decimal.Decimal('0')
        cis.owner_ei = decimal.Decimal('0')
        cis.ei = decimal.Decimal('0')
        cis.be_reviewer_has_warning_user_ids = []
        cis.create_at = int(cis.id.generation_time.timestamp())
        cis.update_at = int(cis.id.generation_time.timestamp())
        if last_item:
            cis.last_id = str(last_item.id)
        cis.save()


def sync_one_cycle_icppper_stat(dao_id, cycle_id, user_id):
    # TODO 补充 cycle_icpper_stat 变化的单元测试
    job_list = Job.objects(
        dao_id=dao_id,
        cycle_id=cycle_id,
        user_id=user_id,
        status__in=[
            JobStatusEnum.MERGED.value, JobStatusEnum.AWAITING_VOTING.value,
            JobStatusEnum.WAITING_FOR_TOKEN.value
        ]
    )
    job_list = [job for job in job_list]

    job_count = len(job_list)

    job_size = decimal.Decimal('0')
    for job in job_list:
        job_size += job.size

    create_or_update_cycle_icpper_stat(
        dao_id=dao_id,
        cycle_id=cycle_id,
        user_id=user_id,
        job_count=job_count,
        job_size=job_size
    )
