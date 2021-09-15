from graphene import Mutation, String, Boolean

from app.common.utils.errors import COMMON_NOT_PERMISSION_ERROR
from app.controllers.mock import init_mock_data
from settings import ICPDAO_APP_ENV


class CreateMock(Mutation):
    class Arguments:
        owner_github_user_login = String(required=True)
        icpper_github_user_login = String(required=True)

    ok = Boolean()

    def mutate(self, info, owner_github_user_login, icpper_github_user_login):
        assert ICPDAO_APP_ENV != 'PROD', COMMON_NOT_PERMISSION_ERROR
        background_tasks = info.context['background']
        background_tasks.add_task(init_mock_data, owner_github_user_login, icpper_github_user_login)

        return CreateMock(ok=True)
