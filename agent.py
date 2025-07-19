from tools import TOOL_REGISTRY
from planner import get_planner_llm_response, parse_planner_output
from models import AgentState, StepDetailModel
from datetime import datetime
import asyncio


class MiniPlannerAgent:
    def __init__(self, max_steps: int = 10):
        self.tools = TOOL_REGISTRY
        self.state = AgentState()
        self.max_steps = max_steps

    async def run(self, user_input: str) -> str:
        original_user_input = user_input
        self.state.memory.append({"step_summary": f"User requested: {original_user_input}"})

        step_count = 0

        while step_count < self.max_steps:
            try:
                # Get planner decision
                planner_output_raw = await get_planner_llm_response(
                    original_user_input, self.tools, self.state.memory
                )

                planner_decision = parse_planner_output(planner_output_raw)
                self._log_step("Planner", user_input, planner_decision.answer)

                if planner_decision.final:
                    return planner_decision.answer

                tool = self.tools.get(planner_decision.tool_call)
                if not tool:
                    error_msg = f"Unknown tool: {planner_decision.tool_call}"
                    self._log_step("Error", planner_decision.tool_call, error_msg)
                    self.state.memory.append({"step_summary": f"Error: {error_msg}"})
                    continue

                try:
                    tool_result = await tool(planner_decision.tool_input or {})
                    self._log_step(planner_decision.tool_call, planner_decision.tool_input, tool_result)

                    self.state.memory.append({
                        "step_summary": f"Tool `{planner_decision.tool_call}` returned: {tool_result}"
                    })

                except Exception as e:
                    error_msg = f"Tool execution failed: {str(e)}"
                    self._log_step(planner_decision.tool_call, planner_decision.tool_input, error_msg)
                    self.state.memory.append({"step_summary": f"Tool error: {error_msg}"})

                step_count += 1

            except Exception as e:
                error_msg = f"Planner error: {str(e)}"
                self._log_step("Error", user_input, error_msg)
                return f"Agent execution failed: {error_msg}"

        final_msg = f"Maximum steps ({self.max_steps}) reached. Task may be incomplete."
        self._log_step("System", "max_steps_reached", final_msg)
        return final_msg

    def _log_step(self, tool: str, input_data, output_data):
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

    def get_execution_summary(self) -> dict:
        return {
            "total_steps": len(self.state.detailed_steps_buffer),
            "memory_entries": len(self.state.memory),
            "steps": [
                {
                    "step": s.step,
                    "tool": s.tool,
                    "timestamp": s.ts,
                    "success": not s.output.startswith("Error") and not s.output.startswith("Tool execution failed")
                }
                for s in self.state.detailed_steps_buffer
            ]
        }

    def clear_state(self):
        self.state = AgentState()

    async def run_with_timeout(self, user_input: str, timeout_seconds: int = 300) -> str:
        try:
            return await asyncio.wait_for(self.run(user_input), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            timeout_msg = f"Agent execution timed out after {timeout_seconds} seconds"
            self._log_step("System", "timeout", timeout_msg)
            return timeout_msg