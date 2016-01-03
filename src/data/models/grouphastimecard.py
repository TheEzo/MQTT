from sqlalchemy import Time, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, String
from ..mixins import CRUDModel
from ..database import db


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