import decimal
import time
import random

from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask, CycleVotePairTaskStatus
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.job import Job
from tests.base import Base


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


class TestCycleUserVoting(Base):
    get_one_voting_cycle_node = """
    query{
        votingCycle{
            datum{
                id
                daoId
            }
        }
    }
"""

    @staticmethod
    def get_cycle_time_by_end_at(end_at):
        begin_at = end_at - 30 * 24 * 60 * 60
        end_at = end_at
        pair_begin_at = end_at + 12 * 60 * 60
        pair_end_at = pair_begin_at + 18 * 60 * 60
        vote_begin_at = pair_end_at
        vote_end_at = vote_begin_at + 18 * 60 * 60

        return begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at

    def test_voting_cycle(self):
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper.id),
            github_owner_id=_get_github_user_id('test_dao'),
            github_owner_name='test_dao'
        )
        test_dao.save()

        res = self.graph_query(
            self.icpper.id, self.get_one_voting_cycle_node
        )

        assert res.json()['data']['votingCycle']['datum'] is None

        now_at = int(time.time())
        test_cycle = Cycle(
            dao_id=str(test_dao.id),
            begin_at=now_at - 5 * 60 * 60,
            end_at=now_at - 4 * 60 * 60,
            pair_begin_at=now_at - 3 * 60 * 60,
            pair_end_at=now_at - 2 * 60 * 60,
            vote_begin_at=now_at - 1 * 60 * 60,
            vote_end_at=now_at + 1 * 60 * 60
        )
        test_cycle.save()

        res = self.graph_query(
            self.icpper.id, self.get_one_voting_cycle_node
        )

        assert res.json()['data']['votingCycle']['datum'] is None

        Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper.id),
            title="1",
            size=decimal.Decimal("1"),
            github_repo_owner="1",
            github_repo_name="1",
            github_repo_owner_id=1,
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1
        ).save()

        res = self.graph_query(
            self.icpper.id, self.get_one_voting_cycle_node
        )

        assert res.json()['data']['votingCycle']['datum']['id'] == str(test_cycle.id)
        assert res.json()['data']['votingCycle']['datum']['daoId'] == str(test_dao.id)
