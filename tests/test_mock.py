from tests.base import Base


class TestMock(Base):

    create_mock = """
mutation{
  createMock(ownerGithubUserLogin: "%s", icpperGithubUserLogin: "%s", otherGithubUserLogin: "%s"){
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
                self.icpper2.github_login,
                self.icpper3.github_login
            )
        )
