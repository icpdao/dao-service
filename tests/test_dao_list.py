import decimal
import os

from app.common.models.icpdao.job import Job
from tests.base import Base

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

from app.common.models.icpdao.dao import DAO, DAOFollow


class TestDaoList(Base):

    get_daos_no_params = """
query{
  daos {
    dao{
      datum{
        createAt
        desc
        id
        logo
        name
        number
        ownerId
        updateAt
      }
      stat{
        following
        job
        size
        token
      }
      isFollowing
      isOwner
    }
    stat{
      icpper
      size
      income
    }
    total
  }
}
"""

    get_daos_by_params = """
query{
  daos(%s) {
    dao{
      datum{
        createAt
        desc
        id
        logo
        name
        number
        ownerId
        updateAt
      }
      stat{
        following
        job
        size
        token
      }
      isFollowing
      isOwner
    }
    stat{
      icpper
      size
      income
    }
    total
  }
}
"""

    create_dao = """
mutation {
  createDao( name: "%s", desc: "test_dao_1", logo:"test_dao_1", timeZone: 8, timeZoneRegion: "Asia/Shanghai") {
    dao {
      id
      name
      logo
      number
      ownerId
      desc
    }
  }
}
"""

    def test_get_daos_all(self):
        self.clear_db()
        self.icpper = self.create_icpper_user()

        ret = self.graph_query(self.icpper.id, self.get_daos_no_params)
        res = ret.json()
        res_daos = res['data']['daos']['dao']
        assert len(res_daos) == 0

        dao_id1 = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_1'
        ).json()['data']['createDao']['dao']['id']

        dao_id2 = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_2'
        ).json()['data']['createDao']['dao']['id']

        dao_dict = {}
        dao_dict[dao_id1] = DAO.objects(id=dao_id1).first()
        dao_dict[dao_id2] = DAO.objects(id=dao_id2).first()

        ret = self.graph_query(self.icpper.id, self.get_daos_no_params)
        res = ret.json()

        res_stat = res['data']['daos']['stat']
        res_daos = res['data']['daos']['dao']
        res_total = res['data']['daos']['total']

        assert res_stat['icpper'] == 0
        assert res_stat['size'] == '0'
        assert res_stat['income'] == '0'

        assert len(res_daos) == 2
        for dao_item in res_daos:
            db_dao = dao_dict[dao_item['datum']['id']]
            assert dao_item['datum']['desc'] == db_dao.desc
            assert dao_item['datum']['ownerId'] == db_dao.owner_id

    def test_get_daos_by_params(self):
        # all
        # owner
        # following
        # following_and_owner

        # icpper1 1 dao
        # icpper2 2 dao
        # icpper1 follow icpper2 1 dao

        self.clear_db()
        self.icpper1 = self.create_icpper_user('icpper1')
        self.icpper2 = self.create_icpper_user('icpper2')
        self.icpper3 = self.create_icpper_user('icpper3')

        daos_params = [
            [self.icpper1, "test_icpper1_dao1"],
            [self.icpper2, "test_icpper2_dao1"],
            [self.icpper2, "test_icpper2_dao2"]
        ]
        for param in daos_params:
            user = param[0]
            name = param[1]
            self.graph_query(
                user.id, self.create_dao % name
            )

        test_icpper2_dao1 = DAO.objects(name='test_icpper2_dao1').first()
        DAOFollow(dao_id=str(test_icpper2_dao1.id), user_id=str(self.icpper1.id)).save()
        Job(
            dao_id=str(test_icpper2_dao1.id),
            user_id=str(self.icpper1.id), title='xx',
            size=decimal.Decimal('100'), github_repo_owner='xx',
            github_repo_name='xx',
            github_repo_owner_id=2,
            github_repo_id=2,
            github_issue_number=3,
            bot_comment_database_id=3
        ).save()
        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: all')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 3
        assert res['data']['daos']['total'] == 3

        ret = self.graph_query(self.icpper2.id, self.get_daos_by_params % 'filter: owner')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 2
        assert res['data']['daos']['total'] == 2

        assert res['data']['daos']['dao'][0]['isOwner'] == True
        assert res['data']['daos']['dao'][0]['isFollowing'] == False

        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: following')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 1
        assert res['data']['daos']['total'] == 1

        assert res['data']['daos']['dao'][0]['isFollowing'] == True
        assert res['data']['daos']['dao'][0]['isOwner'] == False

        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: following_and_owner')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 2
        assert res['data']['daos']['total'] == 2

        # number asc desc
        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: all, sorted: number, sortedType: desc')
        res = ret.json()

        first_number = res['data']['daos']['dao'][0]['datum']['number']
        end_number = res['data']['daos']['dao'][-1]['datum']['number']

        assert first_number > end_number

        # search
        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: owner, sorted: number, sortedType: desc, search: "Dao1"')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 1
        assert res['data']['daos']['total'] == 1

        # offset
        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: all, offset: 1')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 2
        assert res['data']['daos']['total'] == 3

        # offset limit
        ret = self.graph_query(self.icpper1.id, self.get_daos_by_params % 'filter: all, offset: 1, first: 1')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 1
        assert res['data']['daos']['total'] == 3

        # userName
        ret = self.graph_query(self.icpper3.id, self.get_daos_by_params % 'filter: following_and_owner, userName: "{}"'.format(self.icpper1.github_login))
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 2
        assert res['data']['daos']['total'] == 2

    def test_get_daos_by_no_login(self):
        # all
        self.clear_db()
        self.icpper1 = self.create_icpper_user('icpper1')
        self.icpper2 = self.create_icpper_user('icpper2')
        self.icpper3 = self.create_icpper_user('icpper3')

        daos_params = [
            [self.icpper1, "test_icpper1_dao1"],
            [self.icpper2, "test_icpper2_dao1"],
            [self.icpper2, "test_icpper2_dao2"]
        ]
        for param in daos_params:
            user = param[0]
            name = param[1]
            self.graph_query(
                user.id, self.create_dao % name
            )

        test_icpper2_dao1 = DAO.objects(name='test_icpper2_dao1').first()
        DAOFollow(dao_id=str(test_icpper2_dao1.id), user_id=str(self.icpper1.id)).save()

        ret = self.graph_query_no_login(self.get_daos_by_params % 'filter: all')
        res = ret.json()
        assert len(res['data']['daos']['dao']) == 3
        assert res['data']['daos']['total'] == 3
        assert res['data']['daos']['dao'][0]["datum"]["id"] != None
