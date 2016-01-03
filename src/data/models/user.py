from flask_login import UserMixin
from sqlalchemy.schema import Column
from sqlalchemy.types import Boolean, Integer, String
from sqlalchemy.orm import relationship

from ..database import db
from ..mixins import CRUDModel
from ..util import generate_random_token
from ...settings import app_config
from ...extensions import bcrypt
from .vazby import User_has_group

class User(CRUDModel, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    activate_token = Column(String(128), nullable=False, doc="Activation token for email verification")
    email = Column(String(64), nullable=False, unique=True, index=True, doc="The user's email address.")
    password_hash = Column(String(128))
    username = Column(String(64), nullable=False, unique=True, index=True, doc="The user's username.")
    verified = Column(Boolean(name="verified"), nullable=False, default=False)
    card_number = Column(String(32), unique=False, index=True, doc="Card access number")
    name = Column(String(60), unique=False, index=True, doc="Name")
    second_name = Column(String(60), unique=False, index=True, doc="Second name")
    access = Column(String(1), index=True, doc="Access")
    chip_number = Column(String(10), unique=True, index= False, doc= "Chip number", nullable=True)

    group = relationship(User_has_group, backref='user')

    # Use custom constructor
    # pylint: disable=W0231
    def __init__(self, **kwargs):
        self.activate_token = generate_random_token()
        self.access='A'
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    @staticmethod
    def find_by_email(email):
        return db.session.query(User).filter_by(email=email).scalar()

    @staticmethod
    def find_by_username(username):
        return db.session.query(User).filter_by(username=username).scalar()

    # pylint: disable=R0201
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password, app_config.BCRYPT_LOG_ROUNDS)

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_verified(self):
        " Returns whether a user has verified their email "
        return self.verified is True

    @staticmethod
    def find_by_number(card_number):
        return db.session.query(User).filter_by(card_number=card_number).scalar()

    @staticmethod
    def find_by_chip(chip_number):
        return db.session.query(User.id).filter_by(chip_number=chip_number).scalar()

    @staticmethod
    def all_users():
        return db.session.query(User.id, User.name, User.second_name).all()

    @staticmethod
    def all_names():
        return db.session.query(User.name).all()

    @staticmethod
    def ingroup():
        return db.session.query(User.id, User.name, User.second_name)

    @staticmethod
    def findUserById(id):
        return db.session.query(User.id, User.name, User.second_name).filter_by(id=id).all()

    @staticmethod
    def user_in_group():
        return db.session.query(User.id, User.name, User.second_name, User_has_group.group_id).join(User.group).all()

    @staticmethod
    def oneUserById(id):
        return db.session.query(User.name, User.second_name).filter_by(id=id).all()