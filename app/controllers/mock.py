import decimal
from datetime import datetime, timezone, timedelta
import time
import random
import web3

import settings
from app.common.models.icpdao.base import TokenIncome
from app.common.models.icpdao.cycle import CycleVotePairTask, CycleVote, CycleIcpperStat, Cycle, CycleVoteType, \
    VoteResultTypeAll, VoteResultTypeAllResultType, CycleVotePairTaskStatus, CycleVoteConfirm, CycleVoteConfirmStatus
from app.common.models.icpdao.dao import DAO, DAOJobConfig, DAOFollow, DAOToken
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus, MentorRelationStat, \
    MentorRelationStatTokenStat, MentorLevel7IcpperCountStat
from app.common.models.icpdao.job import Job, JobPR, JobPRComment, JobStatusEnum, JobPairTypeEnum, JobPRStatusEnum
from app.common.models.icpdao.token import MentorTokenIncomeStat
from app.common.models.icpdao.user import User, UserStatus


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


def _get_dao_mock_token(dao, income):
    dt = DAOToken.objects(
        dao_id=str(dao.id),
        token_chain_id=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID
    ).first()
    return TokenIncome(token_chain_id=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID, token_address=dt.token_address, token_symbol="DM", income=income)


def _get_dao_other_mock(dao, income):
    return TokenIncome(token_chain_id=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID, token_address=web3.Account.create().address, token_symbol="DMN", income=income)


def _get_random_existed_token(income: decimal.Decimal):
    ad = random.choice([
        ['0x1f9840a85d5af5bf1d1762f925bdaddc4201f984', 'UNI'],
        ['0x6f40d4a6237c257fff2db00fa0510deeecd303eb', 'INST'],
        ['0x35bd01fc9d6d5d81ca9e055db88dc49aa2c699a8', 'FWB']
    ])
    return TokenIncome(token_chain_id=settings.ICPDAO_MINT_TOKEN_ETH_CHAIN_ID, token_address=ad[0], token_symbol=ad[1], income=income)


def _get_mock_token_income(dao, incomes):
    return [
        _get_dao_mock_token(dao, incomes[0]),
        _get_dao_other_mock(dao, incomes[1]),
        _get_random_existed_token(incomes[2])
    ]


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

    def delete_cycle_vote_confirm(self):
        CycleVoteConfirm.objects(dao_id=str(self.dao.id)).delete()

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
        self.delete_cycle_vote_confirm()
        self.delete_dao_follow()
        self.delete_dao_config()
        self.delete_dao()


def create_one_end_cycle_data(owner_user, icpper_user, dao_name):
    if dao_name == 'icpdao-test-icp':
        github_owner_id = 85466462
    else:
        github_owner_id = _get_github_user_id(dao_name)
    # DAO
    dao = DAO(
        name=dao_name,
        logo='https://s3.amazonaws.com/dev.files.icpdao/avatar/rc-upload-1623139230084-2',
        desc='{}_{}_{}'.format(dao_name, dao_name, dao_name),
        owner_id=str(owner_user.id),
        github_owner_id=github_owner_id,
        github_owner_name=dao_name
    )
    dao.save()
    DAOToken(
        dao_id=str(dao.id),
        token_chain_id="3",
        token_address=web3.Account.create().address,
        token_name=dao_name,
        token_symbol=dao_name
    ).save()

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
        pair_begin_at=deadline_day_datetime.timestamp(),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(icpper_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(owner_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
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
        job_size=decimal.Decimal('3.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
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
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
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
    """
    ????????????????????????
    """
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
    ).save()


def create_in_pair_time_cycle_data(owner_user, icpper_user, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    end_at = current_datetime.timestamp() - 1 * 60 * 60
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
    ).save()


def _create_job(dao, cycle, user, repo_name, repo_id, start_number, pair_type):
    job = Job(
        dao_id=str(dao.id),
        user_id=str(user.id),
        title="{}:{}:{}:{}".format(dao.name, "not_pair_cycle", user.github_login, start_number),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name=repo_name,
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=repo_id,
        github_issue_number=start_number * 2,
        bot_comment_database_id=start_number,
        status=JobStatusEnum.MERGED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=pair_type,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job.id),
        user_id=str(user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name=repo_name,
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=repo_id,
        github_pr_number=start_number * 2 + 1,
        github_pr_id=start_number * 2 + 1,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()
    return job


def create_in_vote_time_cycle_data(owner_user, icpper_user, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    pair_end_at = current_datetime.timestamp() - 1 * 60 * 60
    pair_begin_at = pair_end_at - 24 * 60 * 60
    end_at = pair_begin_at

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
        vote_end_at=vote_end_at,
        paired_at=pair_begin_at + 1
    )
    cycle.save()

    owner_user_all_job_list = []
    for index in range(0, 2):
        job = _create_job(dao, cycle, owner_user, "mock", 1, 1+index, JobPairTypeEnum.ALL.value)
        owner_user_all_job_list.append(job)
    icpper_user_all_job_list = []
    for index in range(0, 2):
        job = _create_job(dao, cycle, icpper_user, "mock", 1, 3+index, JobPairTypeEnum.ALL.value)
        icpper_user_all_job_list.append(job)
    owner_user_pair_job_list = []
    for index in range(0, 20):
        job = _create_job(dao, cycle, owner_user, "mock", 1, 5+index, JobPairTypeEnum.PAIR.value)
        owner_user_pair_job_list.append(job)
    icpper_user_pair_job_list = []
    for index in range(0, 20):
        job = _create_job(dao, cycle, icpper_user, "mock", 1, 25+index, JobPairTypeEnum.PAIR.value)
        icpper_user_pair_job_list.append(job)

    # Job
    # JobPR
    # job1 = Job(
    #     dao_id=str(dao.id),
    #     user_id=str(owner_user.id),
    #     title="{}:{}:{}:1".format(dao.name, "not_pair_cycle", owner_user.github_login),
    #     body_text="xxxxx",
    #     size=decimal.Decimal('1.0'),
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_issue_number=1,
    #     bot_comment_database_id=1,
    #     status=JobStatusEnum.MERGED.value,
    #     income=decimal.Decimal(100,
    #     pair_type=JobPairTypeEnum.PAIR.value,
    #     cycle_id=str(cycle.id),
    # ).save()
    # JobPR(
    #     job_id=str(job1.id),
    #     user_id=str(owner_user.id),
    #     title='pr merged',
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_pr_number=2,
    #     github_pr_id=2,
    #     status=JobPRStatusEnum.MERGED.value,
    #     merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
    #     merged_at=cycle.end_at - 12 * 60 * 60
    # ).save()
    #
    # job2 = Job(
    #     dao_id=str(dao.id),
    #     user_id=str(owner_user.id),
    #     title="{}:{}:{}:2".format(dao.name, "not_pair_cycle", owner_user.github_login),
    #     body_text="xxxxx",
    #     size=decimal.Decimal('2.0'),
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_issue_number=3,
    #     bot_comment_database_id=1,
    #     status=JobStatusEnum.MERGED.value,
    #     income=decimal.Decimal(200,
    #     pair_type=JobPairTypeEnum.ALL.value,
    #     cycle_id=str(cycle.id),
    # ).save()
    # JobPR(
    #     job_id=str(job2.id),
    #     user_id=str(owner_user.id),
    #     title='pr merged',
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_pr_number=4,
    #     github_pr_id=4,
    #     status=JobPRStatusEnum.MERGED.value,
    #     merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
    #     merged_at=cycle.end_at - 12 * 60 * 60
    # ).save()
    #
    # job3 = Job(
    #     dao_id=str(dao.id),
    #     user_id=str(icpper_user.id),
    #     title="{}:{}:{}:3".format(dao.name, "not_pair_cycle", owner_user.github_login),
    #     body_text="xxxxx",
    #     size=decimal.Decimal('1.0'),
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_issue_number=5,
    #     bot_comment_database_id=1,
    #     status=JobStatusEnum.MERGED.value,
    #     income=decimal.Decimal(100,
    #     pair_type=JobPairTypeEnum.PAIR.value,
    #     cycle_id=str(cycle.id),
    # ).save()
    # JobPR(
    #     job_id=str(job3.id),
    #     user_id=str(icpper_user.id),
    #     title='pr merged',
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_pr_number=6,
    #     github_pr_id=6,
    #     status=JobPRStatusEnum.MERGED.value,
    #     merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
    #     merged_at=cycle.end_at - 12 * 60 * 60
    # ).save()
    #
    # job4 = Job(
    #     dao_id=str(dao.id),
    #     user_id=str(icpper_user.id),
    #     title="{}:{}:{}:4".format(dao.name, "not_pair_cycle", owner_user.github_login),
    #     body_text="xxxxx",
    #     size=decimal.Decimal('4.0'),
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_issue_number=7,
    #     bot_comment_database_id=1,
    #     status=JobStatusEnum.MERGED.value,
    #     income=decimal.Decimal(400,
    #     pair_type=JobPairTypeEnum.ALL.value,
    #     cycle_id=str(cycle.id),
    # ).save()
    # JobPR(
    #     job_id=str(job4.id),
    #     user_id=str(icpper_user.id),
    #     title='pr merged',
    #     github_repo_owner=dao.name,
    #     github_repo_name='mock',
    #     github_repo_owner_id=_get_github_user_id(dao.name),
    #     github_repo_id=1,
    #     github_pr_number=8,
    #     github_pr_id=8,
    #     status=JobPRStatusEnum.MERGED.value,
    #     merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
    #     merged_at=cycle.end_at - 12 * 60 * 60
    # ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=22,
        size=decimal.Decimal('22.0'),
        job_size=decimal.Decimal('22.0'),
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=22,
        size=decimal.Decimal('22.0'),
        job_size=decimal.Decimal('22.0'),
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        voter_id=str(icpper_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        voter_id=str(owner_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    for index, job in enumerate(owner_user_pair_job_list):
        left_job = owner_user_pair_job_list[index]
        right_job = icpper_user_pair_job_list[index]
        CycleVote(
            dao_id=str(dao.id),
            cycle_id=str(cycle.id),
            left_job_id=str(left_job.id),
            right_job_id=str(right_job.id),
            vote_type=CycleVoteType.PAIR.value,
            voter_id=str(owner_user.id)
        ).save()

    for index, job in enumerate(owner_user_all_job_list):
        CycleVote(
            dao_id=str(dao.id),
            cycle_id=str(cycle.id),
            left_job_id=str(job.id),
            right_job_id=str(job.id),
            vote_type=CycleVoteType.ALL.value
        ).save()
    for index, job in enumerate(icpper_user_all_job_list):
        CycleVote(
            dao_id=str(dao.id),
            cycle_id=str(cycle.id),
            left_job_id=str(job.id),
            right_job_id=str(job.id),
            vote_type=CycleVoteType.ALL.value
        ).save()


def create_in_stat_time_cycle_data(owner_user, icpper_user, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    vote_end_at = current_datetime.timestamp() - 1 * 60 * 60
    vote_begin_at = vote_end_at - 12 * 60 * 60
    pair_end_at = vote_begin_at
    pair_begin_at = pair_end_at - 12 * 60 * 60
    end_at = pair_begin_at

    # Cycle
    cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=prev_cycle.end_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at,
        paired_at=pair_begin_at + 1
    )
    cycle.save()

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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job2 = Job(
        dao_id=str(dao.id),
        user_id=str(owner_user.id),
        title="{}:{}:{}:2".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('2.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job3 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:3".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('1.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    job4 = Job(
        dao_id=str(dao.id),
        user_id=str(icpper_user.id),
        title="{}:{}:{}:4".format(dao.name, "dao_end_cycle", owner_user.github_login),
        body_text="xxxxx",
        size=decimal.Decimal('4.0'),
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=cycle.end_at - 12 * 60 * 60
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        voter_id=str(icpper_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        voter_id=str(owner_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        left_job_id=str(job1.id),
        right_job_id=str(job3.id),
        vote_type=CycleVoteType.PAIR.value,
        vote_job_id=str(job1.id),
        voter_id=str(icpper_user.id)
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        left_job_id=str(job3.id),
        right_job_id=str(job1.id),
        vote_type=CycleVoteType.PAIR.value,
        vote_job_id=str(job3.id),
        voter_id=str(owner_user.id)
    ).save()
    CycleVote(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
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
        cycle_id=str(cycle.id),
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
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0')
    ).save()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0')
    ).save()
    # CycleVotePairTask
    CycleVotePairTask(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        status=CycleVotePairTaskStatus.SUCCESS.value
    ).save()


def create_tip_end_cycle_1_data(owner_user, icpper_user, mock_users, dao_name):
    # DAO
    dao = DAO(
        name=dao_name,
        logo='https://s3.amazonaws.com/dev.files.icpdao/avatar/rc-upload-1623139230084-2',
        desc='{}_{}_{}'.format(dao_name, dao_name, dao_name),
        owner_id=str(owner_user.id),
        github_owner_id=_get_github_user_id(dao_name),
        github_owner_name=dao_name
    )
    dao.save()
    DAOToken(
        dao_id=str(dao.id),
        token_chain_id="3",
        token_address=web3.Account.create().address,
        token_name=dao_name,
        token_symbol=dao_name
    ).save()

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
        pair_begin_at=deadline_day_datetime.timestamp(),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(icpper_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(owner_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
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
    # CycleVotePairTask
    CycleVotePairTask(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        status=CycleVotePairTaskStatus.SUCCESS.value
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
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
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.1'),
        ei=decimal.Decimal('1.1')
    ).save()

    for user in [mock_users[0],mock_users[1],mock_users[2],mock_users[5],mock_users[6]]:
        CycleIcpperStat(
            dao_id=str(dao.id),
            cycle_id=str(dao_end_cycle.id),
            user_id=str(user.id),
            job_count=2,
            size=decimal.Decimal('5.0'),
            job_size=decimal.Decimal('5.0'),
            un_voted_all_vote=False,
            incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
              vote_ei=decimal.Decimal('1.0'),
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(mock_users[3].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7')
    ).save()

    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(mock_users[4].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3')
    ).save()


def create_end_cycle_and_mint_1_data(owner_user, icpper_user, mock_users, dao_name):
    # icppership
    Icppership.objects(
        mentor_user_id=str(owner_user.id),
        icpper_user_id=str(icpper_user.id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=icpper_user.github_login,
    )
    Icppership.objects(
        mentor_user_id=str(owner_user.id),
        icpper_user_id=str(mock_users[0].id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=mock_users[0].github_login,
    )
    Icppership.objects(
        mentor_user_id=str(owner_user.id),
        icpper_user_id=str(mock_users[1].id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=mock_users[1].github_login,
    )
    Icppership.objects(
        mentor_user_id=str(mock_users[1].id),
        icpper_user_id=str(mock_users[2].id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=mock_users[2].github_login,
    )
    # DAO
    dao = DAO(
        name=dao_name,
        logo='https://s3.amazonaws.com/dev.files.icpdao/avatar/rc-upload-1623139230084-2',
        desc='{}_{}_{}'.format(dao_name, dao_name, dao_name),
        owner_id=str(owner_user.id),
        github_owner_id=_get_github_user_id(dao_name),
        github_owner_name=dao_name
    )
    dao.save()
    DAOToken(
        dao_id=str(dao.id),
        token_chain_id="3",
        token_address=web3.Account.create().address,
        token_name=dao_name,
        token_symbol=dao_name
    ).save()

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

    begin_at = deadline_day_datetime.timestamp() - 30 * 24 * 60 * 60
    end_at = begin_at + 16 * 24 * 60 * 60
    pair_begin_at = end_at
    pair_end_at = pair_begin_at + 36 * 60 * 60
    vote_begin_at = pair_end_at
    vote_end_at = vote_begin_at + 36 * 60 * 60
    paired_at = pair_begin_at + 1 * 60 * 60
    vote_result_stat_at = vote_end_at + 1 * 60 * 60
    vote_result_published_at = vote_result_stat_at + 1 * 60 * 60
    # Cycle
    dao_end_cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=begin_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at,
        paired_at=paired_at,
        vote_result_stat_at=vote_result_stat_at,
        vote_result_published_at=vote_result_published_at
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=1,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job1.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=2,
        github_pr_id=2,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=3,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(200), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job2.id),
        user_id=str(owner_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=4,
        github_pr_id=4,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(owner_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=5,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(100), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.PAIR.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job3.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=6,
        github_pr_id=6,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
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
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_issue_number=7,
        bot_comment_database_id=1,
        status=JobStatusEnum.TOKEN_RELEASED.value,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(400), decimal.Decimal(200), decimal.Decimal(200)]),
        pair_type=JobPairTypeEnum.ALL.value,
        cycle_id=str(dao_end_cycle.id),
    ).save()
    JobPR(
        job_id=str(job4.id),
        user_id=str(icpper_user.id),
        title='pr merged',
        github_repo_owner=dao.name,
        github_repo_name='mock',
        github_repo_owner_id=_get_github_user_id(dao.name),
        github_repo_id=1,
        github_pr_number=8,
        github_pr_id=8,
        status=JobPRStatusEnum.MERGED.value,
        merged_user_github_user_id=_get_github_user_id(icpper_user.github_login),
        merged_at=dao_end_cycle.end_at - 12 * 60 * 60
    ).save()

    """
    1 3 PAIR
    3 1 PAIR
    4 4 ALL
    2 2 ALL
    """
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(icpper_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
    CycleVoteConfirm(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        voter_id=str(owner_user.id),
        status=CycleVoteConfirmStatus.WAITING.value
    ).save()
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
    # CycleVotePairTask
    CycleVotePairTask(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        status=CycleVotePairTaskStatus.SUCCESS.value
    ).save()

    # CycleIcpperStat
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
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
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.1'),
        ei=decimal.Decimal('1.1')
    ).save()

    for user in [mock_users[0],mock_users[1],mock_users[2],mock_users[5],mock_users[6]]:
        CycleIcpperStat(
            dao_id=str(dao.id),
            cycle_id=str(dao_end_cycle.id),
            user_id=str(user.id),
            job_count=2,
            size=decimal.Decimal('5.0'),
            job_size=decimal.Decimal('5.0'),
            un_voted_all_vote=False,
            incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
              vote_ei=decimal.Decimal('1.0'),
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(mock_users[3].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7')
    ).save()

    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(dao_end_cycle.id),
        user_id=str(mock_users[4].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        un_voted_all_vote=False,
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3')
    ).save()

    #
    MentorRelationStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(icpper_user.id),
        relation=True,
        has_reward_icpper_count=1,
        token_stat=[MentorRelationStatTokenStat(token_chain_id="3", token_count=1001)],
    ).save()
    MentorTokenIncomeStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(icpper_user.id),
        dao_id=str(dao.id),
        token_chain_id='3',
        token_address='0'*24,
        token_name='test_token_1',
        token_symbol='ICPDT1',
        total_value=decimal.Decimal(888)
    ).save()
    MentorTokenIncomeStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(icpper_user.id),
        dao_id=str(dao.id),
        token_chain_id='3',
        token_address='0' * 24,
        token_name='test_token_2',
        token_symbol='ICPDT2',
        total_value=decimal.Decimal(999)
    ).save()
    MentorTokenIncomeStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(icpper_user.id),
        dao_id=str(dao.id),
        token_chain_id='3',
        token_address='0' * 24,
        token_name='test_token_3',
        token_symbol='ICPDT3',
        total_value=decimal.Decimal(1111)
    ).save()
    MentorRelationStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(mock_users[0].id),
        relation=True,
        has_reward_icpper_count=1
    ).save()
    MentorRelationStat(
        mentor_id=str(owner_user.id),
        icpper_id=str(mock_users[1].id),
        relation=True,
        has_reward_icpper_count=2
    ).save()
    MentorRelationStat(
        mentor_id=str(mock_users[1].id),
        icpper_id=str(mock_users[2].id),
        relation=True,
        has_reward_icpper_count=1
    ).save()
    MentorLevel7IcpperCountStat(
        mentor_id=str(owner_user.id),
        level_1_count=3,
        level_2_count=4,
        level_3_count=4,
        level_4_count=4,
        level_5_count=4,
        level_6_count=4,
        level_7_count=4
    ).save()
    MentorLevel7IcpperCountStat(
        mentor_id=str(mock_users[1].id),
        level_1_count=1,
        level_2_count=1,
        level_3_count=1,
        level_4_count=1,
        level_5_count=1,
        level_6_count=1,
        level_7_count=1
    ).save()


def create_end_cycle_and_mint_2_data(owner_user, icpper_user, mock_users, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    begin_at = prev_cycle.end_at
    end_at = begin_at + 13 * 24 * 60 * 60
    pair_begin_at = end_at
    pair_end_at = pair_begin_at + 1
    vote_begin_at = pair_end_at
    vote_end_at = vote_begin_at + 1
    paired_at = pair_begin_at + 1
    vote_result_stat_at = vote_end_at + 1
    vote_result_published_at = vote_result_stat_at + 1

    # Cycle
    cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=begin_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at,
        paired_at=paired_at,
        vote_result_stat_at=vote_result_stat_at,
        vote_result_published_at=vote_result_published_at
    )
    cycle.save()

    # CycleIcpperStat
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(owner_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.0'),
        ei=decimal.Decimal('1.0'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(icpper_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.3'),
        ei=decimal.Decimal('1.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[0].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[0].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[1].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[1].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[2].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[2].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_reviewer_has_warning_user_ids=[str(mock_users[1].id)]
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[3].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[3].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_08=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[4].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[4].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_04=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[5].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[5].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[6].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[6].id),
        job_count=2,
        size=decimal.Decimal('4.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_deducted_size_by_review=decimal.Decimal('1.0')
    ).save()


def create_end_cycle_and_mint_3_data(owner_user, icpper_user, mock_users, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    begin_at = prev_cycle.end_at
    end_at = begin_at + 30 * 24 * 60 * 60
    pair_begin_at = end_at
    pair_end_at = pair_begin_at + 1
    vote_begin_at = pair_end_at
    vote_end_at = vote_begin_at + 1

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

    # CycleIcpperStat
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(owner_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.0'),
        ei=decimal.Decimal('1.0'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(icpper_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.3'),
        ei=decimal.Decimal('1.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[0].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[0].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[1].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[1].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[2].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[2].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_reviewer_has_warning_user_ids=[str(mock_users[1].id)]
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[3].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[3].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_08=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[4].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[4].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_04=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[5].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[5].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id),
                                   user_id=str(mock_users[6].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[6].id),
        job_count=2,
        size=decimal.Decimal('4.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_deducted_size_by_review=decimal.Decimal('1.0')
    ).save()


def create_tip_end_cycle_2_data(owner_user, icpper_user, mock_users, dao_name):
    dao = DAO.objects(name=dao_name).first()
    prev_cycle = Cycle.objects(dao_id=str(dao.id)).first()

    current_datetime = datetime.fromtimestamp(int(time.time()), tz=timezone(timedelta(hours=8)))
    current_datetime = datetime(
        year=current_datetime.year,
        month=current_datetime.month,
        day=current_datetime.day,
        tzinfo=current_datetime.tzinfo
    )
    vote_end_at = current_datetime.timestamp() - 1 * 60 * 60
    vote_begin_at = vote_end_at - 12 * 60 * 60
    pair_end_at = vote_begin_at
    pair_begin_at = pair_end_at - 12 * 60 * 60
    end_at = pair_begin_at

    # Cycle
    cycle = Cycle(
        dao_id=str(dao.id),
        begin_at=prev_cycle.end_at,
        end_at=end_at,
        pair_begin_at=pair_begin_at,
        pair_end_at=pair_end_at,
        vote_begin_at=vote_begin_at,
        vote_end_at=vote_end_at,
        paired_at=pair_begin_at + 1,
        vote_result_stat_at=vote_end_at + 1,
        vote_result_published_at=vote_end_at + 2
    )
    cycle.save()

    # CycleIcpperStat
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(owner_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(owner_user.id),
        job_count=2,
        size=decimal.Decimal('3.0'),
        job_size=decimal.Decimal('3.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(300), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.0'),
        ei=decimal.Decimal('1.0'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(icpper_user.id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(icpper_user.id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('1.0'),
        owner_ei=decimal.Decimal('0.3'),
        ei=decimal.Decimal('1.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
    ).save()
    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[0].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[0].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[1].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[1].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[2].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[2].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_reviewer_has_warning_user_ids=[str(mock_users[1].id)]
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[3].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[3].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.7'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.7'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_08=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[4].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[4].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.3'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.3'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        have_two_times_lt_04=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[5].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[5].id),
        job_count=2,
        size=decimal.Decimal('5.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=True
    ).save()

    #
    # have_two_times_lt_08 = BooleanField()
    # have_two_times_lt_04 = BooleanField()
    # be_reviewer_has_warning_user_ids = ListField()
    # be_deducted_size_by_review = DecimalField(precision=2)
    last = CycleIcpperStat.objects(dao_id=str(dao.id), cycle_id=str(prev_cycle.id), user_id=str(mock_users[6].id)).first()
    CycleIcpperStat(
        dao_id=str(dao.id),
        cycle_id=str(cycle.id),
        user_id=str(mock_users[6].id),
        job_count=2,
        size=decimal.Decimal('4.0'),
        job_size=decimal.Decimal('5.0'),
        incomes=_get_mock_token_income(dao, [decimal.Decimal(500), decimal.Decimal(200), decimal.Decimal(200)]),
        vote_ei=decimal.Decimal('0.9'),
        owner_ei=decimal.Decimal('0'),
        ei=decimal.Decimal('0.9'),
        last_id=str(last.id),
        un_voted_all_vote=False,
        be_deducted_size_by_review=decimal.Decimal('1.0')
    ).save()


def create_one_empty_cycle(owner_user, dao_name, job_times, pair_times, vote_times):
    if dao_name == 'icpdao-test-vote':
        github_owner_id = 91443188
    else:
        github_owner_id = _get_github_user_id(dao_name)
    # DAO
    dao = DAO(
        name=dao_name,
        logo='https://s3.amazonaws.com/dev.files.icpdao/avatar/rc-upload-1623139230084-2',
        desc='{}_{}_{}'.format(dao_name, dao_name, dao_name),
        owner_id=str(owner_user.id),
        github_owner_id=github_owner_id,
        github_owner_name=dao_name
    )
    dao.save()
    DAOToken(
        dao_id=str(dao.id),
        token_chain_id="3",
        token_address=web3.Account.create().address,
        token_name=dao_name,
        token_symbol=dao_name
    ).save()

    dao_job_config = DAOJobConfig(
        dao_id=str(dao.id)
    )
    dao_job_config.save()


def create_end_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'icpdao-test-icp')


def create_end_and_not_pair_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end-and-not-pair')
    create_not_pair_cycle_data(owner_user, icpper_user, 'end-and-not-pair')


def create_end_and_in_pair_time_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end-and-in-pair-time')
    create_in_pair_time_cycle_data(owner_user, icpper_user, 'end-and-in-pair-time')


def create_end_and_in_vote_time_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end-and-in-vote-time')
    create_in_vote_time_cycle_data(owner_user, icpper_user, 'end-and-in-vote-time')


def create_end_and_in_stat_time_cycle_dao(owner_user, icpper_user):
    create_one_end_cycle_data(owner_user, icpper_user, 'end-and-in-stat-time')
    create_in_stat_time_cycle_data(owner_user, icpper_user, 'end-and-in-stat-time')


def create_tip_cycle_dao(owner_user, icpper_user, mock_users):
    create_tip_end_cycle_1_data(owner_user, icpper_user, mock_users, 'end-and-tip')
    create_tip_end_cycle_2_data(owner_user, icpper_user, mock_users, 'end-and-tip')


def create_end_cycle_and_mint_dao(owner_user, icpper_user, mock_users):
    create_end_cycle_and_mint_1_data(owner_user, icpper_user, mock_users, 'end-and-mint')
    create_end_cycle_and_mint_2_data(owner_user, icpper_user, mock_users, 'end-and-mint')
    create_end_cycle_and_mint_3_data(owner_user, icpper_user, mock_users, 'end-and-mint')


def init_mock_data(owner_github_user_login, icpper_github_user_login):
    delete_dao_name_list = [
        "icpdao-test-fushang318github-change"
    ]

    dao_name_list = [
        "end-and-in-pair-timeend-and-in-vote-time",
        "icpdao-test-icp",
        "end-and-not-pair",
        "end-and-in-pair-time",
        "end-and-in-vote-time",
        "end-and-in-stat-time",
        "end-and-tip",
        "end-and-mint"
    ]

    mock_user_names = [
        "mock_user_1",
        "mock_user_2",
        "mock_user_3",
        "mock_user_4",
        "mock_user_5",
        "mock_user_6",
        "mock_user_7",
        "mock_user_7_mentor_1",
        "mock_user_7_mentor_2"
    ]

    for dao_name in delete_dao_name_list:
        dao = DAO.objects(name=dao_name).first()
        if dao:
            DeleteDaoMock(dao).delete()

    for dao_name in dao_name_list:
        dao = DAO.objects(name=dao_name).first()
        if dao:
            DeleteDaoMock(dao).delete()

    mock_user_ids = User.objects(github_login__in=mock_user_names).distinct('_id')
    owner_and_icpper_user_ids = User.objects(github_login__in=[owner_github_user_login, icpper_github_user_login]).distinct('_id')

    Icppership.objects(icpper_user_id__in=mock_user_ids).delete()
    MentorRelationStat.objects(token_stat__token_count=1001).delete()
    MentorRelationStat.objects(icpper_id__in=mock_user_ids).delete()
    MentorLevel7IcpperCountStat.objects(mentor_id__in=mock_user_ids).delete()
    MentorTokenIncomeStat.objects(token_name__in=['test_token_1', 'test_token_2', 'test_token_3']).delete()

    Icppership.objects(icpper_user_id__in=owner_and_icpper_user_ids).delete()
    MentorRelationStat.objects(icpper_id__in=owner_and_icpper_user_ids).delete()
    MentorLevel7IcpperCountStat.objects(mentor_id__in=owner_and_icpper_user_ids).delete()

    User.objects(github_login__in=mock_user_names).delete()

    mock_users = []
    for mock_user_name in mock_user_names:
        user = User(
            nickname=mock_user_name,
            github_login=mock_user_name,
            github_user_id=_get_github_user_id(mock_user_name),
            avatar='/xxxx',
            status=UserStatus.ICPPER.value,
            erc20_address=web3.Account.create().address
        ).save()
        mock_users.append(user)

    owner_user = User.objects(github_login=owner_github_user_login).first()
    icpper_user = User.objects(github_login=icpper_github_user_login).first()

    create_end_cycle_dao(owner_user, icpper_user)
    create_end_and_not_pair_cycle_dao(owner_user, icpper_user)
    create_end_and_in_pair_time_cycle_dao(owner_user, icpper_user)
    create_end_and_in_vote_time_cycle_dao(owner_user, icpper_user)
    create_end_and_in_stat_time_cycle_dao(owner_user, icpper_user)
    create_tip_cycle_dao(owner_user, icpper_user, mock_users)
    create_end_cycle_and_mint_dao(owner_user, icpper_user, mock_users)
    Icppership.objects(
        mentor_user_id=str(mock_users[7].id),
        icpper_user_id=str(mock_users[6].id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=mock_users[6].github_login,
    )
    Icppership.objects(
        mentor_user_id=str(mock_users[8].id),
        icpper_user_id=str(mock_users[7].id)
    ).upsert_one(
        progress=IcppershipProgress.ACCEPT.value,
        status=IcppershipStatus.ICPPER.value,
        icpper_github_login=mock_users[7].github_login,
    )
