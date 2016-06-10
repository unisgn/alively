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

    id = Column(String, primary_key=True)

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
    created_by = Column(String)
    modified_at = Column(BigInteger)
    modified_by = Column(String)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.created_at = int(time.time() * 1000)
        self.modified_at = self.created_at


class BusinessEntity(VersionEntity, AuditMixin):

    number = Column(String)
    code = Column(String)
    name = Column(String)
    alias = Column(String)
    memo = Column(String)
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
    password = Column(String)
    name = Column(String)
    memo = Column(Text)
    emp_fk = Column(String)

    expire_date = Column(BigInteger)
    login_ip = Column(String)
    login_mac = Column(String)
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
    code = Column(String)
    name = Column(String)
    brief = Column(String)
    nullable = Column(Boolean)
    dict_type = Column(String(1))
    items = relationship('AppDictItem')


class AppDictItem(FakeBase, PrimeEntity):

    app_dict_fk = Column(String, ForeignKey('app_dict.id'))
    value = Column(String(64))
    text = Column(String(255))
    memo = Column(Text)


class Role(FakeBase, PrimeEntity):

    code = Column(String, unique=True, nullable=False)
    memo = Column(Text)
    name = Column(String)
    flag = Column(String(10))

    permissions = relationship('RolePermissionHeader')

    @staticmethod
    def update_permissions(pk, *permissions):
        Session.query(RolePermissionHeader).filter(RolePermissionHeader.role_fk == pk).delete(synchronize_session=False)
        Session.bulk_insert_mappings(RolePermissionHeader, [{'role_fk': pk, 'permission_fk': e} for e in permissions])


class UserRoleHeader(VoidEntity, FakeBase):

    user_fk = Column(String, ForeignKey('t_user.id'), primary_key=True)
    role_fk = Column(String, ForeignKey('role.id'), primary_key=True)


class Permission(PrimeEntity, NodeMixin, FakeBase):

    code = Column(String, unique=True, nullable=False)
    name = Column(String)
    memo = Column(Text)
    parent_fk = Column(String, ForeignKey('permission.id'))

    def save(self):
        self._update_leaf()
        super().save()
        return self


class RolePermissionHeader(VoidEntity, FakeBase):
    role_fk = Column(String, ForeignKey('role.id'), primary_key=True)
    permission_fk = Column(String, ForeignKey('permission.id'), primary_key=True)


class Department(VersionEntity, NodeMixin, FakeBase):

    code = Column(String(20))
    name = Column(String(64))
    memo = Column(Text)
    mgr = Column(String)

    parent_fk = Column(String, ForeignKey('department.id'))

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

    fkid = Column(String(64))
    fpath = Column(String(255))
    fname = Column(String(255))
    mime = Column(String(32))
    upload_date = Column(Integer)
    upload_by = Column(String)

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
    agent = Column(String)


class Customer(VersionEntity, AuditMixin, FakeBase):
    agent = Column(String)
    labels = Column(ARRAY(String))
    info = Column(JSONB)


class Vendor(VersionEntity, AuditMixin, FakeBase):
    pass


class Employee(VersionEntity, AuditMixin, FakeBase):

    info = Column(JSONB)


"""
Part
"""


class Part(BusinessEntity, NodeMixin, FakeBase):
    is_bom = Column(Boolean)
    category_fk = Column(String)
    uom_fk = Column(String)

    labels = Column(ARRAY(String))

    parent_fk = Column(String)

    on_hand = Column(Numeric)
    on_demand = Column(Numeric)
    on_order = Column(Numeric)

    cost_avg = Column(Numeric)
    cost_std = Column(Numeric)


class PartCategory(VersionEntity, NodeMixin, FakeBase):
    name = Column(String)
    memo = Column(Text)


class PartLabelGroup(VersionEntity, FakeBase):
    name = Column(String)
    category_fk = Column(String, ForeignKey('part_category.id'))


class PartLabel(VersionEntity, FakeBase):
    name = Column(String)
    group_fk = Column(String, ForeignKey('part_label_group.id'))


class Uom(VersionEntity, FakeBase):
    """
    Unit of measure
    """
    code = Column(String)
    name = Column(String)
    ratio = Column(Numeric)
    group_fk = Column(String)
    is_base = Column(Boolean)


class UomGroup(VersionEntity, FakeBase):
    name = Column(String)


class Warehouse(VersionEntity, NodeMixin, FakeBase):
    keeper = Column(String)
    code = Column(String)
    name = Column(String)
    memo = Column(Text)


class Stock(PrimeEntity, FakeBase):
    warehouse_fk = Column(ForeignKey('warehouse.id'))
    part_fk = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    uom_fk = Column(String)


class MaterialRequirement(PrimeEntity, FakeBase):
    pass

"""
business activity
"""


class BusinessActivity(VersionEntity, AuditMixin):

    ref_docs = Column(JSONB)
    public_notes = Column(JSONB)
    private_notes = Column(JSONB)
    attachments = Column(JSONB)

    @property
    def channel(self):
        return self.__class__.__name__ + '#' + self.id


class SaleQuotation(BusinessActivity, FakeBase):
    customer_fk = Column(ForeignKey('customer.id'))
    agent = Column(String)


class SaleQuotationItem(PrimeEntity, FakeBase):
    pass


class SaleOrder(BusinessActivity, FakeBase):
    customer_fk = Column(String)
    agent = Column(String)
    contacts = Column(JSONB)
    total_tax = Column(Numeric)
    total_amount = Column(Numeric)
    discount = Column(Numeric)
    due_date = Column(BigInteger)


class SaleOrderItem(PrimeEntity, FakeBase):
    order_fk = Column(ForeignKey('sale_order.id'))
    item = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    price = Column(Numeric)
    tax = Column(Numeric)
    amount = Column(Numeric)
    memo = Column(Text)
    due_date = Column(BigInteger)


class MaterialReturnBill(BusinessActivity, FakeBase):
    """
    RMA, Return Material Authorization, 退货单
    """
    pass


class PurchaseOrder(BusinessActivity, FakeBase):
    customer_fk = Column(String)
    agent = Column(String)
    total_tax = Column(Numeric)
    total_amount = Column(Numeric)
    discount = Column(Numeric)
    due_date = Column(BigInteger)


class PurchaseOrderItem(PrimeEntity, FakeBase):
    order_fk = Column(ForeignKey('purchase_order.id'))
    item = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    price = Column(Numeric)
    tax = Column(Numeric)
    amount = Column(Numeric)
    memo = Column(Text)


class QuotationRequest(BusinessActivity, FakeBase):
    """
    RFQ: Request for quotation，询价单
    """


class WorkOrder(BusinessActivity, FakeBase):
    pass


class WorkOrderItem(PrimeEntity, FakeBase):
    order_fk = Column(ForeignKey('work_order.id'))
    item = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    memo = Column(Text)


class MaterialBilItem(PrimeEntity, FakeBase):
    item = Column(ForeignKey('part.id'))
    lot = Column(Numeric)
    memo = Column(Text)
    warehouse_fk = Column(ForeignKey('warehouse.id'))
    bill_fk = Column(ForeignKey('material_bill.id'))


class MaterialBill(PrimeEntity, FakeBase):
    trans_in = Column(Boolean)
    items = relationship('MaterialBilItem')


class MaterialTransfer(BusinessActivity):

    @declared_attr
    def bill_fk(self):
        return Column(ForeignKey('material_bill.id'))

    @declared_attr
    def bill(self):
        return relationship('MaterialBill')


class MaterialReceipt(MaterialTransfer, FakeBase):
    pass


class MaterialDelivery(MaterialTransfer, FakeBase):
    pass


class MaterialIssue(MaterialTransfer, FakeBase):
    pass


class MaterialPick(MaterialTransfer, FakeBase):
    pass


class InvoiceSale(BusinessActivity, FakeBase):
    pass


class InvoiceReceipt(BusinessActivity, FakeBase):
    pass


class InvoicePurchase(BusinessActivity, FakeBase):
    pass


class InvoicePayment(BusinessActivity, FakeBase):
    pass

"""
Financial
"""


class FinancialAccount(VersionEntity, NodeMixin, FakeBase):
    code = Column(String)
    name = Column(String)
    balance = Column(Numeric)


class GeneralJournal(VersionEntity, AuditMixin, FakeBase):
    date = Column(BigInteger)
    clerk = Column(String)
    posted = Column(Boolean)
    amount = Column(Numeric)


class FinancialJournalItem(PrimeEntity, FakeBase):
    account_fk = Column(ForeignKey('general_journal.id'))
    memo = Column(Text)
    credit = Column(Numeric)
    debit = Column(Numeric)



