import os

from tests.base import Base

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class TestFollow(Base):
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

    query_dao_follow = """
query {
  dao(id: "%s") {
    datum {
      id
      name
      desc
      logo
      ownerId
    }
    following {
      total
      followers %s {
        userId
        daoId
        createAt
      }
    }
  }
}
"""

    update_follow = """
mutation {
  updateDaoFollow(daoId: "%s", type: %s) {
    ok
  }
}    
"""

    @classmethod
    def setup_class(cls):
        # mock user
        cls.icpper = cls.create_icpper_user()
        cls.user_1 = cls.create_normal_user('test_user_1')
        cls.user_2 = cls.create_normal_user('test_user_2')
        cls.user_3 = cls.create_normal_user('test_user_3')
        cls.user_4 = cls.create_normal_user('test_user_4')

    def test_update_follow(self, dao_name='test_dao_1'):
        ret = self.graph_query(self.icpper.id, self.create_dao % dao_name)
        dao_id = ret.json()['data']['createDao']['dao']['id']

        ret = self.graph_query(self.icpper.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 400
        assert ret.json()['errors'][0]['message'] == 'error.common.not_permission'

        ret = self.graph_query(self.user_1.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 200
        assert ret.json()['data']['updateDaoFollow']['ok']

        ret = self.graph_query(self.user_1.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 400
        assert ret.json()['errors'][0]['message'] == 'NOT RIGHT UPDATE FOLLOW'

        ret = self.graph_query(self.user_1.id, self.update_follow % (
            dao_id, 'DELETE'
        ))
        assert ret.status_code == 200
        assert ret.json()['data']['updateDaoFollow']['ok']

        ret = self.graph_query(self.user_2.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 200
        assert ret.json()['data']['updateDaoFollow']['ok']

        ret = self.graph_query(self.user_3.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 200
        assert ret.json()['data']['updateDaoFollow']['ok']

        ret = self.graph_query(self.user_4.id, self.update_follow % (
            dao_id, 'ADD'
        ))
        assert ret.status_code == 200
        assert ret.json()['data']['updateDaoFollow']['ok']

        return dao_id

    def test_query_follow(self):
        dao_id = self.test_update_follow('test_dao_2')
        # everybody can query follow total
        # owner query all follower
        ret = self.graph_query(self.icpper.id, self.query_dao_follow % (
            dao_id, ''
        ))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['following']['total'] == 3
        assert len(data['data']['dao']['following']['followers']) == 3

        # owner query follow by userid
        ret = self.graph_query(self.icpper.id, self.query_dao_follow % (
            dao_id, f'(userId: "{str(self.user_1.id)}")'
        ))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['following']['total'] == 3
        assert len(data['data']['dao']['following']['followers']) == 1
        assert data['data']['dao']['following']['followers'][0] is None
        ret = self.graph_query(self.icpper.id, self.query_dao_follow % (
            dao_id, f'(userId: "{str(self.user_2.id)}")'
        ))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['following']['total'] == 3
        assert len(data['data']['dao']['following']['followers']) == 1
        assert data['data']['dao']['following']['followers'][0]['userId'] == str(self.user_2.id)
        # user only can query self follow
        ret = self.graph_query(self.user_1.id, self.query_dao_follow % (
            dao_id, f'(userId: "{str(self.user_2.id)}")'
        ))
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NOT RIGHT OWNER ACCESS'

        ret = self.graph_query(self.user_2.id, self.query_dao_follow % (
            dao_id, f'(userId: "{str(self.user_2.id)}")'
        ))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['following']['total'] == 3
        assert len(data['data']['dao']['following']['followers']) == 1
        assert data['data']['dao']['following']['followers'][0]['userId'] == str(self.user_2.id)


