from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask, CycleVote, CycleVoteType
from app.common.models.icpdao.dao import DAO
from app.controllers.pair import run_pair_task
from tests.base import Base


class TestMock(Base):

    create_mock = """
mutation{
  createMock(ownerGithubUserLogin: "%s", icpperGithubUserLogin: "%s"){
    ok
  }
}
"""

    def test_pair(self):
        self.__class__.clear_db()
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')
        self.icpper3 = self.__class__.create_icpper_user(nickname='icpper3', github_login='iccper3')

        res = self.graph_query(
            self.icpper1.id, self.create_mock % (
                self.icpper1.github_login,
                self.icpper2.github_login
            )
        )
        print(res.json())

        dao = DAO.objects(name="end-and-in-pair-time").first()
        cycle = Cycle.objects(dao_id=str(dao.id)).order_by("-begin_at").first()
        task = CycleVotePairTask(
            dao_id=str(dao.id),
            cycle_id=str(cycle.id)
        ).save()
        run_pair_task(str(task.id))

        dao = DAO.objects(name="end-and-in-vote-time").first()
        vote_cycle = Cycle.objects(dao_id=str(dao.id)).order_by("-begin_at").first()
        self.get_cycle_vote_list_is_myself = """
        query{
            cycle(id: "%s"){
                votes(isMyself: true){
                    nodes{
                        datum{
                            id
                            createAt
                            updateAt
                        }
                    }
                }
            }
        }
        """

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_is_myself % str(vote_cycle.id)
        )
        votes_list = res.json()['data']['cycle']['votes']['nodes']
        vote_id_list = []
        for vote in votes_list:
            vote_id_list.append(vote['datum']['id'])
        print(vote_id_list)

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

        for vote_id in vote_id_list:
            vote = CycleVote.objects(id=vote_id).first()
            if vote.vote_type == CycleVoteType.ALL.value:
                res = self.graph_query(
                    str(self.icpper1.id),
                    update_all_vote % (str(vote_id), 'true')
                )
                data = res.json()
                assert data['data']['updateAllVote']['ok'] is True
            else:
                res = self.graph_query(
                    str(self.icpper1.id),
                    update_pair_vote % (str(vote_id), str(vote.left_job_id))
                )
                data = res.json()
                assert data['data']['updatePairVote']['ok'] is True

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_is_myself % str(vote_cycle.id)
        )
        votes_list = res.json()['data']['cycle']['votes']['nodes']
        vote_id_list = []
        for vote in votes_list:
            vote_id_list.append(vote['datum']['id'])
        print(vote_id_list)
