import json

import responses

from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.github_app_token import GithubAppToken
from tests.base import Base


class TestOpenGithub(Base):
    query_issue_info = """
query {
  openGithub(daoId: "%s", way: ISSUE_INFO, parameter: ["mockrepo", "1"]) {
    way
    data
  }
}    
"""
    query_open_pr = """
query {
  openGithub(daoId: "%s", way: OPEN_PR, parameter: ["test_github_login"]) {
    way
    data
  }
}    
"""
    query_issue_timeline = """
query {
  openGithub(daoId: "%s", way: ISSUE_TIMELINE, parameter: ["mockrepo", "1"]) {
    way
    data
  }
}    
"""

    @responses.activate
    def test_issue_info(self):
        user = self.create_icpper_user()
        responses.add(
            responses.GET,
            "https://api.github.com/repos/mockdao/mockrepo/issues/1",
            json={"user": {"login": "mockicpper", "id": 1}, "state": "open",
                  "title": "xxx", "body": "xxx"}
        )
        mockdao = DAO(
            name='mockdao', owner_id=str(user.id),
            github_owner_id=1,
            github_owner_name='mockdao'
        ).save()
        GithubAppToken(
            github_owner_id=1,
            token='x',
            expires_at=99999999999
        ).save()
        ret = self.graph_query(str(user.id), self.query_issue_info % str(mockdao.id))
        data = ret.json()['data']['openGithub']['data']
        assert json.loads(data)['user']['login'] == 'mockicpper'
