import os

from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.user import User, UserStatus
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

    update_dao_info = """
mutation {
  updateDaoBaseInfo(id: "%s", %s) {
    dao {
       id
       name
       desc
       logo
       updateAt
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
        cls.pre_icpper = cls.create_pre_icpper_user()
        Icppership(
            progress=IcppershipProgress.ACCEPT.value,
            status=IcppershipStatus.PRE_ICPPER.value,
            icpper_github_login=str(cls.pre_icpper.github_login),
            mentor_user_id=str(cls.icpper.id),
            icpper_user_id=str(cls.pre_icpper.id)
        ).save()

    def test_create_dao(self):
        dao_name='test_dao_1'
        ret = self.graph_query(self.user_1.id, self.create_dao % dao_name)
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]['message'] == 'NO ROLE'

        ret = self.graph_query(self.icpper.id, self.create_dao % dao_name)
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['createDao']['dao']['name'] == dao_name
        assert data['data']['createDao']['dao']['logo'] == dao_name
        assert data['data']['createDao']['dao']['ownerId'] == str(self.icpper.id)
        return data['data']['createDao']['dao']['id']

    def test_pre_icpper_create_dao(self):
        dao_name ='test_pre_icpper_create_dao'
        ret = self.graph_query(self.pre_icpper.id, self.create_dao % dao_name)
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['createDao']['dao']['name'] == dao_name
        assert data['data']['createDao']['dao']['ownerId'] == str(self.pre_icpper.id)

        pre_icpper = User.objects(id=str(self.pre_icpper.id)).first()
        icppership = Icppership.objects(icpper_github_login=str(self.pre_icpper.github_login)).first()
        assert pre_icpper.status == UserStatus.ICPPER.value
        assert icppership.progress == IcppershipProgress.ICPPER.value
        assert icppership.status == IcppershipStatus.ICPPER.value

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
        assert data['data']['dao']['datum']['id']

        ret = self.graph_query(self.icpper.id, self.query_dao % (dao_id))
        assert ret.status_code == 200

    def test_query_dao_without_login(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_21'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query_no_login(self.query_dao % (dao_id))
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['dao']['datum']['name'] == 'test_dao_21'
        assert data['data']['dao']['datum']['ownerId'] == str(self.icpper.id)
        assert data['data']['dao']['datum']['id']


    def test_update_dao_base_info(self):
        dao_id = self.graph_query(
            self.icpper.id, self.create_dao % 'test_dao_3'
        ).json()['data']['createDao']['dao']['id']
        ret = self.graph_query(
            self.user_1.id, self.update_dao_info % (
                dao_id, 'desc: "xxx"')
        )
        assert ret.status_code == 400
        data = ret.json()
        assert data['errors'][0]["message"] == 'NOT RIGHT OWNER ACCESS'
        ret = self.graph_query(
            self.icpper.id, self.update_dao_info % (
                dao_id, 'desc: "xxx"')
        )
        assert ret.status_code == 200
        data = ret.json()
        assert data['data']['updateDaoBaseInfo']['dao']['desc'] == "xxx"
