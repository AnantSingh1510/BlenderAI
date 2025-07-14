from tools import TOOL_REGISTRY
from planner import get_planner_llm_response, parse_planner_output
from models import AgentState, StepDetailModel
from datetime import datetime

class MiniPlannerAgent:
    def __init__(self):
        self.tools = TOOL_REGISTRY
        self.state = AgentState()

    async def run(self, user_input: str) -> str:
        original_user_input = user_input
        self.state.memory.append({"step_summary": f"User requested: {original_user_input}"})
        is_final = False

        while not is_final:
            planner_output_raw = await get_planner_llm_response(
                original_user_input, self.tools, self.state.memory
            )

            planner_decision = parse_planner_output(planner_output_raw)

            self._log_step("Planner", user_input, planner_decision.answer)

            if planner_decision.final:
                return planner_decision.answer

            tool = self.tools.get(planner_decision.tool_call)
            if not tool:
                return f"Unknown tool: {planner_decision.tool_call}"

            tool_result = await tool(planner_decision.tool_input or {})
            self._log_step(planner_decision.tool_call, planner_decision.tool_input, tool_result)

            self.state.memory.append({
                "step_summary": f"Tool `{planner_decision.tool_call}` returned: {tool_result}"
            })

    def _log_step(self, tool, input_data, output_data):
        step = StepDetailModel(
            step=len(self.state.detailed_steps_buffer) + 1,
            ts=datetime.utcnow().isoformat(),
            tool=tool,
            input=input_data,
            output=output_data,
        )

        print(f"\n>>> Step {step.step}: {tool}")
        print(f"Input: {input_data}")
        print(f"Output: {output_data}\n")

        self.state.detailed_steps_buffer.append(step)

