import decimal
import os
import time

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.dao import DAO
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum
from app.routes.token_mint_records import SystemUser
from tests.base import Base


class TestTokenMintRecord(Base):
    # 支持按照 status 查询
    # 支持按照 chain_id 查询
    query_mint_record_list = """
query{
    dao(id: "%s"){
        tokenMintRecords(first: %s, offset: 0){
            nodes{
                datum{
                    id
                    daoId
                    tokenContractAddress
                    status
                    totalRealSize
                    createAt
                    updateAt
                }
            }
        }
    }
}
"""

    query_init_mint_record_list = """
    query{
        dao(id: "%s"){
            tokenMintRecords(status: [INIT], first: %s, offset: 0){
                nodes{
                    datum{
                        id
                        daoId
                        tokenContractAddress
                        status
                        totalRealSize
                        createAt
                        updateAt
                    }
                }
            }
        }
    }
    """

    query_chain_id_mint_record_list = """
    query{
        dao(id: "%s"){
            tokenMintRecords(chainId: "1", first: %s, offset: 0){
                nodes{
                    datum{
                        id
                        daoId
                        tokenContractAddress
                        status
                        totalRealSize
                        createAt
                        updateAt
                    }
                }
            }
        }
    }
    """

    query_chain_id_and_address_mint_record_list = """
    query{
        dao(id: "%s"){
            tokenMintRecords(tokenContractAddress: "%s", chainId: "1", first: %s, offset: 0){
                nodes{
                    datum{
                        id
                        daoId
                        tokenContractAddress
                        status
                        totalRealSize
                        createAt
                        updateAt
                    }
                }
            }
        }
    }
    """

    query_mint_split_infos = """
    query{
        dao(id: "%s"){
            tokenMintSplitInfo(startCycleId: "%s", endCycleId: "%s"){
                splitInfos{
                    userId
                    userNickname
                    userGithubLogin
                    userAvatar
                    userErc20Address
                    ratio
                }
            }
        }
    }
    """

    create_token_mint_record = """
mutation {
  createTokenMintRecord(daoId: "%s", startCycleId: "%s", endCycleId: "%s", tokenContractAddress: "%s", startTimestamp: %s, endTimestamp: %s, tickLower: %s, tickUpper: %s, chainId: "%s", tokenSymbol: "TEST") {
    tokenMintRecord {
        id
        daoId
        tokenContractAddress
        status
        mintTxHash
        totalRealSize
        createAt
        updateAt
    }
  }
}
"""

    link_tx_hash_for_token_mint_record = """
mutation {
    linkTxHashForTokenMintRecord(id: "%s", mintTxHash: "%s") {
        tokenMintRecord {
            id
            daoId
            tokenContractAddress
            status
            mintTxHash
            totalRealSize
            createAt
            updateAt
        }
    }
}
    """

    drop_token_mint_record = """
    mutation {
        dropTokenMintRecord(id: "%s") {
            ok
        }
    }
        """

    sync_token_mint_record_event = """
    mutation {
        syncTokenMintRecordEvent(id: "%s") {
            ok
        }
    }
"""

    def test_query_list(self):
        self.__class__.clear_db()
        self.icpper = self.create_icpper_user()

        self.mock_dao_1 = DAO(
            name="dao_1",
            owner_id=str(self.icpper.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()
        self.mock_dao_2 = DAO(
            name="dao_2",
            owner_id=str(self.icpper.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"
        self.icpper_address = "0x99c85bb64564d9ef9a99621301f22c9993cb89e3"

        for number in range(1, 31):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao_1.id),
                chain_id="1",
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                tick_lower=0,
                tick_upper=1
            ).save()
        for number in range(1, 31):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao_2.id),
                chain_id="1",
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                tick_lower=0,
                tick_upper=1
            ).save()

        ret = self.graph_query(self.icpper.id, self.query_mint_record_list % (str(self.mock_dao_1.id), 2))
        res = ret.json()
        res_records = res['data']['dao']['tokenMintRecords']['nodes']
        assert len(res_records) == 2
        assert res_records[0]['datum']['daoId'] == str(self.mock_dao_1.id)
        assert res_records[0]['datum']['totalRealSize'] == decimal.Decimal('30')
        assert res_records[1]['datum']['daoId'] == str(self.mock_dao_1.id)
        assert res_records[1]['datum']['totalRealSize'] == decimal.Decimal('29')

    def test_query_init_list(self):
        self.__class__.clear_db()
        self.icpper = self.create_icpper_user()

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.icpper.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"
        self.icpper_address = "0x99c85bb64564d9ef9a99621301f22c9993cb89e3"

        for number in range(1, 4):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                chain_id="1",
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                tick_lower=0,
                tick_upper=1
            ).save()
        for number in range(4, 7):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                chain_id="1",
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                status=MintRecordStatusEnum.SUCCESS.value,
                tick_lower=0,
                tick_upper=1
            ).save()

        ret = self.graph_query(self.icpper.id, self.query_init_mint_record_list % (str(self.mock_dao.id), 2))
        res = ret.json()
        res_records = res['data']['dao']['tokenMintRecords']['nodes']
        assert len(res_records) == 2
        assert res_records[0]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[0]['datum']['totalRealSize'] == decimal.Decimal('3')
        assert res_records[1]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[1]['datum']['totalRealSize'] == decimal.Decimal('2')

    def test_query_chain_id_list(self):
        self.__class__.clear_db()
        self.icpper = self.create_icpper_user()

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.icpper.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"
        self.icpper_address = "0x99c85bb64564d9ef9a99621301f22c9993cb89e3"

        for number in range(2, 5):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                chain_id="1",
                end_timestamp=number,
                tick_lower=0,
                tick_upper=1
            ).save()
        for number in range(5, 8):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                token_contract_address=self.token_contract_address,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                chain_id="2",
                tick_lower=0,
                tick_upper=1
            ).save()

        ret = self.graph_query(self.icpper.id, self.query_chain_id_mint_record_list % (str(self.mock_dao.id), 2))
        res = ret.json()
        res_records = res['data']['dao']['tokenMintRecords']['nodes']
        assert len(res_records) == 2
        assert res_records[0]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[0]['datum']['totalRealSize'] == decimal.Decimal('4')
        assert res_records[1]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[1]['datum']['totalRealSize'] == decimal.Decimal('3')


    def test_query_chain_id_and_address_list(self):
        self.__class__.clear_db()
        self.icpper = self.create_icpper_user()

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.icpper.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        self.token_contract_address_1 = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"
        self.token_contract_address_2 = "0x1678630024a158dC505db2d967B4B0e58830D54F"
        self.icpper_address = "0x99c85bb64564d9ef9a99621301f22c9993cb89e3"

        for number in range(2, 5):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                token_contract_address=self.token_contract_address_1,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                chain_id="1",
                end_timestamp=number,
                tick_lower=0,
                tick_upper=1
            ).save()
        for number in range(5, 8):
            TokenMintRecord(
                token_symbol="TEST",
                dao_id=str(self.mock_dao.id),
                token_contract_address=self.token_contract_address_2,
                total_real_size=decimal.Decimal(str(number)),
                mint_token_address_list=[self.icpper_address],
                mint_token_amount_ratio_list=[100],
                start_timestamp=number-1,
                end_timestamp=number,
                chain_id="1",
                tick_lower=0,
                tick_upper=1
            ).save()

        ret = self.graph_query(self.icpper.id, self.query_chain_id_and_address_mint_record_list % (str(self.mock_dao.id), self.token_contract_address_1, 2))
        res = ret.json()
        res_records = res['data']['dao']['tokenMintRecords']['nodes']
        assert len(res_records) == 2
        assert res_records[0]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[0]['datum']['totalRealSize'] == decimal.Decimal('4')
        assert res_records[1]['datum']['daoId'] == str(self.mock_dao.id)
        assert res_records[1]['datum']['totalRealSize'] == decimal.Decimal('3')

    def _link_icpper_mentor(self, mentor, icpper):
        Icppership(
            progress=IcppershipProgress.ACCEPT.value,
            status=IcppershipStatus.ICPPER.value,
            icpper_github_login=icpper.github_login,
            mentor_user_id=str(mentor.id),
            icpper_user_id=str(icpper.id),
            accept_at=0,
            icpper_at=0
        ).save()

    def test_query_mint_split_infos(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        ret = self.graph_query(self.job_user_1_mentor_7.id, self.query_mint_split_infos % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id))
        res = ret.json()
        split_infos = res["data"]["dao"]["tokenMintSplitInfo"]["splitInfos"]

        assert split_infos[0]["userId"] == str(self.job_user_1.id)
        assert split_infos[1]["userId"] == str(self.job_user_2.id)
        assert split_infos[2]["userId"] == str(self.job_user_3.id)

        assert split_infos[3]["userId"] == str(self.job_user_1_mentor_1.id)
        assert split_infos[4]["userId"] == str(self.job_user_1_mentor_2.id)
        assert split_infos[5]["userId"] == str(self.job_user_1_mentor_3.id)
        assert split_infos[6]["userId"] == str(self.job_user_1_mentor_4.id)
        assert split_infos[7]["userId"] == str(self.job_user_1_mentor_6.id)
        assert split_infos[8]["userId"] == str(self.job_user_1_mentor_7.id)

        assert split_infos[9]["userId"] == str(self.job_user_2_mentor_1.id)
        assert split_infos[10]["userId"] == str(self.job_user_2_mentor_2.id)
        assert split_infos[11]["userId"] == SystemUser.id

        assert split_infos[0]["ratio"] == 3420000  # 360 * 100 * 95
        assert split_infos[1]["ratio"] == 3372500  # 355 * 100 * 95
        assert split_infos[2]["ratio"] == 4185400  # 440 * 100 * 95 + 360 * 5 * 3

        assert split_infos[3]["ratio"] == 90000  # 360 * 5 * 50
        assert split_infos[4]["ratio"] == 45000  # 360 * 5 * 25
        assert split_infos[5]["ratio"] == 23400  # 360 * 5 * 13
        assert split_infos[6]["ratio"] == 10800  # 360 * 5 * 6
        assert split_infos[7]["ratio"] == 113600 # 360 * 5 * 2 + 440 * 5 * 50
        assert split_infos[8]["ratio"] == 56800  # 360 * 5 * 1 + 440 * 5 * 25

        assert split_infos[9]["ratio"] == 88750  # 355 * 5 * 50
        assert split_infos[10]["ratio"] == 44375  # 355 * 5 * 25
        assert split_infos[11]["ratio"] == 99375  #  355 * 5 * 25 + 440 * 5 * 25

    def test_create_token_mint_record(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')
        self.job_user_4 = self.create_icpper_user(nickname='job_user_4', github_login='job_user_4')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_4.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('0'),
            vote_ei=0,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('0.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.create_token_mint_record % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id, self.token_contract_address, begin_at_1, end_at_2, 0, 1000, "1")
        )
        res = ret.json()["data"]["createTokenMintRecord"]["tokenMintRecord"]
        assert res["daoId"] == str(self.mock_dao.id)
        assert res["totalRealSize"] == decimal.Decimal("115.5")

        record = TokenMintRecord.objects().first()
        assert len(record.mint_token_address_list) == 12
        assert record.mint_token_address_list == [
            self.job_user_1.erc20_address,
            self.job_user_2.erc20_address,
            self.job_user_3.erc20_address,
            self.job_user_1_mentor_1.erc20_address,
            self.job_user_1_mentor_2.erc20_address,
            self.job_user_1_mentor_3.erc20_address,
            self.job_user_1_mentor_4.erc20_address,
            self.job_user_1_mentor_6.erc20_address,
            self.job_user_1_mentor_7.erc20_address,
            self.job_user_2_mentor_1.erc20_address,
            self.job_user_2_mentor_2.erc20_address,
            SystemUser.erc20_address,
        ]

        assert record.mint_token_amount_ratio_list == [
            3420000,
            3372500,
            4185400,
            90000,
            45000,
            23400,
            10800,
            113600,
            56800,
            88750,
            44375,
            99375,
        ]

        assert len(record.mint_icpper_records) == 3

        assert record.mint_icpper_records[0].user_id == str(self.job_user_1.id)
        assert record.mint_icpper_records[0].user_eth_address == str(self.job_user_1.erc20_address)
        assert record.mint_icpper_records[0].user_ratio == 3420000
        assert len(record.mint_icpper_records[0].mentor_list) == 7

        assert record.mint_icpper_records[0].mentor_list[0].mentor_id == str(self.job_user_1_mentor_1.id)
        assert record.mint_icpper_records[0].mentor_list[0].mentor_eth_address == self.job_user_1_mentor_1.erc20_address
        assert record.mint_icpper_records[0].mentor_list[0].mentor_radio == 90000

        assert record.mint_icpper_records[0].mentor_list[1].mentor_id == str(self.job_user_1_mentor_2.id)
        assert record.mint_icpper_records[0].mentor_list[1].mentor_eth_address == self.job_user_1_mentor_2.erc20_address
        assert record.mint_icpper_records[0].mentor_list[1].mentor_radio == 45000

        assert record.mint_icpper_records[0].mentor_list[2].mentor_id == str(self.job_user_1_mentor_3.id)
        assert record.mint_icpper_records[0].mentor_list[2].mentor_eth_address == self.job_user_1_mentor_3.erc20_address
        assert record.mint_icpper_records[0].mentor_list[2].mentor_radio == 23400

        assert record.mint_icpper_records[0].mentor_list[3].mentor_id == str(self.job_user_1_mentor_4.id)
        assert record.mint_icpper_records[0].mentor_list[3].mentor_eth_address == self.job_user_1_mentor_4.erc20_address
        assert record.mint_icpper_records[0].mentor_list[3].mentor_radio == 10800

        assert record.mint_icpper_records[0].mentor_list[4].mentor_id == str(self.job_user_3.id)
        assert record.mint_icpper_records[0].mentor_list[4].mentor_eth_address == self.job_user_3.erc20_address
        assert record.mint_icpper_records[0].mentor_list[4].mentor_radio == 5400

        assert record.mint_icpper_records[0].mentor_list[5].mentor_id == str(self.job_user_1_mentor_6.id)
        assert record.mint_icpper_records[0].mentor_list[5].mentor_eth_address == self.job_user_1_mentor_6.erc20_address
        assert record.mint_icpper_records[0].mentor_list[5].mentor_radio == 3600

        assert record.mint_icpper_records[0].mentor_list[6].mentor_id == str(self.job_user_1_mentor_7.id)
        assert record.mint_icpper_records[0].mentor_list[6].mentor_eth_address == self.job_user_1_mentor_7.erc20_address
        assert record.mint_icpper_records[0].mentor_list[6].mentor_radio == 1800

        assert record.mint_icpper_records[1].user_id == str(self.job_user_2.id)
        assert record.mint_icpper_records[1].user_eth_address == str(self.job_user_2.erc20_address)
        assert record.mint_icpper_records[1].user_ratio == 3372500
        assert len(record.mint_icpper_records[1].mentor_list) == 2

        assert record.mint_icpper_records[1].mentor_list[0].mentor_id == str(self.job_user_2_mentor_1.id)
        assert record.mint_icpper_records[1].mentor_list[0].mentor_eth_address == self.job_user_2_mentor_1.erc20_address
        assert record.mint_icpper_records[1].mentor_list[0].mentor_radio == 88750

        assert record.mint_icpper_records[1].mentor_list[1].mentor_id == str(self.job_user_2_mentor_2.id)
        assert record.mint_icpper_records[1].mentor_list[1].mentor_eth_address == self.job_user_2_mentor_2.erc20_address
        assert record.mint_icpper_records[1].mentor_list[1].mentor_radio == 44375

        assert record.mint_icpper_records[2].user_id == str(self.job_user_3.id)
        assert record.mint_icpper_records[2].user_eth_address == str(self.job_user_3.erc20_address)
        assert record.mint_icpper_records[2].user_ratio == 4180000
        assert len(record.mint_icpper_records[2].mentor_list) == 2

        assert record.mint_icpper_records[2].mentor_list[0].mentor_id == str(self.job_user_1_mentor_6.id)
        assert record.mint_icpper_records[2].mentor_list[0].mentor_eth_address == self.job_user_1_mentor_6.erc20_address
        assert record.mint_icpper_records[2].mentor_list[0].mentor_radio == 110000

        assert record.mint_icpper_records[2].mentor_list[1].mentor_id == str(self.job_user_1_mentor_7.id)
        assert record.mint_icpper_records[2].mentor_list[1].mentor_eth_address == self.job_user_1_mentor_7.erc20_address
        assert record.mint_icpper_records[2].mentor_list[1].mentor_radio == 55000

    def test_query_mint_split_infos_have_no_erc20_address_mentor(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6', have_erc20_address=False)
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        ret = self.graph_query(self.job_user_1_mentor_7.id, self.query_mint_split_infos % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id))
        res = ret.json()
        split_infos = res["data"]["dao"]["tokenMintSplitInfo"]["splitInfos"]

        assert len(split_infos) == 11

        assert split_infos[0]["userId"] == str(self.job_user_1.id)
        assert split_infos[1]["userId"] == str(self.job_user_2.id)
        assert split_infos[2]["userId"] == str(self.job_user_3.id)

        assert split_infos[3]["userId"] == str(self.job_user_1_mentor_1.id)
        assert split_infos[4]["userId"] == str(self.job_user_1_mentor_2.id)
        assert split_infos[5]["userId"] == str(self.job_user_1_mentor_3.id)
        assert split_infos[6]["userId"] == str(self.job_user_1_mentor_4.id)
        assert split_infos[7]["userId"] == str(self.job_user_1_mentor_7.id)

        assert split_infos[8]["userId"] == str(self.job_user_2_mentor_1.id)
        assert split_infos[9]["userId"] == str(self.job_user_2_mentor_2.id)
        assert split_infos[10]["userId"] == SystemUser.id

        assert split_infos[0]["ratio"] == 3420000  # 360 * 100 * 95
        assert split_infos[1]["ratio"] == 3372500  # 355 * 100 * 95
        assert split_infos[2]["ratio"] == 4185400  # 440 * 100 * 95 + 360 * 5 * 3

        assert split_infos[3]["ratio"] == 90000  # 360 * 5 * 50
        assert split_infos[4]["ratio"] == 45000  # 360 * 5 * 25
        assert split_infos[5]["ratio"] == 23400  # 360 * 5 * 13
        assert split_infos[6]["ratio"] == 10800  # 360 * 5 * 6
        # 360 * 5 * 2 + 440 * 5 * 50 no erc20_address_mentor
        assert split_infos[7]["ratio"] == 56800  # 360 * 5 * 1 + 440 * 5 * 25

        assert split_infos[8]["ratio"] == 88750  # 355 * 5 * 50
        assert split_infos[9]["ratio"] == 44375  # 355 * 5 * 25
        assert split_infos[10]["ratio"] == 99375 + 113600  #  355 * 5 * 25 + 440 * 5 * 25 and (360 * 5 * 2 + 440 * 5 * 50)

    def test_create_token_mint_record_have_no_erc20_address_mentor(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2', have_erc20_address=False)

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.create_token_mint_record % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id, self.token_contract_address, begin_at_1, end_at_2, 0, 1000, "1")
        )
        res = ret.json()["data"]["createTokenMintRecord"]["tokenMintRecord"]
        assert res["daoId"] == str(self.mock_dao.id)
        assert res["totalRealSize"] == decimal.Decimal("115.5")

        record = TokenMintRecord.objects().first()
        assert record.mint_token_address_list == [
            self.job_user_1.erc20_address,
            self.job_user_2.erc20_address,
            self.job_user_3.erc20_address,
            self.job_user_1_mentor_1.erc20_address,
            self.job_user_1_mentor_2.erc20_address,
            self.job_user_1_mentor_3.erc20_address,
            self.job_user_1_mentor_4.erc20_address,
            self.job_user_1_mentor_6.erc20_address,
            self.job_user_1_mentor_7.erc20_address,
            self.job_user_2_mentor_1.erc20_address,
            SystemUser.erc20_address,
        ]

        assert record.mint_token_amount_ratio_list == [
            3420000,
            3372500,
            4185400,
            90000,
            45000,
            23400,
            10800,
            113600,
            56800,
            88750,
            99375 + 44375,
        ]

        assert len(record.mint_icpper_records) == 3

        assert record.mint_icpper_records[0].user_id == str(self.job_user_1.id)
        assert record.mint_icpper_records[0].user_eth_address == str(self.job_user_1.erc20_address)
        assert record.mint_icpper_records[0].user_ratio == 3420000
        assert len(record.mint_icpper_records[0].mentor_list) == 7

        assert record.mint_icpper_records[0].mentor_list[0].mentor_id == str(self.job_user_1_mentor_1.id)
        assert record.mint_icpper_records[0].mentor_list[0].mentor_eth_address == self.job_user_1_mentor_1.erc20_address
        assert record.mint_icpper_records[0].mentor_list[0].mentor_radio == 90000

        assert record.mint_icpper_records[0].mentor_list[1].mentor_id == str(self.job_user_1_mentor_2.id)
        assert record.mint_icpper_records[0].mentor_list[1].mentor_eth_address == self.job_user_1_mentor_2.erc20_address
        assert record.mint_icpper_records[0].mentor_list[1].mentor_radio == 45000

        assert record.mint_icpper_records[0].mentor_list[2].mentor_id == str(self.job_user_1_mentor_3.id)
        assert record.mint_icpper_records[0].mentor_list[2].mentor_eth_address == self.job_user_1_mentor_3.erc20_address
        assert record.mint_icpper_records[0].mentor_list[2].mentor_radio == 23400

        assert record.mint_icpper_records[0].mentor_list[3].mentor_id == str(self.job_user_1_mentor_4.id)
        assert record.mint_icpper_records[0].mentor_list[3].mentor_eth_address == self.job_user_1_mentor_4.erc20_address
        assert record.mint_icpper_records[0].mentor_list[3].mentor_radio == 10800

        assert record.mint_icpper_records[0].mentor_list[4].mentor_id == str(self.job_user_3.id)
        assert record.mint_icpper_records[0].mentor_list[4].mentor_eth_address == self.job_user_3.erc20_address
        assert record.mint_icpper_records[0].mentor_list[4].mentor_radio == 5400

        assert record.mint_icpper_records[0].mentor_list[5].mentor_id == str(self.job_user_1_mentor_6.id)
        assert record.mint_icpper_records[0].mentor_list[5].mentor_eth_address == self.job_user_1_mentor_6.erc20_address
        assert record.mint_icpper_records[0].mentor_list[5].mentor_radio == 3600

        assert record.mint_icpper_records[0].mentor_list[6].mentor_id == str(self.job_user_1_mentor_7.id)
        assert record.mint_icpper_records[0].mentor_list[6].mentor_eth_address == self.job_user_1_mentor_7.erc20_address
        assert record.mint_icpper_records[0].mentor_list[6].mentor_radio == 1800

        assert record.mint_icpper_records[1].user_id == str(self.job_user_2.id)
        assert record.mint_icpper_records[1].user_eth_address == str(self.job_user_2.erc20_address)
        assert record.mint_icpper_records[1].user_ratio == 3372500
        assert len(record.mint_icpper_records[1].mentor_list) == 2

        assert record.mint_icpper_records[1].mentor_list[0].mentor_id == str(self.job_user_2_mentor_1.id)
        assert record.mint_icpper_records[1].mentor_list[0].mentor_eth_address == self.job_user_2_mentor_1.erc20_address
        assert record.mint_icpper_records[1].mentor_list[0].mentor_radio == 88750

        assert record.mint_icpper_records[1].mentor_list[1].mentor_id == str(self.job_user_2_mentor_2.id)
        assert record.mint_icpper_records[1].mentor_list[1].mentor_eth_address == self.job_user_2_mentor_2.erc20_address
        assert record.mint_icpper_records[1].mentor_list[1].mentor_eth_address is None
        assert record.mint_icpper_records[1].mentor_list[1].mentor_radio == 0 # not is 44375

        assert record.mint_icpper_records[2].user_id == str(self.job_user_3.id)
        assert record.mint_icpper_records[2].user_eth_address == str(self.job_user_3.erc20_address)
        assert record.mint_icpper_records[2].user_ratio == 4180000
        assert len(record.mint_icpper_records[2].mentor_list) == 2

        assert record.mint_icpper_records[2].mentor_list[0].mentor_id == str(self.job_user_1_mentor_6.id)
        assert record.mint_icpper_records[2].mentor_list[0].mentor_eth_address == self.job_user_1_mentor_6.erc20_address
        assert record.mint_icpper_records[2].mentor_list[0].mentor_radio == 110000

        assert record.mint_icpper_records[2].mentor_list[1].mentor_id == str(self.job_user_1_mentor_7.id)
        assert record.mint_icpper_records[2].mentor_list[1].mentor_eth_address == self.job_user_1_mentor_7.erc20_address
        assert record.mint_icpper_records[2].mentor_list[1].mentor_radio == 55000

    def test_link_tx_hash_for_token_mint_record(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.create_token_mint_record % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id, self.token_contract_address, begin_at_1, end_at_2, 0, 1000, "1")
        )
        res = ret.json()["data"]["createTokenMintRecord"]["tokenMintRecord"]
        assert res["daoId"] == str(self.mock_dao.id)
        assert res["totalRealSize"] == decimal.Decimal("115.5")

        record_id = res["id"]
        tx_hash = "0xa1b78d0ede1a31897982076331b4dd6f5b36b8206d3039dc0636a13753b05bbd"
        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.link_tx_hash_for_token_mint_record % (record_id, tx_hash)
        )
        res = ret.json()["data"]["linkTxHashForTokenMintRecord"]["tokenMintRecord"]
        assert res["id"] == record_id
        assert res["mintTxHash"] == tx_hash
        assert res["status"] == MintRecordStatusEnum.PENDING.value

    def test_drop_token_mint_record(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.create_token_mint_record % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id, self.token_contract_address, begin_at_1, end_at_2, 0, 1000, "1")
        )
        res = ret.json()["data"]["createTokenMintRecord"]["tokenMintRecord"]
        assert res["daoId"] == str(self.mock_dao.id)
        assert res["totalRealSize"] == decimal.Decimal("115.5")

        record_id = res["id"]
        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.drop_token_mint_record % record_id
        )
        res = ret.json()["data"]["dropTokenMintRecord"]["ok"]
        assert res is True

        record = TokenMintRecord.objects(id=record_id).first()
        assert record.status == MintRecordStatusEnum.DROPED.value

        record.status = MintRecordStatusEnum.PENDING.value
        record.save()

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.drop_token_mint_record % record_id
        )
        res = ret.json()["data"]["dropTokenMintRecord"]["ok"]
        assert res is False

        record = TokenMintRecord.objects(id=record_id).first()
        assert record.status == MintRecordStatusEnum.PENDING.value

    def test_sync_token_mint_record_event(self):
        """
        创建三个有 job 的用户和他们的上级
        创建一个 dao
        创建两个 cycle
        创建多个 cycle_icpper_stat
        """
        self.__class__.clear_db()
        self.job_user_1 = self.create_icpper_user(nickname='job_user_1', github_login='job_user_1')
        self.job_user_2 = self.create_icpper_user(nickname='job_user_2', github_login='job_user_2')
        self.job_user_3 = self.create_icpper_user(nickname='job_user_3', github_login='job_user_3')

        self.job_user_1_mentor_1 = self.create_icpper_user(nickname='job_user_1_mentor_1', github_login='job_user_1_mentor_1')
        self.job_user_1_mentor_2 = self.create_icpper_user(nickname='job_user_1_mentor_2', github_login='job_user_1_mentor_2')
        self.job_user_1_mentor_3 = self.create_icpper_user(nickname='job_user_1_mentor_3', github_login='job_user_1_mentor_3')
        self.job_user_1_mentor_4 = self.create_icpper_user(nickname='job_user_1_mentor_4', github_login='job_user_1_mentor_4')
        self.job_user_1_mentor_5 = self.job_user_3
        self.job_user_1_mentor_6 = self.create_icpper_user(nickname='job_user_1_mentor_6', github_login='job_user_1_mentor_6')
        self.job_user_1_mentor_7 = self.create_icpper_user(nickname='job_user_1_mentor_7', github_login='job_user_1_mentor_7')

        self.job_user_2_mentor_1 = self.create_icpper_user(nickname='job_user_2_mentor_1', github_login='job_user_2_mentor_1')
        self.job_user_2_mentor_2 = self.create_icpper_user(nickname='job_user_2_mentor_2', github_login='job_user_2_mentor_2')

        self._link_icpper_mentor(self.job_user_1_mentor_1, self.job_user_1)
        self._link_icpper_mentor(self.job_user_1_mentor_2, self.job_user_1_mentor_1)
        self._link_icpper_mentor(self.job_user_1_mentor_3, self.job_user_1_mentor_2)
        self._link_icpper_mentor(self.job_user_1_mentor_4, self.job_user_1_mentor_3)
        self._link_icpper_mentor(self.job_user_1_mentor_5, self.job_user_1_mentor_4)
        self._link_icpper_mentor(self.job_user_1_mentor_6, self.job_user_1_mentor_5)
        self._link_icpper_mentor(self.job_user_1_mentor_7, self.job_user_1_mentor_6)

        self._link_icpper_mentor(self.job_user_2_mentor_1, self.job_user_2)
        self._link_icpper_mentor(self.job_user_2_mentor_2, self.job_user_2_mentor_1)

        self.mock_dao = DAO(
            name="dao_name",
            owner_id=str(self.job_user_1_mentor_7.id),
            github_owner_id=1,
            github_owner_name="1"
        ).save()

        begin_at_1 = int(time.time()) - 100 * 24 * 60 * 60
        end_at_1 = begin_at_1 + 30 * 24 * 60 * 60
        begin_at_2 = end_at_1
        end_at_2 = begin_at_2 + 30 * 24 * 60 * 60

        self.mock_cycle_1 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_1,
            end_at=end_at_1,
            pair_begin_at=end_at_1,
            pair_end_at=end_at_1+1,
            vote_begin_at=end_at_1+1,
            vote_end_at=end_at_1+2,
            vote_result_published_at=end_at_1+10
        ).save()

        self.mock_cycle_2 = Cycle(
            dao_id=str(self.mock_dao.id),
            begin_at=begin_at_2,
            end_at=end_at_2,
            pair_begin_at=end_at_2,
            pair_end_at=end_at_2+1,
            vote_begin_at=end_at_2+1,
            vote_end_at=end_at_2+2,
            vote_result_published_at=end_at_2+10
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('19'),
            size=decimal.Decimal('19'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_1.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('21.5'),
            size=decimal.Decimal('21.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_1.id),
            job_count=20,
            job_size=decimal.Decimal('17'),
            size=decimal.Decimal('17'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_2.id),
            job_count=20,
            job_size=decimal.Decimal('18.5'),
            size=decimal.Decimal('18.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()
        CycleIcpperStat(
            dao_id=str(self.mock_dao.id),
            cycle_id=str(self.mock_cycle_2.id),
            user_id=str(self.job_user_3.id),
            job_count=20,
            job_size=decimal.Decimal('22.5'),
            size=decimal.Decimal('22.5'),
            vote_ei=1,
            owner_ei=decimal.Decimal('0.1'),
            ei=decimal.Decimal('1.1')
        ).save()

        self.token_contract_address = "0xb7e390864a90b7b923c9f9310c6f98aafe43f707"

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.create_token_mint_record % (str(self.mock_dao.id), self.mock_cycle_1.id, self.mock_cycle_2.id, self.token_contract_address, begin_at_1, end_at_2, 0, 1000, "1")
        )
        res = ret.json()["data"]["createTokenMintRecord"]["tokenMintRecord"]
        assert res["daoId"] == str(self.mock_dao.id)
        assert res["totalRealSize"] == decimal.Decimal("115.5")

        record_id = res["id"]
        tx_hash = "0xa1b78d0ede1a31897982076331b4dd6f5b36b8206d3039dc0636a13753b05bbd"
        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.link_tx_hash_for_token_mint_record % (record_id, tx_hash)
        )
        res = ret.json()["data"]["linkTxHashForTokenMintRecord"]["tokenMintRecord"]
        assert res["id"] == record_id
        assert res["mintTxHash"] == tx_hash
        assert res["status"] == MintRecordStatusEnum.PENDING.value

        ret = self.graph_query(
            self.job_user_1_mentor_7.id,
            self.sync_token_mint_record_event % (record_id)
        )
        res = ret.json()["data"]["syncTokenMintRecordEvent"]
        assert res["ok"] == True
