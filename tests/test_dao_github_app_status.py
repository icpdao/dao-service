import os

from tests.base import Base

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

from app.common.models.icpdao.dao import DAO, DAOFollow


class TestDAOGithubAppStatus(Base):

    get = """
query{
    daoGithubAppStatus(name: "%s"){
        githubOrgId
        isExists
        isGithubOrgOwner
        isIcpAppInstalled
    }
}
"""

    def test_get(self):
        self.clear_db()
        self.icpper = self.create_icpper_user('fushang318', 'fushang318')

        res = self.graph_query(
            self.icpper.id, self.get % 'icpdao'
        ).json()

        status = res["data"]["daoGithubAppStatus"]

        assert status["githubOrgId"] == 0
        assert status["isExists"] == True
        assert status["isGithubOrgOwner"] == True
        assert status["isIcpAppInstalled"] == True
