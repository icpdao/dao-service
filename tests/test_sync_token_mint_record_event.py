# import decimal
#
# import web3
#
# from app.common.models.icpdao.cycle import Cycle
# from app.common.models.icpdao.dao import DAO
# from app.common.models.icpdao.token import TokenMintRecord, MintRecordStatusEnum, MintIcpperRecord, MintIcpperRecordMeta
# from app.common.models.icpdao.user import User
# from app.controllers.sync_token_mint_record_event import _update_mentor_income
# from tests.base import Base
# from settings import ICPDAO_ETH_DAOSTAKING_ADDRESS
#
#
# class TestSyncTokenMintRecordEvent(Base):
#     create_mock = """
#     mutation{
#       createMock(ownerGithubUserLogin: "%s", icpperGithubUserLogin: "%s"){
#         ok
#       }
#     }
#     """
#
#     def test_run_task(self):
#         self.__class__.clear_db()
#         self.owner = self.__class__.create_icpper_user(nickname='owner', github_login='owner')
#         self.icpper = self.__class__.create_icpper_user(nickname='icpper', github_login='icpper')
#
#         res = self.graph_query(
#             self.owner.id, self.create_mock % (
#                 self.owner.github_login,
#                 self.icpper.github_login
#             )
#         )
#         print(res.json())
#
#         self.mock_user_1 = User.objects(github_login='mock_user_1').first()
#         self.mock_user_2 = User.objects(github_login='mock_user_2').first()
#         self.mock_user_3 = User.objects(github_login='mock_user_3').first()
#         self.mock_user_4 = User.objects(github_login='mock_user_4').first()
#         self.mock_user_5 = User.objects(github_login='mock_user_5').first()
#         self.mock_user_6 = User.objects(github_login='mock_user_6').first()
#         self.mock_user_7 = User.objects(github_login='mock_user_7').first()
#
#         dao = DAO.objects(name="end-and-mint").first()
#         cycle = Cycle.objects(dao_id=str(dao.id)).order_by("_id").first()
#
#         token_contract_address = web3.Account.create().address
#         token_symbol = "FS"
#         chain_id = "3"
#         start_cycle_id = str(cycle.id)
#         end_cycle_id = str(cycle.id)
#         cycle_ids = [str(cycle.id)]
#
#         mint_icpper_records = []
#         mint_icpper_records.append(MintIcpperRecord(
#             user_id=str(self.owner.id),
#             user_eth_address=self.owner.erc20_address,
#             user_ratio=decimal.Decimal("285000"),
#             mentor_list=[]
#         ))
#         mint_icpper_records.append(MintIcpperRecord(
#             user_id=str(self.icpper.id),
#             user_eth_address=self.icpper.erc20_address,
#             user_ratio=decimal.Decimal("475000"),
#             mentor_list=[MintIcpperRecordMeta(
#                 mentor_id=str(self.owner.id),
#                 mentor_eth_address=self.owner.erc20_address,
#                 mentor_radio=decimal.Decimal("12500"),
#             )]
#         ))
#         mint_icpper_records.append(MintIcpperRecord(
#             user_id=str(self.mock_user_1.id),
#             user_eth_address=self.mock_user_1.erc20_address,
#             user_ratio=decimal.Decimal("475000"),
#             mentor_list=[MintIcpperRecordMeta(
#                 mentor_id=str(self.owner.id),
#                 mentor_eth_address=self.owner.erc20_address,
#                 mentor_radio=decimal.Decimal("12500"),
#             )]
#         ))
#         mint_icpper_records.append(MintIcpperRecord(
#             user_id=str(self.mock_user_2.id),
#             user_eth_address=self.mock_user_2.erc20_address,
#             user_ratio=decimal.Decimal("475000"),
#             mentor_list=[MintIcpperRecordMeta(
#                 mentor_id=str(self.owner.id),
#                 mentor_eth_address=self.owner.erc20_address,
#                 mentor_radio=decimal.Decimal("12500"),
#             )]
#         ))
#         mint_icpper_records.append(MintIcpperRecord(
#             user_id=str(self.mock_user_3.id),
#             user_eth_address=self.mock_user_3.erc20_address,
#             user_ratio=decimal.Decimal("475000"),
#             mentor_list=[
#                 MintIcpperRecordMeta(
#                     mentor_id=str(self.mock_user_2.id),
#                     mentor_eth_address=self.mock_user_2.erc20_address,
#                     mentor_radio=decimal.Decimal("12500"),
#                 ),
#                 MintIcpperRecordMeta(
#                     mentor_id=str(self.owner.id),
#                     mentor_eth_address=self.owner.erc20_address,
#                     mentor_radio=decimal.Decimal("6250"),
#                 )
#             ]
#         ))
#         for user in [self.mock_user_4, self.mock_user_5, self.mock_user_6, self.mock_user_7]:
#             mint_icpper_records.append(MintIcpperRecord(
#                 user_id=str(user.id),
#                 user_eth_address=user.erc20_address,
#                 user_ratio=decimal.Decimal("475000"),
#                 mentor_list=[]
#             ))
#
#         token_transfer_event_logs = []
#         mint_token_address_list = [
#             self.owner.erc20_address,
#             self.icpper.erc20_address,
#             self.mock_user_1.erc20_address,
#             self.mock_user_2.erc20_address,
#             self.mock_user_3.erc20_address,
#             self.mock_user_4.erc20_address,
#             self.mock_user_5.erc20_address,
#             self.mock_user_6.erc20_address,
#             self.mock_user_7.erc20_address,
#             ICPDAO_ETH_DAOSTAKING_ADDRESS
#         ]
#         mint_token_amount_ratio_list = [
#             decimal.Decimal("328750"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("487500"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("475000"),
#             decimal.Decimal("158750")
#         ]
#
#         record = TokenMintRecord(
#             dao_id=str(dao.id),
#             token_contract_address=token_contract_address,
#             token_symbol=token_symbol,
#             chain_id=chain_id,
#             start_cycle_id=start_cycle_id,
#             end_cycle_id=end_cycle_id,
#             cycle_ids=cycle_ids,
#             status=MintRecordStatusEnum.SUCCESS.value,
#             mint_icpper_records=mint_icpper_records,
#             token_transfer_event_logs=token_transfer_event_logs,
#             total_real_size=decimal.Decimal("43"),
#             unit_real_size_value=decimal.Decimal("7.511627906976744186046511628"),
#             mint_token_address_list=mint_token_address_list,
#             mint_token_amount_ratio_list=mint_token_amount_ratio_list,
#             start_timestamp=0,
#             end_timestamp=0,
#             tick_lower=0,
#             tick_upper=0,
#             mint_value=decimal.Decimal("340")
#         ).save()
#
#         record = TokenMintRecord.objects(id=str(record.id)).first()
#
#         _update_mentor_income(record)
