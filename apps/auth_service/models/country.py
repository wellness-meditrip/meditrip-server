from common.base import Base 
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship


class Country(Base):
    __tablename__ = "meditrip_country"

    id = Column(Integer, primary_key=True)
    name = Column(String)

    users = relationship("User", back_populates="country_obj")