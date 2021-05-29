import os

from tests.base import Base

TESTS_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class TestDAOs(Base):
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

    query_dao = """
query {
  dao(id: "%s") {
    datum {
      id
      name
      desc
      logo
      ownerId
    }
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

    def test_create_dao(self):
        dao_name='test_dao_1'
        ret = self.graph_query(self.user_1.id, self.create_dao % dao_name)
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NOT RIGHT ICPPER ACCESS'

        ret = self.graph_query(self.icpper.id, self.create_dao % dao_name)
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['createDao']['dao']['name'] == dao_name
        assert data['data']['createDao']['dao']['logo'] == dao_name
        assert data['data']['createDao']['dao']['ownerId'] == str(self.icpper.id)
        return data['data']['createDao']['dao']['id']

    def test_query_dao(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_2'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query(self.user_1.id, self.query_dao % (dao_id))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['datum']['name'] == 'test_dao_2'
        assert data['data']['dao']['datum']['ownerId'] == str(self.icpper.id)
        return data['data']['dao']['datum']['id']

        ret = self.graph_query(self.icpper.id, self.query_dao % (dao_id))
        assert ret.status_code == 200
