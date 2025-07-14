import os
import re
from langsmith import traceable
from typing import Dict, List, Optional

from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage
from models import PlannerResponseModel

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    temperature=0.1,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    response_mime_type="application/json"
)

@traceable(name="Planner Decision (Gemini)")
async def get_planner_llm_response(
    query: str,
    tools: Dict[str, callable],
    memory: Optional[List[dict]] = None
) -> str:
    tool_descriptions = "\n".join([
        f"- {name}: {fn.__doc__ or 'No description provided'}"
        for name, fn in tools.items()
    ])

    context_summary = ""
    if memory:
        for i, m in enumerate(memory):
            step = m.get("step_summary", "") or m.get("task_query", "")
            context_summary += f"- Step {i + 1}: {step}\n"
    else:
        context_summary = "No previous steps."

    prompt = (
        "You are a planner agent that decides which tool to use to fulfill a user request.\n\n"
        "You must only respond with `final: true` if the task is purely descriptive or conversational."

        "If the task involves creating, generating, or manipulating 3D models, always call the appropriate tool — such as `RunBlenderScript`."

        "Never generate 3D descriptions or stories when tools are available to fulfill the request visually."

        "If a user asks to \"make\", \"build\", \"create\", \"model\", or \"render\" anything — it MUST be done via tool call."

        "If the user’s request involves fetching or saving data, always call a tool.\n\n"
        "In this session, multiple tools may need to be used in sequence before you respond with `final: true`.\n\n"
        "You must respond with a valid JSON structure:\n"
        '{\n'
        '  "final": false,\n'
        '  "tool_call": "WebReader",\n'
        '  "tool_input": {"url": "https://example.com"},\n'
        '  "answer": "Reading the webpage now."\n'
        '}\n'
        "OR:\n"
        '{\n'
        '  "final": true,\n'
        '  "answer": "The current time is 3:14 PM."\n'
        '}\n\n'
        "Only use available tools. Don't invent tool names.\n\n"
        "When `final` is true, you must include the actual values returned by tools (like timestamps or summaries). "
        "Do not say 'OK' or 'Saved' — always include the actual result value in your response.\n\n"
        f"Available tools:\n{tool_descriptions}\n\n"
        f"User Query:\n{query}\n\n"
        f"Tool Call History:\n{context_summary}\n\n"
        "Respond with the next step or final answer as valid JSON.\n\n"
        "If none of the tools are suitable for the task, and the request is general knowledge, creative writing, or opinion-based,"
        "respond directly with `final: true` and a helpful answer as if you were answering without tools.\n"

        "Use tools only when they're needed for fetching data, saving, transforming input, or accessing external sources."

       " When generating a Blender script:"
       " - The script will automatically clear existing objects."
       " - It will calculate the bounding box for all geometric objects (meshes, curves, etc.)."
       " - It will dynamically position the camera to frame the entire scene."
       " - It will add basic lighting if none is present."
       " - To apply a texture, include a `texture` parameter in the `RunBlenderScript` tool call (e.g., `\"texture\": \"checker\"`)."

    )

    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content.strip()

def parse_planner_output(raw: str) -> PlannerResponseModel:
    try:
        if raw.startswith("```json"):
            raw = raw[7:-3].strip()
        return PlannerResponseModel.model_validate_json(raw)
    except Exception:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return PlannerResponseModel.model_validate_json(match.group())
        except Exception:
            pass
        return PlannerResponseModel(final=True, answer="❌ Could not parse Gemini planner output.")
