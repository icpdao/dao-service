import decimal
from datetime import datetime, timezone, timedelta
import time

from app.common.models.icpdao.cycle import CycleVotePairTask, CycleVote, CycleIcpperStat, Cycle, CycleVoteType, \
    VoteResultTypeAll, VoteResultTypeAllResultType, CycleVotePairTaskStatus
from app.common.models.icpdao.dao import DAO, DAOJobConfig, DAOFollow
from app.common.models.icpdao.job import Job, JobPR, JobPRComment, JobStatusEnum, JobPairTypeEnum, JobPRStatusEnum
from app.common.models.icpdao.user import User


class DeleteDaoMock:
    def __init__(self, dao):
        self.dao = dao

    def delete_job(self):
        job_list = Job.objects(dao_id=str(self.dao.id))
        for job in job_list:
            job_pr_list = JobPR.objects(job_id=str(job.id))
            for job_pr in job_pr_list:
                JobPRComment.objects(
                    github_repo_id=job_pr.github_repo_id,
                    github_pr_number=job_pr.github_pr_number
                ).delete()
            job_pr_list.delete()
        job_list.delete()

    def delete_cycle(self):
        Cycle.objects(dao_id=str(self.dao.id)).delete()

    def delete_cycle_icpper_stat(self):
        CycleIcpperStat.objects(dao_id=str(self.dao.id)).delete()

    def delete_cycle_vote(self):
        CycleVote.objects(dao_id=str(self.dao.id)).delete()

    def delete_cycle_vote_pair_task(self):
        CycleVotePairTask.objects(dao_id=str(self.dao.id)).delete()

    def delete_dao_config(self):
        DAOJobConfig.objects(dao_id=str(self.dao.id)).delete()

    def delete_dao_follow(self):
        DAOFollow.objects(dao_id=str(self.dao.id)).delete()

    def delete_dao(self):
        DAO.objects(id=str(self.dao.id)).delete()

    def delete(self):
        self.delete_job()
        self.delete_cycle()
        self.delete_cycle_icpper_stat()
        self.delete_cycle_vote()
        self.delete_cycle_vote_pair_task()
        self.delete_dao_follow()
        self.delete_dao_config()
        self.delete_dao()


def create_one_end_cycle_data(owner_user, icpper_user, dao_name):
    # DAO
    dao = DAO(
        name=dao_name,
        logo='https://s3.amazonaws.com/dev.files.icpdao/avatar/rc-upload-1623139230084-2',
        desc='{}_{}_{}'.format(dao_name, dao_name, dao_name),
        owner_id=str(owner_user.id)
    )
    dao.save()

    # DAOJobConfig
    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    deadline_day_datetime = current_datetime - timedelta(days=15)
    deadline_day_datetime = datetime(
        year=deadline_day_datetime.year,
        month=deadline_day_datetime.month,
        day=deadline_day_datetime.day,
        tzinfo=deadline_day_datetime.tzinfo
    )
    if deadline_day_datetime.day >= 25:
        deadline_day_datetime = deadline_day_datetime + timedelta(days=7)

    pair_begin_day_datetime = deadline_day_datetime + timedelta(days=1)
    pair_end_day_datetime = deadline_day_datetime + timedelta(days=3)
    voting_begin_day = deadline_day_datetime + timedelta(days=3)
    voting_end_day = deadline_day_datetime + timedelta(days=4)
    dao_job_config = DAOJobConfig(
        dao_id=str(dao.id),
        deadline_day=deadline_day_datetime.day,
        deadline_time=0,
        pair_begin_day=pair_begin_day_datetime.day,
        pair_begin_hour=12,
        pair_end_day=pair_end_day_datetime.day,
        pair_end_hour=0,
        voting_begin_day=voting_begin_day.day,
        voting_begin_hour=0,
        voting_end_day=voting_end_day.day,
        voting_end_hour=12
    )
    dao_job_config.save()

    # Cycle
    dao_end_cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=deadline_day_datetime.timestamp() - 30 * 24 * 60 * 60,
        end_at=deadline_day_datetime.timestamp(),
        pair_begin_at=deadline_day_datetime.timestamp() + 12 * 60 * 60,
        pair_end_at=deadline_day_datetime.timestamp() + 36 * 60 * 60,
        vote_begin_at=deadline_day_datetime.timestamp() + 36 * 60 * 60,
        vote_end_at=deadline_day_datetime.timestamp() + 72 * 60 * 60,
        paired_at=deadline_day_datetime.timestamp() + 36 * 60 * 60,
        vote_result_stat_at=deadline_day_datetime.timestamp() + 72 * 60 * 60,
        vote_result_published_at=deadline_day_datetime.timestamp() + 75 * 60 * 60
    )
    dao_end_cycle.save()

    # Job
    # JobPR
    job1 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:1".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    job2 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:2".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('2.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        income=200,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    job3 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:3".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    job4 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:4".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('4.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        income=400,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        left_job_id=str(job1.id),
        right_job_id=str(job3.id),
        vote_type=CycleVoteType.PAIR.value,
        vote_job_id=str(job1.id),
        voter_id=str(icpper_user.id)
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        left_job_id=str(job3.id),
        right_job_id=str(job1.id),
        vote_type=CycleVoteType.PAIR.value,
        vote_job_id=str(job3.id),
        voter_id=str(owner_user.id)
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        left_job_id=str(job4.id),
        right_job_id=str(job4.id),
        vote_type=CycleVoteType.ALL.value,
        vote_result_stat_type_all=100,
        vote_result_type_all=[
            VoteResultTypeAll(
                voter_id=str(owner_user.id),
                result=VoteResultTypeAllResultType.YES.value
            ),
            VoteResultTypeAll(
                voter_id=str(icpper_user.id),
                result=VoteResultTypeAllResultType.YES.value
            )
        ],
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        left_job_id=str(job2.id),
        right_job_id=str(job2.id),
        vote_type=CycleVoteType.ALL.value,
        vote_result_stat_type_all=100,
        vote_result_type_all=[
            VoteResultTypeAll(
                voter_id=str(owner_user.id),
                result=VoteResultTypeAllResultType.YES.value
            ),
            VoteResultTypeAll(
                voter_id=str(icpper_user.id),
                result=VoteResultTypeAllResultType.YES.value
            )
        ],
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        income=300,
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.0'),
        ei=decimal.Decimal('1.0')
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        income=500,
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.1'),
        ei=decimal.Decimal('1.1')
    ).save()
    # CycleVotePairTask
    CycleVotePairTask(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        status=CycleVotePairTaskStatus.SUCCESS.value
    ).save()


def create_not_pair_cycle_data(owner_user, icpper_user, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    end_at = current_datetime.timestamp()
    pair_begin_at = end_at + 24 * 60 * 60
    pair_end_at = pair_begin_at + 24 * 60 * 60
    vote_begin_at = pair_end_at
    vote_end_at = vote_begin_at + 36 * 60 * 60

    # Cycle
    cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=prev_cycle.end_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at
    )
    cycle.save()

    # Job
    # JobPR
    job1 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:1".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job2 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:2".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('2.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=200,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job3 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:3".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job4 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:4".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('4.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=400,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0')
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
    ).save()


def create_end_and_in_pair_time_cycle_data(owner_user, icpper_user, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    end_at = current_datetime.timestamp()
    pair_begin_at = end_at
    pair_end_at = pair_begin_at + 24 * 60 * 60
    vote_begin_at = pair_end_at
    vote_end_at = vote_begin_at + 36 * 60 * 60

    # Cycle
    cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=prev_cycle.end_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at
    )
    cycle.save()

    # Job
    # JobPR
    job1 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:1".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job2 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:2".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('2.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=200,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=owner_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job3 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:3".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=100,
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job4 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:4".format(dao.name, "not_pair_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('4.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        income=400,
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_id=1,
        github_pr_number=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_login=icpper_user.github_login,
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0')
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
    ).save()


def create_ing_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'icpdao-test-icp')


def create_end_and_not_pair_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end-and-not-pair')
    create_not_pair_cycle_data(owner_user, icpper_user, 'end-and-not-pair')


def create_end_and_in_pair_time_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end_and_in_pair_time')
    create_end_and_in_pair_time_cycle_data(owner_user, icpper_user, 'end_and_in_pair_time')


def init_mock_data(owner_github_user_login, icpper_github_user_login):
    dao_name_list = [
        "icpdao-test-icp"
    ]

    for dao_name in dao_name_list:
        dao = DAO.objects(name=dao_name).first()
        if dao:
            DeleteDaoMock(dao).delete()

    owner_user = User.objects(github_login=owner_github_user_login).first()
    icpper_user = User.objects(github_login=icpper_github_user_login).first()

    create_ing_cycle_dao(owner_user, icpper_user)
    create_end_and_not_pair_cycle_dao(owner_user, icpper_user)
    create_end_and_in_pair_time_cycle_dao(owner_user, icpper_user)
