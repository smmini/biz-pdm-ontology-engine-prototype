from pydantic import BaseModel, Field
from typing import Optional

class OntologyNode(BaseModel):
    name: str
    description: Optional[str] = None
    available: bool = True
    category: str
    unit: Optional[str] = None
    
    # 추가로 Capability Detection에 필요한 메타 정보를 담을 수 있음
    # 예: is_sensor, is_cost_related 등
