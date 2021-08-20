import random
import time
from decimal import Decimal

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.dao import DAO
from tests.base import Base


def _get_github_user_id(github_login):
    random.seed(github_login)
    github_user_id = int(random.random() * 10000)
    random.seed()
    return github_user_id


class TestUserIcpperStats(Base):
    get_icpper_stats_list = """
    query{
        icpperStats(daoName: "%s", userName: "%s", first: %s, offset: %s){
            nodes {
              datum {
                id
                jobCount
                size
                income
                ei
                ownerEi
                voteEi
                beDeductedSizeByReview
                haveTwoTimesLt04
                haveTwoTimesLt08
                unVotedAllVote
              }
              cycle {
                id
                timeZone
                beginAt
                endAt
                pairBeginAt
                pairEndAt
                voteBeginAt
                voteEndAt
                pairedAt
                voteResultPublishedAt
                createAt
                updateAt
              }
              icpper {
                id
                avatar
                nickname
                githubLogin
              }
              lastEi
              beReviewerHasWarningUsers {
                id
                nickname
              }
            }
            total
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

    def test_query_list(self):
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper.id),
            github_owner_id=_get_github_user_id('test_dao'),
            github_owner_name='test_dao'
        )
        test_dao.save()

        cycle_list = []
        count = 4
        end_at = time.time()
        for index in range(0, count):
            begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
            if index == 0:
                cycle = Cycle(
                    dao_id=str(test_dao.id),
                    begin_at=begin_at,
                    end_at=end_at,
                    pair_begin_at=pair_begin_at,
                    pair_end_at=pair_end_at,
                    vote_begin_at=vote_begin_at,
                    vote_end_at=vote_end_at
                ).save()
            else:
                cycle = Cycle(
                    dao_id=str(test_dao.id),
                    begin_at=begin_at,
                    end_at=end_at,
                    pair_begin_at=pair_begin_at,
                    pair_end_at=pair_end_at,
                    vote_begin_at=vote_begin_at,
                    vote_end_at=vote_end_at,
                    vote_result_published_at=int(time.time())
                ).save()
            cycle_list.append(cycle)
            end_at = cycle.begin_at

        for index in range(0, count):
            cycle = cycle_list[index]
            CycleIcpperStat(
                dao_id=str(test_dao.id),
                cycle_id=str(cycle.id),
                user_id=str(self.icpper.id),
                job_count=1,
                size=Decimal('10') + Decimal(count),
                income=Decimal('1000'),
                vote_ei=1,
                owner_ei=Decimal('0.1'),
                ei=Decimal('1.1'),
                create_at=int(time.time()) - index
            ).save()

        res = self.graph_query(
            self.icpper.id, self.get_icpper_stats_list % (test_dao.name, self.icpper.github_login, 20, 0)
        )

        icpper_stat_list = res.json()['data']['icpperStats']['nodes']
        assert len(icpper_stat_list) == 3

        res = self.graph_query(
            self.icpper.id, self.get_icpper_stats_list % (test_dao.name, self.icpper.github_login, 2, 0)
        )

        icpper_stat_list = res.json()['data']['icpperStats']['nodes']
        total = res.json()['data']['icpperStats']['total']
        assert len(icpper_stat_list) == 2
        assert total == 3

        assert icpper_stat_list[0]['cycle']['id']
