from pydantic import BaseModel
from typing import Optional, List, Any

class PlannerResponseModel(BaseModel):
    final: bool
    tool_call: Optional[str] = None
    tool_input: Optional[dict] = None
    answer: str

class StepDetailModel(BaseModel):
    step: int
    ts: str
    tool: Optional[str] = None
    input: Optional[Any] = None
    output: Optional[Any] = None

class AgentState(BaseModel):
    detailed_steps_buffer: List[StepDetailModel] = []
    memory: List[dict] = []
