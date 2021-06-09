import time
from decimal import Decimal

from app.common.models.icpdao.job import Job, JobStatusEnum, JobPairTypeEnum
from tests.base import Base

from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat, CycleVote, CycleVoteType, VoteResultTypeAll, \
    VoteResultTypeAllResultType


class TestCycles(Base):

    get_cycles = """
query{
    dao(id: "%s"){
        cycles{
            nodes{
                datum{
                    id
                    timeZone
                    beginAt
                    endAt
                    pairBeginAt
                    pairEndAt
                    voteBeginAt
                    voteEndAt
                    isPaired
                    isVoteResultPublished
                    createAt
                    updateAt
                }
            }
        }
    }
}
"""

    get_one_cycle_node = """
    query{
        cycle(id: "%s"){
            datum{
                id
                timeZone
                beginAt
                endAt
                pairBeginAt
                pairEndAt
                voteBeginAt
                voteEndAt
                isPaired
                isVoteResultPublished
                createAt
                updateAt
            }
        }
    }
    """

    get_cycle_icpper_stats_by_owner = """
query{
    cycle(id: "%s"){
        icpperStats{
            total
            nodes{
                datum{
                    userId
                    jobCount
                    size
                    income
                    ei
                    voteEi
                    ownerEi
                }
                icpper{
                    nickname
                    avatar
                }
                lastEi
            }
        }
    }
}
"""

    get_cycle_icpper_stats_params_by_owner = """
query{
    cycle(id: "%s"){
        icpperStats(sorted: jobCount, sortedType: desc){
            total
            nodes{
                datum{
                    userId
                    jobCount
                    size
                    income
                    ei
                    voteEi
                    ownerEi
                }
                icpper{
                    nickname
                    avatar
                }
                lastEi
            }
        }
    }
}
    """

    get_cycle_icpper_stats_params_by_icpper = """
query{
    cycle(id: "%s"){
        icpperStats(sorted: jobCount, sortedType: desc){
            total
            nodes{
                datum{
                    userId
                    jobCount
                    size
                    income
                    ei
                }
                icpper{
                    nickname
                    avatar
                }
                lastEi
            }
        }
    }
}
"""

    get_cycle_job_list = """
query{
    cycle(id: "%s"){
        jobs{
            nodes{
                datum{
                    id
                    userId
                    title
                    size
                    githubRepoOwner
                    githubRepoName
                    githubRepoId
                    githubIssueNumber
                    status
                    income
                    pairType
                    createAt
                    updateAt
                }
                user{
                    nickname
                    avatar
                }
            }
        }
    }
}
"""

    get_cycle_job_list_by_sort = """
    query{
        cycle(id: "%s"){
            jobs(sorted: size){
                nodes{
                    datum{
                        id
                        userId
                        title
                        size
                        githubRepoOwner
                        githubRepoName
                        githubRepoId
                        githubIssueNumber
                        status
                        income
                        pairType
                        createAt
                        updateAt
                    }
                    user{
                        nickname
                        avatar
                    }
                }
            }
        }
    }
    """

    get_cycle_job_list_by_type = """
    query{
        cycle(id: "%s"){
            jobs(pairType: all){
                nodes{
                    datum{
                        id
                        userId
                        title
                        size
                        githubRepoOwner
                        githubRepoName
                        githubRepoId
                        githubIssueNumber
                        status
                        income
                        pairType
                        createAt
                        updateAt
                    }
                    user{
                        nickname
                        avatar
                    }
                }
            }
        }
    }
    """

    get_cycle_vote_list = """
    query{
        cycle(id: "%s"){
            votes{
                nodes{
                    datum{
                        leftJobId
                        rightJobId
                        voteType
                        voteJobId
                        voterId
                        voteResultStatTypeAll
                        isResultPublic
                        createAt
                        updateAt
                    }
                    leftJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
    
                    rightJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voteJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voter{
                        nickname
                    }
                }
            }
        }
    }
    """

    get_cycle_vote_list_is_public = """
    query{
        cycle(id: "%s"){
            votes(isPublic: %s){
                nodes{
                    datum{
                        id
                        leftJobId
                        rightJobId
                        voteType
                        voteJobId
                        voterId
                        voteResultStatTypeAll
                        isResultPublic
                        createAt
                        updateAt
                    }
                    leftJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }

                    rightJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voteJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voter{
                        nickname
                    }
                }
            }
        }
    }
    """


    get_cycle_vote_list_is_myself = """
    query{
        cycle(id: "%s"){
            votes(isMyself: true){
                nodes{
                    datum{
                        id
                        leftJobId
                        rightJobId
                        voteType
                        voteJobId
                        voterId
                        voteResultStatTypeAll
                        isResultPublic
                        createAt
                        updateAt
                    }
                    leftJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }

                    rightJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voteJob{
                        datum{
                            id
                            userId
                            title
                            size
                            githubRepoOwner
                            githubRepoName
                            githubRepoId
                            githubIssueNumber
                            status
                            income
                            pairType
                            createAt
                            updateAt
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voter{
                        nickname
                    }
                }
            }
        }
    }
    """

    get_cycle_vote_list_role = """
    query{
        cycle(id: "%s"){
            votes{
                nodes{
                    datum{
                        id
                        voteJobId
                        voterId
                    }
                    leftJob{
                        datum{
                            id
                        }
                        user{
                            nickname
                            avatar
                        }
                    }

                    rightJob{
                        datum{
                            id
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voteJob{
                        datum{
                            id
                        }
                        user{
                            nickname
                            avatar
                        }
                    }
                    voter{
                        nickname
                    }
                }
            }
        }
    }
    """

    @staticmethod
    def get_cycle_time_by_end_at(end_at):
        begin_at = end_at - 30 * 24 * 60 * 60
        end_at = end_at
        pair_begin_at = end_at + 12 * 60 * 60
        pair_end_at = pair_begin_at + 18 * 60 * 60
        vote_begin_at = pair_end_at
        vote_end_at = vote_begin_at + 18 * 60 * 60

        return begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at

    def test_get_cycles_all(self):
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper.id)
        )
        test_dao.save()

        res = self.graph_query(
            self.icpper.id, self.get_cycles % str(test_dao.id)
        )

        assert len(res.json()['data']['dao']['cycles']['nodes']) == 0

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()

        res = self.graph_query(
            self.icpper.id, self.get_cycles % str(test_dao.id)
        )
        assert len(res.json()['data']['dao']['cycles']['nodes']) == 2
        assert res.json()['data']['dao']['cycles']['nodes'][0]['datum']['beginAt'] == test_cycle_2.begin_at
        assert res.json()['data']['dao']['cycles']['nodes'][1]['datum']['beginAt'] == test_cycle_1.begin_at

    def test_get_one_cycle(self):
        self.__class__.clear_db()
        self.icpper = self.__class__.create_icpper_user()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper.id)
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()

        res = self.graph_query(
            self.icpper.id, self.get_one_cycle_node % str(test_cycle_1.id)
        )

        cycle_node = res.json()['data']['cycle']['datum']
        assert cycle_node['beginAt'] == test_cycle_1.begin_at

    def test_get_cycle_icpper_stats(self):
        self.__class__.clear_db()
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')

        DAO(
            name='test_dao2',
            logo='xxx.png2',
            desc='test_dao_desc2',
            owner_id=str(self.icpper2.id)
        ).save()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper1.id)
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()

        cycle_1_icpper1 = CycleIcpperStat(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_1.id),
            user_id=str(self.icpper1.id),
            job_count=1,
            size=Decimal('10'),
            income=1000,
            vote_ei=1,
            owner_ei=Decimal('0.1'),
            ei=Decimal('1.1')
        )
        cycle_1_icpper1.save()

        time.sleep(1)

        cycle_2_icpper1 = CycleIcpperStat(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_2.id),
            user_id=str(self.icpper1.id),
            job_count=2,
            size=Decimal('5'),
            income=500,
            vote_ei=1,
            owner_ei=Decimal('0.1'),
            ei=Decimal('1.1')
        )
        cycle_2_icpper1.save()

        cycle_2_icpper2 = CycleIcpperStat(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_2.id),
            user_id=str(self.icpper2.id),
            job_count=3,
            size=Decimal('7'),
            income=700,
            vote_ei=1,
            owner_ei=Decimal('0.2'),
            ei=Decimal('1.2')
        )
        cycle_2_icpper2.save()

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_icpper_stats_by_owner % str(test_cycle_1.id)
        )

        icpper_stat_list = res.json()['data']['cycle']['icpperStats']['nodes']

        assert len(icpper_stat_list) == 1

        assert icpper_stat_list[0]['datum']['income'] == 1000
        assert icpper_stat_list[0]['datum']['ei'] is not None
        assert icpper_stat_list[0]['datum']['voteEi'] is not None
        assert icpper_stat_list[0]['datum']['ownerEi'] is not None

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_icpper_stats_params_by_owner % str(test_cycle_2.id)
        )

        icpper_stat_list = res.json()['data']['cycle']['icpperStats']['nodes']
        total = res.json()['data']['cycle']['icpperStats']['total']

        assert len(icpper_stat_list) == 2
        assert total == 2
        assert icpper_stat_list[0]['datum']['jobCount'] == 3
        assert icpper_stat_list[0]['icpper']['nickname'] == 'icpper2'
        assert icpper_stat_list[0]['lastEi'] is None

        assert icpper_stat_list[1]['datum']['jobCount'] == 2
        assert icpper_stat_list[1]['icpper']['nickname'] == 'icpper1'
        assert icpper_stat_list[1]['lastEi'] is not None

        res = self.graph_query(
            self.icpper2.id, self.get_cycle_icpper_stats_params_by_owner % str(test_cycle_2.id)
        )

        icpper_stat_list = res.json()['data']['cycle']['icpperStats']['nodes']
        total = res.json()['data']['cycle']['icpperStats']['total']

        assert icpper_stat_list[0]['datum'] is None

        res = self.graph_query(
            self.icpper2.id, self.get_cycle_icpper_stats_params_by_icpper % str(test_cycle_2.id)
        )

        icpper_stat_list = res.json()['data']['cycle']['icpperStats']['nodes']
        total = res.json()['data']['cycle']['icpperStats']['total']

        assert len(icpper_stat_list) == 2
        assert total == 2
        assert icpper_stat_list[0]['datum']['jobCount'] == 3
        assert icpper_stat_list[0]['icpper']['nickname'] == 'icpper2'
        assert icpper_stat_list[0]['lastEi'] is None

        assert icpper_stat_list[1]['datum']['jobCount'] == 2
        assert icpper_stat_list[1]['icpper']['nickname'] == 'icpper1'
        assert icpper_stat_list[1]['lastEi'] is not None

    def test_get_cycle_job_list(self):
        self.__class__.clear_db()
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')

        DAO(
            name='test_dao2',
            logo='xxx.png2',
            desc='test_dao_desc2',
            owner_id=str(self.icpper2.id)
        ).save()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper1.id)
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()

        job_1 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_title1",
            size=Decimal("1.0"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1,
            status=JobStatusEnum.MERGED.value,
            income=10,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_1.save()

        job_2 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_title2",
            size=Decimal("1.1"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=2,
            github_issue_number=2,
            bot_comment_database_id=2,
            status=JobStatusEnum.MERGED.value,
            income=20,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_2.save()

        job_3 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_title1",
            size=Decimal("1.2"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=3,
            github_issue_number=3,
            bot_comment_database_id=3,
            status=JobStatusEnum.MERGED.value,
            income=30,
            pair_type=JobPairTypeEnum.ALL.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_3.save()

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_job_list % str(test_cycle_2.id)
        )

        job_list = res.json()['data']['cycle']['jobs']['nodes']

        assert len(job_list) == 3

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_job_list_by_sort % str(test_cycle_2.id)
        )

        job_list = res.json()['data']['cycle']['jobs']['nodes']

        assert len(job_list) == 3

        assert job_list[0]['datum']['size'] == 1.0
        assert job_list[1]['datum']['size'] == 1.1
        assert job_list[2]['datum']['size'] == 1.2

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_job_list_by_type % str(test_cycle_2.id)
        )

        job_list = res.json()['data']['cycle']['jobs']['nodes']

        assert len(job_list) == 1

        assert job_list[0]['datum']['size'] == 1.2

    def test_get_cycle_vote_list(self):
        self.__class__.clear_db()
        self.icpper1 = self.__class__.create_icpper_user(nickname='icpper1', github_login='iccper1')
        self.icpper2 = self.__class__.create_icpper_user(nickname='icpper2', github_login='iccper2')
        self.icpper3 = self.__class__.create_icpper_user(nickname='icpper3', github_login='iccper3')

        DAO(
            name='test_dao2',
            logo='xxx.png2',
            desc='test_dao_desc2',
            owner_id=str(self.icpper2.id)
        ).save()

        test_dao = DAO(
            name='test_dao',
            logo='xxx.png',
            desc='test_dao_desc',
            owner_id=str(self.icpper1.id)
        )
        test_dao.save()

        end_at = time.time()
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_2 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_2.save()

        end_at = test_cycle_2.begin_at
        begin_at, end_at, pair_begin_at, pair_end_at, vote_begin_at, vote_end_at = self.get_cycle_time_by_end_at(end_at)
        test_cycle_1 = Cycle(
            dao_id=str(test_dao.id),
            begin_at=begin_at,
            end_at=end_at,
            pair_begin_at=pair_begin_at,
            pair_end_at=pair_end_at,
            vote_begin_at=vote_begin_at,
            vote_end_at=vote_end_at
        )
        test_cycle_1.save()

        job_1 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper1.id),
            title="test_dao_icpper1_title1",
            size=Decimal("1.0"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=1,
            github_issue_number=1,
            bot_comment_database_id=1,
            status=JobStatusEnum.MERGED.value,
            income=10,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_1.save()

        job_2 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_title1",
            size=Decimal("1.1"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=2,
            github_issue_number=2,
            bot_comment_database_id=2,
            status=JobStatusEnum.MERGED.value,
            income=20,
            pair_type=JobPairTypeEnum.PAIR.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_2.save()

        job_3 = Job(
            dao_id=str(test_dao.id),
            user_id=str(self.icpper2.id),
            title="test_dao_icpper2_title2",
            size=Decimal("1.2"),
            github_repo_owner="icpdao",
            github_repo_name="public",
            github_repo_id=3,
            github_issue_number=3,
            bot_comment_database_id=3,
            status=JobStatusEnum.MERGED.value,
            income=30,
            pair_type=JobPairTypeEnum.ALL.value,
            cycle_id=str(test_cycle_2.id)
        )
        job_3.save()

        cycle_vote_1 = CycleVote(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_2.id),
            left_job_id=str(job_1.id),
            right_job_id=str(job_2.id),
            vote_type=CycleVoteType.PAIR.value,
            vote_job_id=str(job_1.id),
            voter_id=str(self.icpper1.id),
            is_result_public=True
        )
        cycle_vote_1.save()

        cycle_vote_2 = CycleVote(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_2.id),
            left_job_id=str(job_3.id),
            right_job_id=str(job_3.id),
            vote_type=CycleVoteType.ALL.value,
            is_result_public=True,
            vote_result_type_all=[
                VoteResultTypeAll(
                    voter_id=str(self.icpper1.id),
                    result=VoteResultTypeAllResultType.YES.value
                ),
                VoteResultTypeAll(
                    voter_id=str(self.icpper2.id),
                    result=VoteResultTypeAllResultType.YES.value
                )
            ],
            vote_result_stat_type_all=100
        )
        cycle_vote_2.save()

        cycle_vote_3 = CycleVote(
            dao_id=str(test_dao.id),
            cycle_id=str(test_cycle_2.id),
            left_job_id=str(job_2.id),
            right_job_id=str(job_1.id),
            vote_type=CycleVoteType.PAIR.value,
            vote_job_id=str(job_1.id),
            voter_id=str(self.icpper2.id),
            is_result_public=False
        )
        cycle_vote_3.save()

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_job_list % str(test_cycle_2.id)
        )

        job_list = res.json()['data']['cycle']['jobs']['nodes']

        assert len(job_list) == 3

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_job_list_by_sort % str(test_cycle_2.id)
        )

        job_list = res.json()['data']['cycle']['jobs']['nodes']

        assert len(job_list) == 3

        assert job_list[0]['datum']['size'] == 1.0
        assert job_list[1]['datum']['size'] == 1.1
        assert job_list[2]['datum']['size'] == 1.2

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list % str(test_cycle_2.id)
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 3

        assert votes_list[0]['datum']['leftJobId'] == str(job_1.id)
        assert votes_list[0]['datum']['rightJobId'] == str(job_2.id)
        assert votes_list[0]['datum']['voteJobId'] == str(job_1.id)
        assert votes_list[0]['datum']['voterId'] == str(self.icpper1.id)

        assert votes_list[0]['leftJob']['datum']['id'] == str(job_1.id)
        assert votes_list[0]['rightJob']['datum']['id'] == str(job_2.id)
        assert votes_list[0]['voter']['nickname'] == str(self.icpper1.nickname)

        assert votes_list[1]['datum']['leftJobId'] == str(job_3.id)
        assert votes_list[1]['datum']['rightJobId'] == str(job_3.id)
        assert votes_list[1]['datum']['voteJobId'] is None
        assert votes_list[1]['datum']['voterId'] is None
        assert votes_list[1]['datum']['voteResultStatTypeAll'] == 100

        assert votes_list[1]['leftJob']['datum']['id'] == str(job_3.id)
        assert votes_list[1]['rightJob']['datum']['id'] == str(job_3.id)
        assert votes_list[1]['voter'] is None

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_is_public % (str(test_cycle_2.id), "true")
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 2

        assert votes_list[0]['datum']['id'] == str(cycle_vote_1.id)
        assert votes_list[1]['datum']['id'] == str(cycle_vote_2.id)

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_is_public % (str(test_cycle_2.id), "false")
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 1

        assert votes_list[0]['datum']['id'] == str(cycle_vote_3.id)

        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_is_myself % str(test_cycle_2.id)
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 2

        id_list = [votes_list[0]['datum']['id'], votes_list[1]['datum']['id']]

        assert str(cycle_vote_1.id) in id_list
        assert str(cycle_vote_2.id) in id_list

        # owner role
        res = self.graph_query(
            self.icpper1.id, self.get_cycle_vote_list_role % str(test_cycle_2.id)
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 3

        assert votes_list[0]['datum']['id'] == str(cycle_vote_1.id)
        assert votes_list[0]['datum']['voteJobId'] == str(job_1.id)
        assert votes_list[0]['datum']['voterId'] == str(self.icpper1.id)
        assert votes_list[0]['voteJob']['datum']['id'] == str(job_1.id)
        assert votes_list[0]['voter']['nickname'] == str(self.icpper1.nickname)

        assert votes_list[1]['datum']['id'] == str(cycle_vote_2.id)
        assert votes_list[1]['datum']['voteJobId'] is None
        assert votes_list[1]['datum']['voterId'] is None

        assert votes_list[2]['datum']['id'] == str(cycle_vote_3.id)
        assert votes_list[2]['datum']['voteJobId'] is None
        assert votes_list[2]['datum']['voterId'] == str(self.icpper2.id)
        assert votes_list[2]['voteJob'] is None
        assert votes_list[2]['voter']['nickname'] == str(self.icpper2.nickname)

        # icpper3 role
        res = self.graph_query(
            self.icpper3.id, self.get_cycle_vote_list_role % str(test_cycle_2.id)
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 3

        assert votes_list[0]['datum']['id'] == str(cycle_vote_1.id)
        assert votes_list[0]['datum']['voteJobId'] == str(job_1.id)
        assert votes_list[0]['datum']['voterId'] == str(self.icpper1.id)
        assert votes_list[0]['voteJob']['datum']['id'] == str(job_1.id)
        assert votes_list[0]['voter']['nickname'] == str(self.icpper1.nickname)

        assert votes_list[1]['datum']['id'] == str(cycle_vote_2.id)
        assert votes_list[1]['datum']['voteJobId'] is None
        assert votes_list[1]['datum']['voterId'] is None

        assert votes_list[2]['datum']['id'] == str(cycle_vote_3.id)
        assert votes_list[2]['datum']['voteJobId'] is None
        assert votes_list[2]['datum']['voterId'] is None
        assert votes_list[2]['voteJob'] is None
        assert votes_list[2]['voter'] is None

        # icpper2 role
        res = self.graph_query(
            self.icpper2.id, self.get_cycle_vote_list_role % str(test_cycle_2.id)
        )

        votes_list = res.json()['data']['cycle']['votes']['nodes']
        assert len(votes_list) == 3

        assert votes_list[0]['datum']['id'] == str(cycle_vote_1.id)
        assert votes_list[0]['datum']['voteJobId'] == str(job_1.id)
        assert votes_list[0]['datum']['voterId'] == str(self.icpper1.id)
        assert votes_list[0]['voteJob']['datum']['id'] == str(job_1.id)
        assert votes_list[0]['voter']['nickname'] == str(self.icpper1.nickname)

        assert votes_list[1]['datum']['id'] == str(cycle_vote_2.id)
        assert votes_list[1]['datum']['voteJobId'] is None
        assert votes_list[1]['datum']['voterId'] is None

        assert votes_list[2]['datum']['id'] == str(cycle_vote_3.id)
        assert votes_list[2]['datum']['voteJobId'] == str(job_1.id)
        assert votes_list[2]['datum']['voterId'] == str(self.icpper2.id)
        assert votes_list[2]['voteJob']['datum']['id'] == str(job_1.id)
        assert votes_list[2]['voter']['nickname'] == str(self.icpper2.nickname)