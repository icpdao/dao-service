from fastapi.testclient import TestClient

from app import app, graph_route
from app.common.models.icpdao.user import User, UserStatus
from app.common.models.icpdao.dao import DAO, DAOJobConfig, DAOFollow


class Base:
    client = TestClient(app)

    @classmethod
    def setup_class(cls):
        cls.clear_db()

    @classmethod
    def teardown_class(cls):
        cls.clear_db()

    @classmethod
    def clear_db(cls):
        User.drop_collection()
        DAOFollow.drop_collection()
        DAOJobConfig.drop_collection()
        DAO.drop_collection()

    @staticmethod
    def create_icpper_user(nickname='test_icpper', github_login='test_github_login'):
        record = User(
            nickname=nickname,
            github_login=github_login,
            status=UserStatus.ICPPER.value,
            avatar='test_avatar'
        )
        record.save()
        return record

    @staticmethod
    def create_normal_user(nickname='test_user'):
        record = User(
            nickname=nickname,
            github_login='test_github_login',
            status=UserStatus.NORMAL.value,
            avatar='test_avatar'
        )
        record.save()
        return record

    def graph_query(self, user_id, query):
        return self.client.post(
            graph_route, headers={'user_id': str(user_id)},
            json={
                'query': query,
                'variables': None
            }
        )

