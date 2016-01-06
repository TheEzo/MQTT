from sqlalchemy import Time, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, String
from ..mixins import CRUDModel
from .group import Group
from ..database import db

class User_has_group(CRUDModel):
    __tablename__ = 'user_has_group'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('groups.id'), primary_key=True)
    group = relationship("Group", backref="user_has_group")

    def __init__(self, user_id, group_id):
        self.user_id = user_id
        self.group_id = group_id

    @staticmethod
    def find_timecard_by_userid(id):
        group_id = db.session.query(User_has_group.group_id).filter_by(user_id=id).all()
        return Group.find_access_time(group_id)


    @staticmethod
    def getAll():
        return db.session.query(User_has_group.user_id, User_has_group.group_id).all()

    @staticmethod
    def usersInGroup(group_id):
        return db.session.query(User_has_group.user_id).filter_by(group_id=group_id).all()

    @staticmethod
    def getGroupName():
        return db.session.query(User_has_group.group_id, Group.group_name).all()

    @staticmethod
    def compareUsers(id):
        return db.session.query(User_has_group.group_id).filter_by(user_id=id).all()

    @staticmethod
    def findToDelete(user, group):
        return db.session.query(User_has_group.user_id).filter(User_has_group.user_id == user, User_has_group.group_id == group).delete()

