from fastapi.testclient import TestClient

from app import app
from app.common.models.icpdao.user import User
from app.common.models.icpdao.user_github_token import UserGithubToken
from app.common.models.icpdao.icppership import Icppership


class Base():
    client = TestClient(app)

    def clear_db(self):
        User.drop_collection()
        UserGithubToken.drop_collection()
        Icppership.drop_collection()

    def create_icpper_user(self, code='user'):
        # TODO

    def create_normal_user(self, code='user'):
        # TODO
