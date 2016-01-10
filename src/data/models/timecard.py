from sqlalchemy import Time, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, String
from ..mixins import CRUDModel
from ..database import db


class Timecard(CRUDModel):
    __tablename__ = 'timecard'

    id = Column(Integer, primary_key=True)
    timecard_name = Column("timecard_name", String(30), nullable=False, index=True)
    timecard_head = Column("timecard_head", String(30), nullable=False, index=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)


    @staticmethod
    def getTimecardList():
        return db.session.query(Timecard.id, Timecard.timecard_name, Timecard.timecard_head).all()

    @staticmethod
    def getName(id):
        return db.session.query(Timecard.timecard_name).filter_by(id=id).first()

    @staticmethod
    def getIdAndName():
        return db.session.query(Timecard.id, Timecard.timecard_head).all()

    @staticmethod
    def getIdName():
        return db.session.query(Timecard.id, Timecard.timecard_name).all()