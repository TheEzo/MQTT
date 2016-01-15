from sqlalchemy import Time, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, String
from ..mixins import CRUDModel
from ..database import db
from .timecard import Timecard

class Group_has_timecard(CRUDModel):
    __tablename__ = 'group_has_timecard'

    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)
    timecard_id = Column(Integer, ForeignKey('timecard.id'), primary_key=True)
    timecard = relationship("Timecard", backref="group_has_timecard")

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    @staticmethod
    def findTimecard(id):
        return db.session.query(Group_has_timecard.timecard_id).filter_by(group_id=id).all()

    @staticmethod
    def findToDelete(timecard, group):
        return db.session.query(Group_has_timecard.group_id).filter(Group_has_timecard.group_id == group, Group_has_timecard.timecard_id == timecard).delete()

    @staticmethod
    def timecard_in_group():
        return db.session.query(Group_has_timecard.id, Group_has_timecard.group_id, Timecard.id, Timecard.timecard_name).join(Group_has_timecard.timecard).all()