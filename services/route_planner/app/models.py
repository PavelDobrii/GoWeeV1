from sqlalchemy import JSON, Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True)
    mode = Column(String(50), nullable=False)
    distance_m = Column(Integer, nullable=False)
    eta_min = Column(Integer, nullable=False)

    snapshot = relationship("RouteSnapshot", back_populates="route", uselist=False)


class RouteSnapshot(Base):
    __tablename__ = "route_snapshots"

    id = Column(Integer, primary_key=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    order = Column(JSON, nullable=False)
    distance_m = Column(Integer, nullable=False)
    eta_min = Column(Integer, nullable=False)

    route = relationship("Route", back_populates="snapshot")
