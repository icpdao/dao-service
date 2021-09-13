import decimal

from graphene import List, Field, String, Int, Mutation, Boolean
from mongoengine import Q

from app.common.models.icpdao.cycle import Cycle, CycleIcpperStat
from app.common.models.icpdao.icppership import Icppership, IcppershipProgress, IcppershipStatus
from app.common.models.icpdao.token import TokenMintRecord, MintRadtio, MintIcpperRecord, MintIcpperRecordMeta, \
    MintRecordStatusEnum
from app.common.models.icpdao.user import User
from app.common.schema import BaseObjectType
from app.common.schema.icpdao import TokenMintRecordSchema
from settings import ICPDAO_ETH_DAOSTAKING_ADDRESS


class SystemUser:
    id = "icpdao"
    nickname = "icpdao"
    github_login = "icpdao"
    github_user_id = "icpdao"
    avatar = ""
    erc20_address = ICPDAO_ETH_DAOSTAKING_ADDRESS


class BuildSplitInfo:
    def __init__(self, dao_id, cycles):
        self.dao_id = dao_id
        self.cycles = cycles
        self.job_user_id__2__job_size = self._build_job_user_id__2__job_size(self.dao_id, self.cycles)
        self.job_user_id_list = self._build_job_user_id_list(self.job_user_id__2__job_size)
        self.job_user_id__2__job_size_ratio = self._build_job_user_id__2__job_size_ratio(self.job_user_id__2__job_size)
        self.job_user_id__2__level7_mentor_id_list = self._build_job_user_id__2__level7_mentor_id_list(self.job_user_id_list)
        self.job_user_id__2__level7_mentor_id_2_ratio = self._build_job_user_id__2__level7_mentor_id_2_ratio(self.job_user_id__2__job_size, self.job_user_id__2__level7_mentor_id_list)
        self.user_id__2__ratio = self._build_user_id__2__ratio(self.job_user_id__2__job_size, self.job_user_id__2__level7_mentor_id_list)
        self.split_user_id_list = self._build_split_user_id_list(self.job_user_id__2__level7_mentor_id_list, self.job_user_id_list, self.user_id__2__ratio)
        self.user_id__2__user = self._build_user_id__2__user(self.split_user_id_list)

    @staticmethod
    def _build_job_user_id__2__job_size(dao_id, cycles):
        cycle_id_list = [str(cycle.id) for cycle in cycles]
        job_user_id__2__job_size = {}
        for stat in CycleIcpperStat.objects(dao_id=dao_id, cycle_id__in=cycle_id_list):
            job_user_id__2__job_size.setdefault(stat.user_id, decimal.Decimal("0"))
            job_user_id__2__job_size[stat.user_id] += stat.size
        return job_user_id__2__job_size

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
            for icppership in Icppership.objects(progress=IcppershipProgress.ACCEPT.value, status=IcppershipStatus.ICPPER.value, icpper_user_id__in=current_query_user_id_list):
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
            job_user_id__2__job_size_ratio[user_id] = job_size_base_ratio * MintRadtio.ICPPER_RATIO
        return job_user_id__2__job_size_ratio

    @staticmethod
    def _build_job_user_id__2__level7_mentor_id_2_ratio(job_user_id__2__job_size, job_user_id__2__level7_mentor_id_list):
        job_user_id__2__level7_mentor_id_2_ratio = {}

        for job_user_id in job_user_id__2__level7_mentor_id_list:
            parent_user_ids = job_user_id__2__level7_mentor_id_list[job_user_id]
            level7_mentor_id_2_ratio = {}
            for index, parent_user_id in enumerate(parent_user_ids):
                job_size_base_ratio = job_user_id__2__job_size[job_user_id] * decimal.Decimal('100000')
                size = job_size_base_ratio * \
                    MintRadtio.MENTOR_BASE_ALL_RATIO * \
                    MintRadtio.MENTOR_7_LELVES_RATIO_LIST[index]
                level7_mentor_id_2_ratio[parent_user_id] = size
            job_user_id__2__level7_mentor_id_2_ratio[job_user_id] = level7_mentor_id_2_ratio
        return job_user_id__2__level7_mentor_id_2_ratio

    @staticmethod
    def _build_user_id__2__ratio(job_user_id__2__job_size, job_user_id__2__level7_mentor_id_list):
        user_id__2__ratio = {}
        for user_id in job_user_id__2__job_size:
            job_size_base_ratio = job_user_id__2__job_size[user_id] * decimal.Decimal('100000')
            user_id__2__ratio.setdefault(user_id, decimal.Decimal('0'))
            user_id__2__ratio[user_id] += job_size_base_ratio * MintRadtio.ICPPER_RATIO

            parent_user_ids = job_user_id__2__level7_mentor_id_list[user_id]
            for index in range(0, 7):
                parent_user_id = SystemUser.id
                if index+1 <= len(parent_user_ids):
                    parent_user_id = parent_user_ids[index]
                user_id__2__ratio.setdefault(parent_user_id, decimal.Decimal('0'))
                user_id__2__ratio[parent_user_id] += job_size_base_ratio * \
                    MintRadtio.MENTOR_BASE_ALL_RATIO * \
                    MintRadtio.MENTOR_7_LELVES_RATIO_LIST[index]

        for user_id in user_id__2__ratio:
            user_id__2__ratio[user_id] = int(user_id__2__ratio[user_id])

        return user_id__2__ratio

    @staticmethod
    def _build_split_user_id_list(job_user_id__2__level7_mentor_id_list, job_user_id_list, user_id__2__ratio):
        split_user_id_list = []
        for user_id in job_user_id_list:
            if user_id not in split_user_id_list:
                split_user_id_list.append(user_id)

        for user_id in job_user_id_list:
            parent_user_ids = job_user_id__2__level7_mentor_id_list[user_id]
            for parent_user_id in parent_user_ids:
                if parent_user_id not in split_user_id_list:
                    split_user_id_list.append(parent_user_id)

        if SystemUser.id in list(user_id__2__ratio.keys()):
            split_user_id_list.append(SystemUser.id)
        return split_user_id_list

    @staticmethod
    def _build_user_id__2__user(split_user_id_list):
        user_id__2__user = {}
        split_user_id_list_have_system_user = False
        query_user_id = []
        for user_id in split_user_id_list:
            if user_id != SystemUser.id:
                query_user_id.append(user_id)
            else:
                split_user_id_list_have_system_user = True

        for user in User.objects(id__in=query_user_id):
            user_id__2__user[str(user.id)] = user
        if split_user_id_list_have_system_user:
            user_id__2__user[SystemUser.id] = SystemUser
        return user_id__2__user

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
            query_q = query_q & Q(status=status)
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

    def get_query(self, info, dao, start_timestamp, end_timestamp):
        """
        查找指定 cycle
        找到 cycle 所有 user job size
        找到所有人的上级，生成 user id list
        按照比例给所有 user id 生成 radio
        """
        cycles = [cycle for cycle in Cycle.objects(dao_id=str(dao.id), begin_at__gte=start_timestamp, end_at__lte=end_timestamp)]

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
        token_contract_address = String(required=True)
        start_timestamp = Int(required=True)
        end_timestamp = Int(required=True)
        tick_lower = Int(required=True)
        tick_upper = Int(required=True)
        chain_id = String(required=True)

    token_mint_record = Field(TokenMintRecordSchema)

    def mutate(self, info, dao_id, token_contract_address, start_timestamp, end_timestamp, tick_lower, tick_upper, chain_id):
        cycles = [cycle for cycle in Cycle.objects(dao_id=dao_id, begin_at__gte=start_timestamp, end_at__lte=end_timestamp)]

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
                    mentor_radio=decimal.Decimal(str(bsi.job_user_id__2__level7_mentor_id_2_ratio[job_user_id][parent_user_id])),
                ))
            mint_icpper_records.append(MintIcpperRecord(
                user_id=job_user_id,
                user_eth_address=bsi.user_id__2__user[job_user_id].erc20_address,
                user_ratio=decimal.Decimal(str(bsi.job_user_id__2__job_size_ratio[job_user_id])),
                mentor_list=mentor_list
            ))

        record = TokenMintRecord(
            dao_id=dao_id,
            token_contract_address=token_contract_address,
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
