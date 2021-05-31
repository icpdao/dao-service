from graphene import ObjectType, List, Int, String, Mutation, Boolean, NonNull
from graphql import ResolveInfo

from app.common.models.icpdao.dao import DAOFollow
from app.common.schema.icpdao import DAOFollowSchema as DFs
from app.common.utils.access import check_is_dao_owner, check_is_not_dao_owner
from app.common.utils.route_helper import get_current_user_by_graphql
from app.routes.schema import DAOFollowTypeEnum


class DAOFollowUDSchema(ObjectType):
    dao_id = String(required=True)
    followers = List(DFs, user_id=String())
    total = Int(required=True)

    @staticmethod
    def resolve_followers(parent, info, user_id=''):
        dao_id = parent.dao_id
        current_user = get_current_user_by_graphql(info)
        if not user_id:
            # query all, only owner can do
            check_is_dao_owner(current_user, dao_id=dao_id)
            return list(DAOFollow.objects(dao_id=dao_id).all())
        if str(current_user.id) != user_id:
            check_is_dao_owner(current_user, dao_id=dao_id)
        return [DAOFollow.objects(dao_id=dao_id, user_id=user_id).first()]

    @staticmethod
    def resolve_total(parent, info):
        dao_id = parent.dao_id
        return DAOFollow.objects(dao_id=dao_id).count()


class UpdateDAOFollow(Mutation):
    class Arguments:
        dao_id = String(required=True)
        type = NonNull(DAOFollowTypeEnum)

    ok = Boolean()

    @staticmethod
    def mutate(root, info: ResolveInfo, dao_id, type):
        # can't be owner
        current_user = get_current_user_by_graphql(info)
        check_is_not_dao_owner(
            current_user, dao_id=dao_id)
        record = DAOFollow.objects(
            dao_id=dao_id, user_id=str(current_user.id)).first()
        if type == DAOFollowTypeEnum.ADD and not record:
            record = DAOFollow(
                dao_id=dao_id, user_id=str(current_user.id))
            record.save()
            return UpdateDAOFollow(ok=True)
        if type == DAOFollowTypeEnum.DELETE and record:
            record.delete()
            return UpdateDAOFollow(ok=True)
        raise ValueError('NOT RIGHT UPDATE FOLLOW')
