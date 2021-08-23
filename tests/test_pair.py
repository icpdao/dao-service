import time
from decimal import Decimal
import random

from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask, CycleVote, CycleVoteType, CycleVoteConfirm, \
    CycleVoteConfirmStatus
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job, JobStatusEnum, JobPairTypeEnum, JobPR, JobPRStatusEnum
from app.common.models.icpdao.user import User
from app.controllers.pair import run_pair_task
from tests.base import Base


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


class TestPair(Base):

    @staticmethod
    def get_cycle_time_by_end_at(end_at):
        begin_at = end_at - 30 * 24 * 60 * 60
        end_at = end_at
        pair_begin_at = end_at + 12 * 60 * 60
        pair_end_at = pair_begin_at + 18 * 60 * 60
        vote_begin_at = pair_end_at
        vote_end_at = vote_begin_at + 18 * 60 * 60

        return begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at

    def test_pair(self):
        self.__class__.clear_db()
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')
        self.icpper3 = self.__class__.create_icpper_user(nickname='icpper3', github_login='iccper3')

        DAO(
            name='test_dao2',
            logo='xxx.png2',
            desc='test_dao_desc2',
            owner_id=str(self.icpper2.id),
            github_owner_id=_get_github_user_id('test_dao2'),
            github_owner_name='test_dao2'
        ).save()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper1.id),
            github_owner_id=_get_github_user_id('test_dao'),
            github_owner_name='test_dao'
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=end_at - 1,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()


        icpper1_job_1 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_job_1",
            size=Decimal("1.0"),
            labels=['ICP_UI'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper1_job_1.save()

        icpper1_job_1_pr = JobPR(
            job_id=str(icpper1_job_1.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_job_1_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=101,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper2.github_login),
            merged_at=time.time()
        )
        icpper1_job_1_pr.save()

        icpper1_job_2 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_job_2",
            size=Decimal("1.0"),
            labels=['ICP_OP'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=2,
            bot_comment_database_id=2,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper1_job_2.save()

        icpper1_job_2_pr = JobPR(
            job_id=str(icpper1_job_2.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_job_2_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=102,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper2.github_login),
            merged_at=time.time()
        )
        icpper1_job_2_pr.save()

        icpper2_job_1 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_job_1",
            size=Decimal("1.0"),
            labels=['ICP_UI'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=3,
            bot_comment_database_id=3,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper2_job_1.save()

        icpper2_job_1_pr = JobPR(
            job_id=str(icpper2_job_1.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_job_1_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=103,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper3.github_login),
            merged_at=time.time()
        )
        icpper2_job_1_pr.save()

        icpper2_job_2 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_job_2",
            size=Decimal("1.0"),
            labels=['ICP_OP'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=4,
            bot_comment_database_id=4,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper2_job_2.save()

        icpper2_job_2_pr = JobPR(
            job_id=str(icpper2_job_2.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_job_2_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=104,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper3.github_login),
            merged_at=time.time()
        )
        icpper2_job_2_pr.save()

        icpper3_job_1 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_1",
            size=Decimal("1.0"),
            labels=['ICP_UI'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=5,
            bot_comment_database_id=5,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper3_job_1.save()

        icpper3_job_1_pr = JobPR(
            job_id=str(icpper3_job_1.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_1_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=105,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper1.github_login),
            merged_at=time.time()
        )
        icpper3_job_1_pr.save()

        icpper3_job_2 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_2",
            size=Decimal("1.0"),
            labels=['ICP_OP'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=6,
            bot_comment_database_id=6,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper3_job_2.save()

        icpper3_job_2_pr = JobPR(
            job_id=str(icpper3_job_2.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_2_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=106,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper1.github_login),
            merged_at=time.time()
        )
        icpper3_job_2_pr.save()

        icpper3_job_all = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_all",
            size=Decimal("1.0"),
            labels=['ICP_OP'],
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_issue_number=7,
            bot_comment_database_id=7,
            status=JobStatusEnum.MERGED.value,
            pair_type=JobPairTypeEnum.ALL.value,
            cycle_id=str(test_cycle_2.id)
        )
        icpper3_job_all.save()

        icpper3_job_all_pr = JobPR(
            job_id=str(icpper3_job_2.id),
            user_id=str(self.icpper3.id),
            title="test_dao_icpper3_job_all_pr",
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_owner_id=_get_github_user_id("icpdao"),
            github_repo_id=1,
            github_pr_number=107,
            status=JobPRStatusEnum.MERGED.value,
            merged_user_github_user_id=_get_github_user_id(self.icpper1.github_login),
            merged_at=time.time()
        )
        icpper3_job_all_pr.save()

        task = CycleVotePairTask(
            dao_id=test_cycle_2.dao_id,
            cycle_id=str(test_cycle_2.id)
        ).save()
        assert CycleVote.objects().count() == 0
        run_pair_task(str(task.id))
        assert CycleVote.objects().count() == 7

        assert CycleVote.objects(vote_type=CycleVoteType.ALL.value, is_result_public=True).count() == 1
        all_vote = CycleVote.objects(vote_type=CycleVoteType.ALL.value, is_result_public=True).first()
        assert all_vote.left_job_id == str(icpper3_job_all.id)
        assert all_vote.right_job_id == str(icpper3_job_all.id)
        assert all_vote.dao_id == str(test_dao.id)
        assert all_vote.cycle_id == str(test_cycle_2.id)

        assert CycleVote.objects(dao_id=str(test_dao.id), cycle_id=str(test_cycle_2.id), vote_type=CycleVoteType.PAIR.value, is_result_public=False).count() == 6

        vote_list = CycleVote.objects(dao_id=str(test_dao.id), cycle_id=str(test_cycle_2.id),
                                 vote_type=CycleVoteType.PAIR.value, is_result_public=False)

        pair_job_id_list = [
            str(icpper1_job_1.id),
            str(icpper1_job_2.id),
            str(icpper2_job_1.id),
            str(icpper2_job_2.id),
            str(icpper3_job_1.id),
            str(icpper3_job_2.id),
        ]

        jobid_2_count = {}
        for item in vote_list:
            left_job = Job.objects(id=item.left_job_id).first()
            right_job = Job.objects(id=item.right_job_id).first()
            voter = User.objects(id=item.voter_id).first()
            jobid_2_count.setdefault(item.left_job_id, 0)
            jobid_2_count.setdefault(item.right_job_id, 0)

            jobid_2_count[item.left_job_id] += 1
            jobid_2_count[item.right_job_id] += 1

            assert left_job.user_id != right_job.user_id
            assert left_job.user_id != str(voter.id)
            assert right_job.user_id != str(voter.id)
            assert item.left_job_id in pair_job_id_list
            assert item.right_job_id in pair_job_id_list

        for jobid in jobid_2_count:
            count = jobid_2_count[jobid]
            assert count <= 2

        cyc = CycleVoteConfirm.objects().all()
        assert len(cyc) == 3
        for c in cyc:
            assert c.status == CycleVoteConfirmStatus.WAITING.value
