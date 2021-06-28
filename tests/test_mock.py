from app.common.models.icpdao.cycle import Cycle, CycleVotePairTask
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
