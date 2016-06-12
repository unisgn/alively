# coding=utf-8
# Created by 0xFranCiS on Jun 08, 2016.

from sqlalchemy.ext.declarative import declarative_base, AbstractConcreteBase, as_declarative, declared_attr

from sqlalchemy import *
from sqlalchemy.orm import relationship, composite, backref, aliased
from sqlalchemy.sql import select, func as sqlfn, exists, except_, case, label
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.inspection import inspect
from sqlalchemy.dialects.postgresql import ARRAY, JSON, JSONB, HSTORE, TSVECTOR
from sqlalchemy.ext.mutable import MutableDict
from enum import Enum
import time
from excepts import *
import hashlib
from dbx import Session, redis
import jieba

from util import ChainDict
from web import route, ctx, restful
from app_dict import *
import uuid

def default_naming_strategy(name):
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


@as_declarative()
class Base:

    def _asdict(self):
        ret = ChainDict()
        for c in inspect(self.__class__).columns:
            val = getattr(self, c.name, None)
            ret[c.name] = val
        return ret


class FakeBase(AbstractConcreteBase, Base):

    """__mapper_args__ can be set by @declared_attr if you need some dynamic info

    """
    # @declared_attr
    # def __mapper_args__(cls):
    #     return {
    #         'concrete': True,
    #         # 'polymorphic_identity': cls.__name__
    #     }
    __mapper_args__ = {
        'concrete': True
    }


class VoidEntity:

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @declared_attr
    def __tablename__(cls):
        return default_naming_strategy(cls.__name__)

    def update_vo(self, **kwargs):
        """
        :rtype: VoidEntity
        :param kwargs:
        :return:
        """
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        return self

    @classmethod
    def load(cls, pk):
        """
        :rtype: VoidEntity
        :type pk: str
        :param pk: str
        :return: VoidEntity
        """
        return Session.query(cls).get(pk)

    @classmethod
    def remove(cls, pk):
        cls.load(pk).erase()

    def save(self):
        """
        :rtype: VoidEntity
        :return: VoidEntity
        """
        Session.add(self)
        return self

    def erase(self):
        Session.delete(self)

    @property
    def phantom(self):
        return not inspect(self).has_identity


class PrimeEntity(VoidEntity):

    id = Column(Text, primary_key=True)

    def __eq__(self, other):
        return False if not isinstance(other, self.__class__) else self.id == other.id


class VersionEntity(PrimeEntity):
    """ place this class and its subclass before the VoidBase to supply the __mapped_args__

    """

    version = Column(Integer, nullable=False)

    archived = Column(Boolean, default=False)
    active = Column(Boolean, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.active = True
        self.archived = False

    def erase(self):
        self.archive()

    def archive(self):
        self.archived = False
        self.save()

    @declared_attr
    def __mapper_args__(cls):
        return {
            'concrete': True,
            # 'polymorphic_identity': cls.__name__, # turn off polymorphic loading
            'version_id_col': cls.version
        }


class AuditMixin:

    created_at = Column(BigInteger)
    created_by = Column(Text)
    modified_at = Column(BigInteger)
    modified_by = Column(Text)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = int(time.time() * 1000)
        self.modified_at = self.created_at


class BusinessEntity(VersionEntity, AuditMixin):

    number = Column(Text)
    code = Column(Text)
    name = Column(Text)
    alias = Column(Text)
    memo = Column(Text)
    keyword = Column(Text)

    notes = Column(JSONB)
    attachments = Column(JSONB)


class NodeMixin:
    """ subclass must satisfy: id property as primary_key, parent_fk property as parent foreign key
        subclass should override PrimeEntity's save method to invoke _update_leaf method before save

    """

    leaf = Column(Boolean, default=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.leaf = True

    def _update_leaf(self):
        clz = self.__class__
        tbl = clz.__table__
        # use execute instead of query, because the session may issue an update command before query method
        if not self.phantom:
            old_parent_fk = Session.execute(select([tbl.c.parent_fk]).where(tbl.c.id == self.id)).first()[0]
            if old_parent_fk == self.parent_fk:
                return
            if old_parent_fk:
                cnt = Session.query(func.count(clz.id)).filter(clz.parent_fk == old_parent_fk).one()[0]
                if cnt <= 1:
                    stmt = tbl.update().values(leaf=True).where((tbl.c.id == old_parent_fk) & (tbl.c.leaf == False))
                    Session.execute(stmt)
        if self.parent_fk:
            stmt = tbl.update().values(leaf=False).where((tbl.c.id == self.parent_fk) & (tbl.c.leaf == True))
            Session.execute(stmt)

    @classmethod
    def tree(cls, node=None):
        """

        :rtype: list[VoidEntity]
        :type node: str
        :param node:
        :return:
        """
        return Session.query(cls).filter(cls.parent_fk == node).all()


"""
preferred inherit order: MyEntity(xxxEntity, MyMixin, xxxBase)
END: mapped super, helper, mixin classes
####################################################


####################################################
START: system domain entity
"""


class User(VersionEntity, AuditMixin, FakeBase):
    __tablename__ = 't_user'
    password = Column(Text)
    name = Column(Text)
    memo = Column(Text)
    emp_fk = Column(Text)

    expire_date = Column(BigInteger)
    login_ip = Column(Text)
    login_mac = Column(Text)
    login_time = Column(BigInteger)
    logout_time = Column(BigInteger)

    OPWD = '898989'
    SALT = '9iOl*$K'

    @hybrid_property
    def username(self):
        return self.id

    def save(self):
        """

        :rtype: User
        """
        super().save()
        redis.hmset('user:%s' % self.id, self._asdict())
        return self

    @staticmethod
    def add_role(user_fk, role_fk):
        po = UserRoleHeader(user_fk=user_fk, role_fk=role_fk)
        Session.add(po)
        permits = Session.query(Permission.code).\
            join(RolePermissionHeader).\
            filter(RolePermissionHeader.role_fk == role_fk).all()
        if permits:
            redis.sadd('user_permits:%s' % user_fk, *[e[0] for e in permits])

    @staticmethod
    def remove_role(user_fk, role_fk):
        po = Session.query(UserRoleHeader)\
            .filter(UserRoleHeader.user_fk == user_fk, UserRoleHeader.role_fk == role_fk).one()
        q1 = Session.query(Permission.code)\
            .join(RolePermissionHeader)\
            .filter(RolePermissionHeader.role_fk == role_fk)
        q2 = Session.query(Permission.code).join(RolePermissionHeader, UserRoleHeader)\
            .filter(UserRoleHeader.user_fk == user_fk, RolePermissionHeader.role_fk != role_fk)
        to_remove = q1.except_(q2).all()
        if to_remove:
            redis.srem('user_permits:%s' % user_fk, *[e[0] for e in to_remove])
        Session.delete(po)

    def digest_passwd(self):
        msg = self.id + ':' + self.password + ':' + User.SALT
        self.password = str(hashlib.md5(msg.encode()).hexdigest())
        return self

    def set_passwd(self, passwd=None):
        if not passwd:
            passwd = User.OPWD
        self.password = passwd
        self.digest_passwd()
        return self


class ActivityLog:
    activity_category = None
    action_type = None
    subject = None
    detail = None
    target = None


class AppDict(VersionEntity, FakeBase):
    code = Column(Text)
    name = Column(Text)
    brief = Column(Text)
    nullable = Column(Boolean)
    dict_type = Column(Text)
    items = relationship('AppDictItem')


class AppDictItem(FakeBase, PrimeEntity):

    app_dict_fk = Column(ForeignKey('app_dict.id'))
    value = Column(Text)
    text = Column(Text)
    memo = Column(Text)


class Role(FakeBase, PrimeEntity):

    code = Column(Text, unique=True, nullable=False)
    memo = Column(Text)
    name = Column(Text)
    flag = Column(Text)

    permissions = relationship('RolePermissionHeader')

    @staticmethod
    def update_permissions(pk, *permissions):
        Session.query(RolePermissionHeader).filter(RolePermissionHeader.role_fk == pk).delete(synchronize_session=False)
        Session.bulk_insert_mappings(RolePermissionHeader, [{'role_fk': pk, 'permission_fk': e} for e in permissions])


class UserRoleHeader(VoidEntity, FakeBase):

    user_fk = Column(ForeignKey('t_user.id'), primary_key=True)
    role_fk = Column(ForeignKey('role.id'), primary_key=True)


class Permission(PrimeEntity, NodeMixin, FakeBase):

    code = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    memo = Column(Text)
    parent_fk = Column(ForeignKey('permission.id'))

    def save(self):
        self._update_leaf()
        super().save()
        return self


class RolePermissionHeader(VoidEntity, FakeBase):
    role_fk = Column(ForeignKey('role.id'), primary_key=True)
    permission_fk = Column(ForeignKey('permission.id'), primary_key=True)


class Department(VersionEntity, NodeMixin, FakeBase):

    code = Column(Text)
    name = Column(Text)
    memo = Column(Text)
    mgr = Column(Text)

    parent_fk = Column(ForeignKey('department.id'))

    def save(self):
        self._update_leaf()
        super().save()
        return self


"""
END: system entity
========================

========================
START: point cut entity

entities that owned by many different type of entities

"""


class Attachment(FakeBase, PrimeEntity):
    """
    Attachment and its owner is a N:1 relation, but Attachment can't has a reference to its owner, because
    the type of owner is unsure.
    solution here is: Attachment issue an fkid to its owner; By holding the fkid, the owner can easily find
    its N attachments
    """

    fkid = Column(Text)
    fpath = Column(Text)
    fname = Column(Text)
    mime = Column(Text)
    upload_date = Column(Integer)
    upload_by = Column(Text)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.upload_date = int(time.time())


"""
END: point cut entity
###########################

##########################
START: business domain entity
"""


class Partner(BusinessEntity, FakeBase):
    agent = Column(Text)
    role_flag = Column(Integer)  # use bit mask to combine multi roles


class Customer(VersionEntity, AuditMixin, FakeBase):
    partner_fk = Column(Text)
    agent = Column(Text)
    labels = Column(ARRAY(Text))
    info = Column(JSONB)


class Vendor(VersionEntity, AuditMixin, FakeBase):
    partner_fk = Column(Text)


class Employee(VersionEntity, AuditMixin, FakeBase):
    partner_fk = Column(Text)
    info = Column(JSONB)


"""
Part
"""


class MaterialSource(Enum):
    SELF_MADE = '1'
    PURCHASE = '2'


class Bom(VersionEntity, FakeBase):
    id = Column(String, primary_key=True)

    part_fk = Column(ForeignKey('part.id'))
    amount = Column(Numeric)
    acc_amount = Column(Numeric)
    uom_fk = Column(Text)
    leaf = Column(Boolean)
    parent_fk = Column(ForeignKey('bom.id'))
    final_part_fk = Column(ForeignKey('part.id'))

    parent = relationship('Bom', remote_side=[id], backref=backref('children', cascade='all'))
    part = relationship('Part', foreign_keys=[part_fk], backref=backref('bom', uselist=False))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.leaf = True

    def append(self, child):
        """
        :type child: Bom
        """
        child.parent = self
        child.final_part_fk = self.final_part_fk
        if self.amount is not None:
            child.acc_amount = self.amount * child.amount
        else:
            child.acc_amount = child.amount
        part = Part.load(child.part_fk)
        if part.has_bom:
            child.leaf = False
            for c in part.bom.children:  # type: Bom
                c = c._fork()
                child.append(c)

        self.children.append(child)
        return self

    def top(self, part_fk):
        if self.leaf:
            self.leaf = False
        self.part_fk = part_fk
        if not self.part:
            self.part = Part.load(part_fk)
            if not self.part.has_bom:
                self.part.has_bom = True
        self.final_part_fk = part_fk
        self.acc_amount = 1
        return self

    def _fork(self):
        return Bom(id=str(uuid.uuid4()), amount=self.amount, uom_fk=self.uom_fk, leaf=self.leaf, part_fk=self.part_fk)

    def truncate(self):
        self.children.clear()
        return self


class Part(BusinessEntity, FakeBase):
    has_bom = Column(Boolean)
    category_fk = Column(Text)
    uom_fk = Column(Text)
    source = Column(Text)
    barcode = Column(Text)

    img_url = Column(Text)

    labels = Column(ARRAY(Text))

    on_hand = Column(Numeric)
    on_demand = Column(Numeric)
    on_produce = Column(Numeric)

    safe_stock = Column(Numeric)
    min_stock = Column(Numeric)
    max_stock = Column(Numeric)

    stocks = Column(JSONB)

    cost_avg = Column(Numeric)
    cost_std = Column(Numeric)

    pd_cycle = Column(Numeric)
    yield_rate = Column(Numeric)

    props = Column(JSONB)

    # bom_fk = Column(ForeignKey('bom.id'))
    # bom = relationship('Bom', uselist=False, back_populates='part', foreign_keys=[Bom.part_fk])


class PartItem(PrimeEntity):
    part_fk = Column(Text)
    ref_fk = Column(Text)
    tx_warehouse_fk = Column(Text)
    rx_warehouse_fk = Column(Text)
    uom_fk = Column(Text)
    lot = Column(Numeric)
    price = Column(Numeric)
    amount = Column(Numeric)
    discount = Column(Numeric)
    tax = Column(Numeric)
    memo = Column(Numeric)
    due_date = Column(BigInteger)
    lot_proceed = Column(Numeric)
    lot_received = Column(Numeric)
    lot_delivered = Column(Numeric)
    lot_invoiced = Column(Numeric)
    lot_total_return = Column(Numeric)


class PartProperty(PrimeEntity, FakeBase):
    part_fk = Column(Text)
    name = Column(Text)
    value = Column(Text)


class PartCategory(VersionEntity, NodeMixin, FakeBase):
    name = Column(Text)
    memo = Column(Text)


class PartPropertyName(VersionEntity, FakeBase):
    name = Column(Text)
    value_type = Column(Text)
    category_fk = Column(ForeignKey('part_category.id'))


class PartPropertyValue(VersionEntity, FakeBase):
    name = Column(Text)
    prop_fk = Column(ForeignKey('part_property_name.id'))


class Uom(VersionEntity, FakeBase):
    """
    Unit of measure
    """
    code = Column(Text)
    name = Column(Text)
    ratio = Column(Numeric)
    group_fk = Column(Text)
    is_base = Column(Boolean)


class UomGroup(VersionEntity, FakeBase):
    name = Column(Text)


class Warehouse(VersionEntity, NodeMixin, FakeBase):
    keeper = Column(Text)
    code = Column(Text)
    name = Column(Text)
    info = Column(JSONB)
    is_default = Column(Boolean)


class Stock(PrimeEntity, FakeBase):
    warehouse_fk = Column(ForeignKey('warehouse.id'))
    part_fk = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    uom_fk = Column(Text)


"""
business activity
"""


class TaskReminder(PrimeEntity, FakeBase):
    channel = Column(Text)


class BusinessActivity(VersionEntity, AuditMixin):
    number = Column(Text)
    code = Column(Text)
    event_date = Column(BigInteger)
    status = Column(Text)
    ref_docs = Column(JSONB)
    notes = Column(JSONB)
    attachments = Column(JSONB)

    @property
    def channel(self):
        return self.__class__.__name__ + '#' + self.id


class BusinessOrder(BusinessActivity):
    partner_fk = Column(Text)
    agent = Column(Text)
    total_tax = Column(Numeric)
    total_amount = Column(Numeric)
    discount = Column(Numeric)
    ref_order_no = Column(Text)
    deliver_plan = Column(JSONB)
    payment_plan = Column(JSONB)
    stat_payment = Column(Text)
    stat_deliver = Column(Text)


class BusinessQuotation(BusinessActivity):
    partner_fk = Column(Text)
    agent = Column(Text)


class SaleOrder(BusinessOrder, FakeBase):
    pass


class SaleOrderItem(PartItem, FakeBase):
    pass


class SaleQuotation(BusinessQuotation, FakeBase):
    pass


class SaleQuotationItem(PartItem, FakeBase):
    pass


class PurchaseOrder(BusinessOrder, FakeBase):
    pass


class PurchaseOrderItem(PartItem, FakeBase):
    pass


class PurchaseRequisition(BusinessActivity, FakeBase):
    applicant = Column(Text)
    receipt = Column(Text)
    department_fk = Column(Text)
    due_date = Column(BigInteger)


class PurchaseRequisitionItem(PartItem, FakeBase):
    pass


class PurchaseQuotation(BusinessQuotation, FakeBase):
    """
    RFQ: Request for quotation，询价单
    """
    pass


class PurchaseQuotationItem(PartItem, FakeBase):
    pass


class MaterialTransfer(BusinessActivity):
    operator = Column(Text)
    sender = Column(Text)
    receiver = Column(Text)
    warehouse_tx = Column(Text)
    warehouse_rx = Column(Text)
    total_amount = Column(Numeric)
    parent_doc = Column(Text)


class MaterialReceipt(MaterialTransfer, FakeBase):
    pass


class MaterialReceiptItem(PartItem, FakeBase):
    pass


class MaterialReceiptReturn(MaterialTransfer, FakeBase):
    pass


class MaterialReceiptReturnItem(PartItem, FakeBase):
    pass


class MaterialDelivery(MaterialTransfer, FakeBase):
    pass


class MaterialDeliveryItem(PartItem, FakeBase):
    pass


class MaterialDeliveryReturn(MaterialTransfer, FakeBase):
    pass


class MaterialDeliveryReturnItem(PartItem, FakeBase):
    pass


class OtherMaterialTransfer(MaterialTransfer, FakeBase):
    pass


class OtherMaterialTransferItem(PartItem, FakeBase):
    pass


"""
Manufacture
"""



class MasterProductionSchedule:
    """
    MPS相较于MRP，主要区别在于其目标是加入人为干预后形成持续的，平稳的生产计划
    而依据MRP具有较大的波动性，
    """


class MaterialRequirementPlan:
    """
    MRP
    """
    part_fk = Column(Text)
    due_date = Column(BigInteger)
    source = Column(Text)
    source_fk = Column(Text)


class CapacityRequirementPlan:
    """
    CRP
    """
    pass


class WorkOrder(BusinessActivity, FakeBase):
    pass


class WorkOrderItem(PrimeEntity, FakeBase):
    order_fk = Column(ForeignKey('work_order.id'))
    item = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    memo = Column(Text)


class MaterialIssue(MaterialTransfer, FakeBase):
    pass


class MaterialIssueReturn(MaterialTransfer, FakeBase):
    pass


class MaterialPick(MaterialTransfer, FakeBase):
    pass


"""
Financial
"""


class FinancialAccount(VersionEntity, NodeMixin, FakeBase):
    code = Column(Text)
    name = Column(Text)
    balance = Column(Numeric)
    category = Column(Text)

    def make_debit(self, amount):
        cat = AccountCategory(self.category)
        if cat.is_asset():
            self.balance += amount
        else:
            self.balance -= amount

    def make_credit(self, amount):
        cat = AccountCategory(self.category)
        if cat.is_asset():
            self.balance -= amount
        else:
            self.balance += amount


class GeneralJournal(VersionEntity, AuditMixin, FakeBase):
    date = Column(BigInteger)
    clerk = Column(Text)
    posted = Column(Boolean)
    amount = Column(Numeric)


class GeneralJournalItem(PrimeEntity, FakeBase):
    account_fk = Column(ForeignKey('general_journal.id'))
    memo = Column(Text)
    debit = Column(Numeric)
    credit = Column(Numeric)


class GeneralInvoice(PrimeEntity):
    code = Column(Text)
    date = Column(Text)
    flag = Column(Text)  # app_dict: invoice_flag
    type = Column(Text)  # app_dict: invoice_type
    amount = Column(Numeric)
    subject = Column(Text)  # @Partner.id
    note = Column(Text)
    memo = Column(Text)
    ref_docs = Column(JSONB)


class Currency(PrimeEntity, FakeBase):
    code = Column(Text)
    name = Column(Text)
    ex_rate = Column(Text)
    is_base = Column(Boolean)
    is_default = Column(Boolean)


class CashAccount(PrimeEntity, FakeBase):
    code = Column(Text)
    name = Column(Text)
    cash_type = Column(Text)
    bank_branch = Column(Text)
    bank_acct = Column(Text)
    cuy = Column(Text)  # @Currency.id
    init_balance = Column(Numeric)
    balance = Column(Numeric)
    is_default = Column(Boolean)


class InvoiceItem(PrimeEntity, FakeBase):
    part_fk = Column(Text)
    amount = Column(Numeric)


class SaleInvoice(GeneralInvoice, FakeBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.flag = '2'


class PurchaseInvoice(GeneralInvoice, FakeBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.flag = '1'




