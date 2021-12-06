import random
import time
import random

from mongoengine import Q

from app.common.models.icpdao.cycle import Cycle, CycleVote, CycleVoteConfirm, CycleVoteConfirmStatus, CycleVoteType
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job
from tests.base import Base


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


class TestUpdateVote(Base):
    update_pair_vote = """
mutation {
  updatePairVote(id: "%s", voteJobId: "%s") {
    ok
  }
}
"""
    update_all_vote = """
mutation {
  updateAllVote(id: "%s", vote: %s) {
    ok
  }
}
"""
    update_pair_vote_with_repeat = """
    mutation {
      updatePairVoteWithRepeat(id: "%s", voteJobId: "%s") {
        ok
      }
    }
    """

    @staticmethod
    def create_job(dao_id, user_id, cycle_id, pair_type=0):
        job = Job(
            dao_id=dao_id, user_id=user_id, title="xxx",
            size=random.randint(1, 10),
            github_repo_owner='mockdao',
            github_repo_name='mockrepo',
            github_repo_owner_id=_get_github_user_id("mockdao"),
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1,
            status=2,
            pair_type=pair_type,
            cycle_id=cycle_id)
        job.save()
        return job

    @staticmethod
    def create_cycle_vote(
            dao_id, cycle_id, pair_type, left_job, right_job=None, voter=None):
        if pair_type == 0:
            record = CycleVote(
                dao_id=dao_id, cycle_id=cycle_id, left_job_id=str(left_job.id),
                right_job_id=str(right_job.id),
                vote_type=0,
                voter_id=str(voter.id)
            )
            record.save()
            return record
        record = CycleVote(
            dao_id=dao_id, cycle_id=cycle_id, left_job_id=str(left_job.id),
            right_job_id=str(left_job.id), vote_type=1)
        record.save()
        return record

    @staticmethod
    def create_cycle_confirm(dao_id, cycle_id, voter):
        record = CycleVoteConfirm(
            dao_id=dao_id,
            cycle_id=cycle_id,
            voter_id=str(voter.id),
            status=CycleVoteConfirmStatus.WAITING.value
        ).save()
        return record

    def create_vote(self):
        self.icpper1 = self.create_icpper_user('mockicpper1', 'mockicpper1')
        self.icpper2 = self.create_icpper_user('mockicpper2', 'mockicpper2')
        self.icpper3 = self.create_icpper_user('mockicpper3', 'mockicpper3')
        self.icpper4 = self.create_icpper_user('mockicpper4', 'mockicpper4')
        self.icpper5 = self.create_icpper_user('mockicpper5', 'mockicpper5')
        mockdao = DAO(
            name='mockdao', owner_id=str(self.icpper1.id),
            github_owner_id=_get_github_user_id('mockdao'),
            github_owner_name='mockdao'
        )
        mockdao.save()
        self.dao = mockdao
        dao_id = str(mockdao.id)
        cycle = Cycle(
            dao_id=dao_id, vote_begin_at=0, vote_end_at=33180161000,
            paired_at=time.time())
        cycle.save()
        self.cycle = cycle
        cycle_id = str(cycle.id)
        self.job1 = self.create_job(str(mockdao.id), str(self.icpper1.id), str(cycle.id))
        self.job2 = self.create_job(str(mockdao.id), str(self.icpper2.id), str(cycle.id))
        self.job3 = self.create_job(str(mockdao.id), str(self.icpper2.id), str(cycle.id))
        self.job4 = self.create_job(str(mockdao.id), str(self.icpper3.id), str(cycle.id))
        self.job5 = self.create_job(str(mockdao.id), str(self.icpper4.id), str(cycle.id))
        self.job6 = self.create_job(str(mockdao.id), str(self.icpper4.id), str(cycle.id))
        self.job7 = self.create_job(str(mockdao.id), str(self.icpper4.id), str(cycle.id))

        self.vote1 = self.create_cycle_vote(dao_id, cycle_id, 1, self.job1)
        self.vote2 = self.create_cycle_vote(dao_id, cycle_id, 1, self.job2)
        self.vote3 = self.create_cycle_vote(dao_id, cycle_id, 1, self.job3)

        self.vote4 = self.create_cycle_vote(
            dao_id, cycle_id, 0, self.job4, self.job5, self.icpper1)
        self.vote5 = self.create_cycle_vote(
            dao_id, cycle_id, 0, self.job5, self.job6, self.icpper3)
        self.vote6 = self.create_cycle_vote(
            dao_id, cycle_id, 0, self.job6, self.job7, self.icpper2)
        self.vote7 = self.create_cycle_vote(
            dao_id, cycle_id, 0, self.job7, self.job4, self.icpper2)
        self.vote8 = self.create_cycle_vote(
            dao_id, cycle_id, 0, self.job7, self.job4, self.icpper2)
        self.vote8.is_repeat = True
        self.vote8.save()
        self.create_cycle_confirm(dao_id, cycle_id, self.icpper1)
        self.create_cycle_confirm(dao_id, cycle_id, self.icpper2)
        self.create_cycle_confirm(dao_id, cycle_id, self.icpper3)
        self.create_cycle_confirm(dao_id, cycle_id, self.icpper4)

    def test_update_pair_vote(self):
        self.create_vote()
        res = self.graph_query(
            str(self.icpper2.id),
            self.update_pair_vote % (str(self.vote4.id), str(self.job4.id))
        )
        data = res.json()
        assert data['errors'][0]['message'] == 'NOT PERMISSION VOTE'
        res = self.graph_query(
            str(self.icpper1.id),
            self.update_pair_vote % (str(self.vote4.id), str(self.job4.id))
        )
        data = res.json()
        assert data['data']['updatePairVote']['ok'] is True
        res = self.graph_query(
            str(self.icpper3.id),
            self.update_pair_vote % (str(self.vote5.id), str(self.job6.id))
        )
        data = res.json()
        assert data['data']['updatePairVote']['ok'] is True

        res = self.graph_query(
            str(self.icpper2.id),
            self.update_pair_vote % (str(self.vote6.id), str(self.job7.id))
        )
        data = res.json()
        assert data['data']['updatePairVote']['ok'] is True

        res = self.graph_query(
            str(self.icpper2.id),
            self.update_pair_vote % (str(self.vote7.id), str(self.job7.id))
        )
        data = res.json()
        assert data['data']['updatePairVote']['ok'] is True

    def test_update_all_vote(self):
        self.clear_db()
        self.create_vote()
        res = self.graph_query(
            str(self.icpper1.id),
            self.update_all_vote % (str(self.vote1.id), 'true')
        )
        data = res.json()
        assert data['data']['updateAllVote']['ok'] is True

        res = self.graph_query(
            str(self.icpper5.id),
            self.update_all_vote % (str(self.vote1.id), 'false')
        )
        data = res.json()
        assert data['errors'][0]['message'] == 'NOT PERMISSION VOTE'


        res = self.graph_query(
            str(self.icpper2.id),
            self.update_all_vote % (str(self.vote1.id), 'true')
        )
        res = self.graph_query(
            str(self.icpper3.id),
            self.update_all_vote % (str(self.vote1.id), 'false')
        )
        res = self.graph_query(
            str(self.icpper4.id),
            self.update_all_vote % (str(self.vote1.id), 'true')
        )
        vote = CycleVote.objects(id=str(self.vote1.id)).first()
        assert vote.vote_result_stat_type_all == 75

    def test_get_vote(self):
        self.clear_db()
        self.create_vote()

        res = CycleVote.objects.filter(Q(vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=False))

        assert res.count() == CycleVote.objects(vote_type=CycleVoteType.PAIR.value).count()

        res = self.graph_query(
            str(self.icpper1.id),
            self.update_pair_vote % (str(self.vote4.id), str(self.job4.id))
        )

        res = CycleVote.objects.filter(Q(vote_type=CycleVoteType.PAIR.value, vote_job_id__exists=False))
        assert res.count() == CycleVote.objects(vote_type=CycleVoteType.PAIR.value).count() - 1

        res = CycleVote.objects.filter(Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id__ne=str(self.icpper2.id)))
        assert res.count() == CycleVote.objects(vote_type=CycleVoteType.ALL.value).count()
        res = self.graph_query(
            str(self.icpper2.id),
            self.update_all_vote % (str(self.vote1.id), 'true')
        )
        res = CycleVote.objects.filter(
            Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id__ne=str(self.icpper2.id)))
        assert res.count() == CycleVote.objects(vote_type=CycleVoteType.ALL.value).count() - 1
        self.graph_query(
            str(self.icpper4.id),
            self.update_all_vote % (str(self.vote2.id), 'true')
        )
        res = CycleVote.objects.filter(
            Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id__ne=str(self.icpper2.id)))
        assert res.count() == CycleVote.objects(vote_type=CycleVoteType.ALL.value).count() - 1
        res = CycleVote.objects.filter(
            Q(vote_type=CycleVoteType.ALL.value, vote_result_type_all__voter_id=str(self.icpper4.id)))

    def test_update_pair_vote_with_repeat(self):
        self.clear_db()
        self.create_vote()
        self.cycle.vote_end_at = int(time.time()) - 60 * 60
        self.cycle.save()

        res = self.graph_query(
            str(self.icpper4.id),
            self.update_pair_vote_with_repeat % (str(self.vote8.id), str(self.job4.id))
        )
        data = res.json()
        assert data['errors'][0]['message'] == 'NOT PERMISSION VOTE'

        res = self.graph_query(
            str(self.dao.owner_id),
            self.update_pair_vote_with_repeat % (str(self.vote8.id), str(self.job4.id))
        )
        data = res.json()
        assert data['data']['updatePairVoteWithRepeat']['ok'] is True

