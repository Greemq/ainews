from sqlalchemy import Column, String,  Integer, Enum
from sqlalchemy.orm import relationship
import enum
from src.models.base import BaseModel

class SourceType(enum.Enum):
    TENGRINEWS = "tengrinews"
    KAZINFORM = "kazinform"
    ZAKON = "zakon"
    NUR = "nur" 
    INFORMBURO = "informburo"

class Source(BaseModel):
    __tablename__ = "sources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    url = Column(String(512), nullable=False)
    type = Column(String(50), nullable=False)

    news = relationship("News", back_populates="source")

    @property
    def source_type(self) -> SourceType:
        return SourceType(self.type)

    @source_type.setter
    def source_type(self, value: SourceType):
        self.type = value.value

