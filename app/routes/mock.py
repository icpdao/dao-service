from graphene import Mutation, String, Boolean

from app.controllers.mock import init_mock_data


class CreateMock(Mutation):
    class Arguments:
        owner_github_user_login = String(required=True)
        icpper_github_user_login = String(required=True)

    ok = Boolean()

    def mutate(self, info, owner_github_user_login, icpper_github_user_login):
        background_tasks = info.context['background']
        background_tasks.add_task(init_mock_data, owner_github_user_login, icpper_github_user_login)

        return CreateMock(ok=True)
