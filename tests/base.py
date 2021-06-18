from fastapi.testclient import TestClient
from mongoengine.connection import get_db

from app import app, graph_route
from app.common.models.icpdao.github_app_token import GithubAppToken
from app.common.models.icpdao.user import User, UserStatus


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
        get_db('icpdao').client.drop_database('icpdao')

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

    def graph_query(self, user_id, query, variables=None):
        return self.client.post(
            graph_route, headers={'user_id': str(user_id)},
            json={
                'query': query,
                'variables': variables
            }
        )

    def gen_github_app_token(self):
        with open(
                './github_app.pem', 'r') as f:
            cert_str = f.read()
        return GithubAppToken.get_token(
            app_id='111590', app_private_key=cert_str, dao_name='icpdao')


if __name__ == '__main__':
    print(Base().gen_github_app_token())
    # print(Base().create_icpper_user(github_login='bqx619'))
