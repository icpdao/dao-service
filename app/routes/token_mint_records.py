import decimal
import os
import time

from graphene import List, Field, String, Int, Mutation, Boolean
from mongoengine import Q
from web3 import Web3

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.token import TokenMintRecord, MintRadtio, MintIcpperRecord, MintIcpperRecordMeta, \
    MintRecordStatusEnum
from app.common.models.icpdao.user import User
from app.common.schema import BaseObjectType
from app.common.schema.icpdao import TokenMintRecordSchema
from app.common.utils.errors import TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_NO_START_CYCLE, \
    TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_NO_END_CYCLE, \
    TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_START_CYCLE_NOT_IN_END_CYCLE_BEFORE, \
    TOKEN_MINT_RECORD_CREATE_HAVE_UN_DONE_RECORD
from app.controllers.find_lost_tx_for_droped_token_mint_record import run_find_lost_tx_for_drop_token_mint_record_task
from app.controllers.sync_token_mint_record_event import run_sync_token_mint_record_event_task, get_eth_node_url, \
    TOKEN_ABI
from settings import ICPDAO_ETH_TOKEN_FACTORY_DEPLOY_BLACK_NUMBER, ICPDAO_ETH_DAO_FACTORY_OWNER_ADDRESS


class SystemUser:
    id = "icpdao"
    nickname = "icpdao"
    github_login = "icpdao"
    github_user_id = "icpdao"
    avatar = ""
    erc20_address = ICPDAO_ETH_DAO_FACTORY_OWNER_ADDRESS


def query_cycles_by_params(dao_id, start_cycle_id, end_cycle_id):
    two_cycles = [cycle for cycle in Cycle.objects(dao_id=dao_id, id__in=[start_cycle_id, end_cycle_id])]
    start_cycle = None
    end_cycle = None

    for cycle in two_cycles:
        if str(cycle.id) == start_cycle_id:
            start_cycle = cycle
        if str(cycle.id) == end_cycle_id:
            end_cycle = cycle

    if start_cycle is None:
        raise ValueError(TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_NO_START_CYCLE)
    if end_cycle is None:
        raise ValueError(TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_NO_END_CYCLE)
    if str(start_cycle.id) != str(end_cycle.id):
        if start_cycle.begin_at >= end_cycle.begin_at:
            raise ValueError(TOKEN_MINT_RECORD_QUERY_CYCLES_BY_PARAMS_START_CYCLE_NOT_IN_END_CYCLE_BEFORE)

    cycles = [cycle for cycle in
              Cycle.objects(dao_id=dao_id, begin_at__gte=start_cycle.begin_at, end_at__lte=end_cycle.end_at)]

    cycles = sorted(cycles, key=lambda cycle: cycle.begin_at)
    return start_cycle, end_cycle, cycles


class BuildSplitInfo:
    def __init__(self, dao_id, cycles):
        self.dao_id = dao_id
        self.cycles = cycles

        self.job_user_id__2__job_size = self._build_job_user_id__2__job_size(self.dao_id, self.cycles)

        self.job_user_id_list = self._build_job_user_id_list(self.job_user_id__2__job_size)
        self.job_user_id__2__level7_mentor_id_list = self._build_job_user_id__2__level7_mentor_id_list(
            self.job_user_id_list)
        self.all_user_id_list = self._build_all_user_id_list(self.job_user_id__2__level7_mentor_id_list,
                                                             self.job_user_id_list)

        self.user_id__2__user = self._build_user_id__2__user(self.all_user_id_list)
        self.no_erc20_address_mentor_id_list = self._build_no_erc20_address_mentor_id_list(
            self.job_user_id__2__level7_mentor_id_list, self.user_id__2__user)

        self.job_user_id__2__job_size_ratio = self._build_job_user_id__2__job_size_ratio(self.job_user_id__2__job_size)
        self.job_user_id__2__level7_mentor_id_2_ratio = self._build_job_user_id__2__level7_mentor_id_2_ratio(
            self.job_user_id__2__job_size, self.job_user_id__2__level7_mentor_id_list,
            self.no_erc20_address_mentor_id_list)
        self.user_id__2__ratio = self._build_user_id__2__ratio(self.job_user_id__2__job_size,
                                                               self.job_user_id__2__level7_mentor_id_list,
                                                               self.no_erc20_address_mentor_id_list)
        self.split_user_id_list = self._build_split_user_id_list(self.job_user_id_list,
                                                                 self.job_user_id__2__level7_mentor_id_list,
                                                                 self.user_id__2__ratio,
                                                                 self.no_erc20_address_mentor_id_list)

    @staticmethod
    def _build_job_user_id__2__job_size(dao_id, cycles):
        cycle_id_list = [str(cycle.id) for cycle in cycles]
        job_user_id__2__job_size = {}
        for stat in CycleIcpperStat.objects(dao_id=dao_id, cycle_id__in=cycle_id_list):
            job_user_id__2__job_size.setdefault(stat.user_id, decimal.Decimal("0"))
            job_user_id__2__job_size[stat.user_id] += stat.size

        have_job_user_id__2__job_size = {}
        for user_id in job_user_id__2__job_size:
            value = job_user_id__2__job_size[user_id]
            if value != 0:
                have_job_user_id__2__job_size[user_id] = value
        return have_job_user_id__2__job_size

    @staticmethod
    def _build_job_user_id_list(job_user_id__2__job_size):
        job_user_id_list = list(job_user_id__2__job_size.keys())
        job_user_id_list.sort()
        return job_user_id_list

    @staticmethod
    def _build_job_user_id__2__level7_mentor_id_list(job_user_id_list):
        icppership_list = []
        current_query_user_id_list = job_user_id_list
        next_query_user_id_list = []
        for index in range(0, 7):
            for icppership in Icppership.objects(progress=IcppershipProgress.ACCEPT.value,
                                                 status=IcppershipStatus.ICPPER.value,
                                                 icpper_user_id__in=current_query_user_id_list):
                icppership_list.append(icppership)
                next_query_user_id_list.append(icppership.mentor_user_id)
            current_query_user_id_list = next_query_user_id_list
            next_query_user_id_list = []

        icpper_id__2__mentor_id = {}
        for icppership in icppership_list:
            icpper_id__2__mentor_id[icppership.icpper_user_id] = icppership.mentor_user_id

        job_user_id__2__level7_mentor_id_list = {}
        for user_id in job_user_id_list:
            job_user_id__2__level7_mentor_id_list[user_id] = []
            current_user_id = user_id
            while True:
                mentor_id = icpper_id__2__mentor_id.get(current_user_id, None)
                if mentor_id:
                    job_user_id__2__level7_mentor_id_list[user_id].append(mentor_id)
                    current_user_id = mentor_id
                else:
                    break

        return job_user_id__2__level7_mentor_id_list

    @staticmethod
    def _build_job_user_id__2__job_size_ratio(job_user_id__2__job_size):
        job_user_id__2__job_size_ratio = {}
        for user_id in job_user_id__2__job_size:
            job_size_base_ratio = job_user_id__2__job_size[user_id] * decimal.Decimal('100000')
            job_user_id__2__job_size_ratio[user_id] = int(job_size_base_ratio * MintRadtio.ICPPER_RATIO)
        return job_user_id__2__job_size_ratio

    @staticmethod
    def _build_job_user_id__2__level7_mentor_id_2_ratio(job_user_id__2__job_size, job_user_id__2__level7_mentor_id_list,
                                                        no_erc20_address_mentor_id_list):
        job_user_id__2__level7_mentor_id_2_ratio = {}

        for job_user_id in job_user_id__2__level7_mentor_id_list:
            parent_user_ids = job_user_id__2__level7_mentor_id_list[job_user_id]
            level7_mentor_id_2_ratio = {}
            for index, parent_user_id in enumerate(parent_user_ids):
                job_size_base_ratio = job_user_id__2__job_size[job_user_id] * decimal.Decimal('100000')

                size = decimal.Decimal('0')
                if parent_user_id not in no_erc20_address_mentor_id_list:
                    size = job_size_base_ratio * \
                           MintRadtio.MENTOR_BASE_ALL_RATIO * \
                           MintRadtio.MENTOR_7_LELVES_RATIO_LIST[index]

                level7_mentor_id_2_ratio[parent_user_id] = int(size)
            job_user_id__2__level7_mentor_id_2_ratio[job_user_id] = level7_mentor_id_2_ratio
        return job_user_id__2__level7_mentor_id_2_ratio

    @staticmethod
    def _build_user_id__2__ratio(job_user_id__2__job_size, job_user_id__2__level7_mentor_id_list,
                                 no_erc20_address_mentor_id_list):
        user_id__2__ratio = {}
        for user_id in job_user_id__2__job_size:
            job_size_base_ratio = job_user_id__2__job_size[user_id] * decimal.Decimal('100000')
            user_id__2__ratio.setdefault(user_id, decimal.Decimal('0'))
            user_id__2__ratio[user_id] += job_size_base_ratio * MintRadtio.ICPPER_RATIO

            parent_user_ids = job_user_id__2__level7_mentor_id_list[user_id]
            for index in range(0, 7):
                parent_user_id = SystemUser.id
                size = job_size_base_ratio * \
                       MintRadtio.MENTOR_BASE_ALL_RATIO * \
                       MintRadtio.MENTOR_7_LELVES_RATIO_LIST[index]
                if index + 1 <= len(parent_user_ids):
                    mentor_id = parent_user_ids[index]
                    if mentor_id not in no_erc20_address_mentor_id_list:
                        parent_user_id = mentor_id

                user_id__2__ratio.setdefault(parent_user_id, decimal.Decimal('0'))
                user_id__2__ratio[parent_user_id] += size

        for user_id in user_id__2__ratio:
            user_id__2__ratio[user_id] = int(user_id__2__ratio[user_id])

        return user_id__2__ratio

    @staticmethod
    def _build_split_user_id_list(job_user_id_list, job_user_id__2__level7_mentor_id_list, user_id__2__ratio, no_erc20_address_mentor_id_list):
        split_user_id_list = []
        for user_id in job_user_id_list:
            if user_id not in split_user_id_list:
                split_user_id_list.append(user_id)

        for user_id in job_user_id_list:
            parent_user_ids = job_user_id__2__level7_mentor_id_list[user_id]
            for parent_user_id in parent_user_ids:
                if parent_user_id not in no_erc20_address_mentor_id_list and parent_user_id not in split_user_id_list:
                    split_user_id_list.append(parent_user_id)

        if SystemUser.id in list(user_id__2__ratio.keys()):
            split_user_id_list.append(SystemUser.id)
        return split_user_id_list


    @staticmethod
    def _build_all_user_id_list(job_user_id__2__level7_mentor_id_list, job_user_id_list):
        all_user_id_list = []
        for user_id in job_user_id_list:
            if user_id not in all_user_id_list:
                all_user_id_list.append(user_id)

        for user_id in job_user_id_list:
            parent_user_ids = job_user_id__2__level7_mentor_id_list[user_id]
            for parent_user_id in parent_user_ids:
                if parent_user_id not in all_user_id_list:
                    all_user_id_list.append(parent_user_id)
        all_user_id_list.append(SystemUser.id)
        return all_user_id_list

    @staticmethod
    def _build_user_id__2__user(all_user_id_list):
        user_id__2__user = {}
        have_system_user = False
        query_user_id = []

        for user_id in all_user_id_list:
            if user_id != SystemUser.id:
                query_user_id.append(user_id)
            else:
                have_system_user = True

        for user in User.objects(id__in=query_user_id):
            user_id__2__user[str(user.id)] = user

        if have_system_user:
            user_id__2__user[SystemUser.id] = SystemUser

        return user_id__2__user

    @staticmethod
    def _build_no_erc20_address_mentor_id_list(job_user_id__2__level7_mentor_id_list, user_id__2__user):
        tmp_set = set()
        for job_user_id in job_user_id__2__level7_mentor_id_list:
            for mentor_id in job_user_id__2__level7_mentor_id_list[job_user_id]:
                if not user_id__2__user[mentor_id].erc20_address:
                    tmp_set.add(mentor_id)

        return list(tmp_set)

    def total_size(self):
        result = decimal.Decimal("0")
        for user_id in self.job_user_id__2__job_size:
            job_size = self.job_user_id__2__job_size[user_id]
            result += job_size
        return result

    def split_user_erc20_address_list(self):
        address_list = []
        for user_id in self.split_user_id_list:
            user = self.user_id__2__user[user_id]
            address_list.append(user.erc20_address)
        return address_list

    def split_user_ratio_list(self):
        ratio_list = []
        for user_id in self.split_user_id_list:
            ratio = self.user_id__2__ratio[user_id]
            ratio_list.append(ratio)
        return ratio_list


class TokenMintRecordQuery(BaseObjectType):
    datum = Field(TokenMintRecordSchema)


class TokenMintRecordsQuery(BaseObjectType):
    nodes = List(TokenMintRecordQuery)

    def get_query(self, info, dao, first, offset, status=None, chain_id=None, token_contract_address=None):
        query_q = Q(dao_id=str(dao.id))
        if status is not None:
            query_q = query_q & Q(status__in=status)
        if chain_id is not None:
            query_q = query_q & Q(chain_id=chain_id)
        if token_contract_address is not None:
            query_q = query_q & Q(token_contract_address=token_contract_address)
        query = TokenMintRecord.objects(query_q).order_by("-start_timestamp")
        return TokenMintRecordsQuery(
            nodes=[TokenMintRecordQuery(datum=item) for item in query.limit(first).skip(offset)]
        )


class SplitInfo(BaseObjectType):
    user_id = String()
    user_nickname = String()
    user_github_login = String()
    user_avatar = String()
    user_erc20_address = String()
    ratio = Int()


class TokenMintSplitInfoQuery(BaseObjectType):
    split_infos = List(SplitInfo)

    def get_query(self, info, dao, start_cycle_id, end_cycle_id):
        """
        查找指定 cycle
        找到 cycle 所有 user job size
        找到所有人的上级，生成 user id list
        按照比例给所有 user id 生成 radio
        """
        start_cycle, end_cycle, cycles = query_cycles_by_params(str(dao.id), start_cycle_id, end_cycle_id)

        bsi = BuildSplitInfo(str(dao.id), cycles)
        split_infos = []
        for user_id in bsi.split_user_id_list:
            user = bsi.user_id__2__user[user_id]
            user_ratio = int(bsi.user_id__2__ratio[str(user.id)])
            split_infos.append(SplitInfo(
                user_id=str(user.id),
                user_nickname=user.nickname,
                user_github_login=user.github_login,
                user_avatar=user.avatar,
                user_erc20_address=user.erc20_address,
                ratio=user_ratio
            ))

        return TokenMintSplitInfoQuery(split_infos=split_infos)


class CreateTokenMintRecord(Mutation):
    class Arguments:
        dao_id = String(required=True)
        start_cycle_id = String(required=True)
        end_cycle_id = String(required=True)
        token_contract_address = String(required=True)
        token_symbol = String(required=True)
        start_timestamp = Int(required=True)
        end_timestamp = Int(required=True)
        tick_lower = Int(required=True)
        tick_upper = Int(required=True)
        chain_id = String(required=True)

    token_mint_record = Field(TokenMintRecordSchema)

    def mutate(self, info, dao_id, start_cycle_id, end_cycle_id, token_contract_address, start_timestamp, end_timestamp,
               tick_lower, tick_upper, chain_id, token_symbol):
        un_done_record_count = TokenMintRecord.objects(
            dao_id=dao_id,
            token_contract_address=token_contract_address,
            chain_id=chain_id,
            status__in=[MintRecordStatusEnum.INIT.value, MintRecordStatusEnum.PENDING.value]
        ).count()

        if un_done_record_count != 0:
            raise ValueError(TOKEN_MINT_RECORD_CREATE_HAVE_UN_DONE_RECORD)

        start_cycle, end_cycle, cycles = query_cycles_by_params(dao_id, start_cycle_id, end_cycle_id)

        cycle_id_list = [str(cycle.id) for cycle in cycles]

        bsi = BuildSplitInfo(dao_id, cycles)

        total_real_size = bsi.total_size()
        mint_token_address_list = bsi.split_user_erc20_address_list()
        mint_token_amount_ratio_list = bsi.split_user_ratio_list()
        mint_icpper_records = []
        for job_user_id in bsi.job_user_id_list:
            mentor_list = []
            for parent_user_id in bsi.job_user_id__2__level7_mentor_id_list[job_user_id]:
                mentor_list.append(MintIcpperRecordMeta(
                    mentor_id=parent_user_id,
                    mentor_eth_address=bsi.user_id__2__user[parent_user_id].erc20_address,
                    mentor_radio=bsi.job_user_id__2__level7_mentor_id_2_ratio[job_user_id].get(parent_user_id, 0),
                ))
            mint_icpper_records.append(MintIcpperRecord(
                user_id=job_user_id,
                user_eth_address=bsi.user_id__2__user[job_user_id].erc20_address,
                user_ratio=bsi.job_user_id__2__job_size_ratio[job_user_id],
                mentor_list=mentor_list
            ))

        record = TokenMintRecord(
            dao_id=dao_id,
            token_contract_address=token_contract_address,
            token_symbol=token_symbol,
            start_cycle_id=str(start_cycle.id),
            end_cycle_id=str(end_cycle.id),
            cycle_ids=cycle_id_list,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            tick_lower=tick_lower,
            tick_upper=tick_upper,
            chain_id=chain_id,
            total_real_size=total_real_size,
            mint_token_address_list=mint_token_address_list,
            mint_token_amount_ratio_list=mint_token_amount_ratio_list,
            mint_icpper_records=mint_icpper_records
        ).save()

        return CreateTokenMintRecord(token_mint_record=record)


class LinkTxHashForTokenMintRecord(Mutation):
    class Arguments:
        id = String(required=True)
        mint_tx_hash = String(required=True)

    token_mint_record = Field(TokenMintRecordSchema)

    def mutate(self, info, id, mint_tx_hash):
        tr = TokenMintRecord.objects(mint_tx_hash=mint_tx_hash).first()
        if tr:
            raise ValueError("error.link_tx_hash_for_token_mint_record.repeat_mint_tx_hash")

        record = TokenMintRecord.objects(id=id).first()
        record.mint_tx_hash = mint_tx_hash
        record.status = MintRecordStatusEnum.PENDING.value
        record.save()

        record = TokenMintRecord.objects(id=id).first()
        return LinkTxHashForTokenMintRecord(token_mint_record=record)


class DropTokenMintRecord(Mutation):
    class Arguments:
        id = String(required=True)

    ok = Boolean()

    def mutate(self, info, id):
        record = TokenMintRecord.objects(id=id).first()
        if record.status == MintRecordStatusEnum.INIT.value:
            record.status = MintRecordStatusEnum.DROPED.value
            record.save()
            return DropTokenMintRecord(ok=True)
        else:
            return DropTokenMintRecord(ok=False)


class SyncTokenMintRecordEvent(Mutation):
    class Arguments:
        id = String(required=True)

    ok = Boolean()

    def mutate(self, info, id):
        if os.environ.get('IS_UNITEST') != 'yes':
            background_tasks = info.context['background']
            background_tasks.add_task(run_sync_token_mint_record_event_task, id)
        return DropTokenMintRecord(ok=True)


class FindLostTxForInitTokenMintRecord(Mutation):
    class Arguments:
        id = String(required=True)

    token_mint_record = Field(TokenMintRecordSchema)

    def mutate(self, info, id):
        token_mint_record = TokenMintRecord.objects(id=id).first()
        if not token_mint_record:
            return FindLostTxForInitTokenMintRecord(token_mint_record=token_mint_record)

        if token_mint_record.status != MintRecordStatusEnum.INIT.value:
            return FindLostTxForInitTokenMintRecord(token_mint_record=token_mint_record)

        last_success_record = TokenMintRecord.objects(
            dao_id=token_mint_record.dao_id,
            token_contract_address=token_mint_record.token_contract_address,
            chain_id=token_mint_record.chain_id,
            status=MintRecordStatusEnum.SUCCESS.value
        ).order_by("-end_timestamp").first()

        from_black_number = ICPDAO_ETH_TOKEN_FACTORY_DEPLOY_BLACK_NUMBER
        if last_success_record:
            from_black_number = last_success_record.block_number

        web3 = Web3(Web3.WebsocketProvider(get_eth_node_url(token_mint_record.chain_id)))
        token = web3.eth.contract(address=Web3.toChecksumAddress(token_mint_record.token_contract_address),
                                  abi=TOKEN_ABI)
        tef = token.events["Mint"].createFilter(fromBlock=from_black_number, toBlock="latest")

        for log in tef.get_all_entries():
            mint_tx_hash = Web3.toHex(log["transactionHash"])
            _mintTokenAddressList = log["args"]["_mintTokenAddressList"]
            _mintTokenAmountRatioList = log["args"]["_mintTokenAmountRatioList"]
            _startTimestamp = log["args"]["_startTimestamp"]
            _endTimestamp = log["args"]["_endTimestamp"]
            _tickLower = log["args"]["_tickLower"]
            _tickUpper = log["args"]["_tickUpper"]

            eq1 = _mintTokenAddressList == token_mint_record.mint_token_address_list
            eq2 = _mintTokenAmountRatioList == token_mint_record.mint_token_amount_ratio_list
            eq3 = _startTimestamp == token_mint_record.start_timestamp
            eq4 = _endTimestamp == token_mint_record.end_timestamp
            eq5 = _tickLower == token_mint_record.tick_lower
            eq6 = _tickUpper == token_mint_record.tick_upper

            if eq1 and eq2 and eq3 and eq4 and eq5 and eq6:
                tr = TokenMintRecord.objects(
                    dao_id=token_mint_record.dao_id,
                    token_contract_address=token_mint_record.token_contract_address,
                    chain_id=token_mint_record.chain_id,
                    mint_tx_hash=mint_tx_hash,
                ).first()
                if not tr:
                    token_mint_record.mint_tx_hash = mint_tx_hash
                    token_mint_record.status = MintRecordStatusEnum.PENDING.value
                    token_mint_record.save()

        return FindLostTxForInitTokenMintRecord(token_mint_record=token_mint_record)


class FindLostTxForDropTokenMintRecord(Mutation):
    class Arguments:
        dao_id = String(required=True)
        token_contract_address = String(required=True)
        chain_id = String(required=True)

    ok = Boolean()

    def mutate(self, info, dao_id, token_contract_address, chain_id):
        if os.environ.get('IS_UNITEST') != 'yes':
            background_tasks = info.context['background']
            background_tasks.add_task(run_find_lost_tx_for_drop_token_mint_record_task, dao_id, token_contract_address,
                                      chain_id)
        return DropTokenMintRecord(ok=True)
