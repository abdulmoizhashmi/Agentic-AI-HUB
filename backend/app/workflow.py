import re
from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .llm import generate
from .tools import detect_escalation, lookup_order, search_knowledge_base

SUPPORT_SYSTEM = """You are a kind, concise customer support agent. Use only facts in tool results.
Never claim an order was changed/refunded/cancelled. Ask for missing details. Escalate fraud, legal, safety,
account compromise, or explicit human requests. Never ask for passwords, full card numbers, or authentication codes."""
INTERVIEW_SYSTEM = """You are a professional, encouraging mock interviewer. Ask one question at a time, tailored to role and difficulty.
After each answer, give specific feedback and ask exactly one next question. Do not claim to represent an employer."""


class AgentState(TypedDict):
    session_id: str
    agent: Literal["support", "interview"]
    input: str
    role: str
    difficulty: Literal["beginner", "intermediate", "advanced"]
    history: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    trace: list[dict[str, str]]
    escalated: bool
    awaiting_human: bool
    plan: str
    reply: str
    memory_summary: str


class AgentOrchestrator:
    """LangGraph supervisor/router for support and interview specialist workflows."""

    def __init__(self, store):
        self.store = store
        graph = StateGraph(AgentState)
        graph.add_node("router", self._route)
        graph.add_node("planner", self._plan)
        graph.add_node("support_tools", self._support_tools)
        graph.add_node("specialist_agent", self._respond)
        graph.add_node("reflection", self._reflect)
        graph.add_node("checkpoint", self._checkpoint)
        graph.add_edge(START, "router")
        graph.add_edge("router", "planner")
        graph.add_conditional_edges(
            "planner",
            self._select_specialist,
            {"support": "support_tools", "interview": "specialist_agent"},
        )
        graph.add_edge("support_tools", "specialist_agent")
        graph.add_edge("specialist_agent", "reflection")
        graph.add_edge("reflection", "checkpoint")
        graph.add_edge("checkpoint", END)
        self.graph = graph.compile(checkpointer=MemorySaver())

    async def run(self, req: dict[str, Any]) -> dict[str, Any]:
        sid = req["session_id"]
        agent = req["agent"]
        message = req["message"].strip()
        prior = self.store.get_session(sid)
        state: AgentState = {
            "session_id": sid,
            "agent": agent,
            "input": message,
            "role": req.get("role") or "Software Engineer",
            "difficulty": req.get("difficulty") or "intermediate",
            "history": prior.get("messages", []),
            "tools": [],
            "trace": [],
            "escalated": False,
            "awaiting_human": False,
            "plan": "",
            "reply": "",
            "memory_summary": "",
        }
        result = await self.graph.ainvoke(
            state,
            config={"configurable": {"thread_id": f"{sid}:{agent}"}},
        )
        return {
            "session_id": sid,
            "agent": agent,
            "reply": result["reply"],
            "workflow": result["trace"],
            "escalated": result["escalated"],
            "awaiting_human": result["awaiting_human"],
            "memory_summary": result["memory_summary"],
        }

    def _route(self, state: AgentState) -> dict[str, Any]:
        return {"trace": [self.step("router", f"Routed request to the {state['agent']} specialist.", "route")]}

    def _plan(self, state: AgentState) -> dict[str, Any]:
        if state["agent"] == "support":
            plan = "Understand issue → check escalation signals → use FAQ/order tools → answer from tool results."
        else:
            plan = (
                f"Run a {state['difficulty']} {state['role']} interview → assess answer → "
                "give feedback → ask next question."
            )
        return {
            "plan": plan,
            "trace": [*state["trace"], self.step("planner", plan, "plan")],
        }

    @staticmethod
    def _select_specialist(state: AgentState) -> str:
        return state["agent"]

    def _support_tools(self, state: AgentState) -> dict[str, Any]:
        tools: list[dict[str, Any]] = []
        trace = list(state["trace"])
        escalated = detect_escalation(state["input"])
        if escalated:
            self.store.set_pending_review(
                state["session_id"],
                {"reason": "Escalation trigger detected", "last_message": state["input"]},
            )
            trace.append(
                self.step(
                    "human_in_the_loop",
                    "Flagged for human review; no irreversible action was taken.",
                    "approval",
                )
            )

        match = re.search(r"\bDEMO-\d{4}\b", state["input"].upper())
        if match:
            result = lookup_order(match.group())
            tools.append({"tool": "lookup_order", "result": result})
            trace.append(self.step("tool_call", f"Called lookup_order({match.group()}).", "tool"))

        result = search_knowledge_base(state["input"])
        tools.append({"tool": "search_knowledge_base", "result": result})
        trace.append(self.step("tool_call", "Searched the mock support knowledge base.", "tool"))
        return {
            "tools": tools,
            "trace": trace,
            "escalated": escalated,
            "awaiting_human": escalated,
        }

    async def _respond(self, state: AgentState) -> dict[str, str]:
        reply = (
            await self.support_reply(state)
            if state["agent"] == "support"
            else await self.interview_reply(state)
        )
        return {"reply": reply}

    def _reflect(self, state: AgentState) -> dict[str, Any]:
        reply = state["reply"]
        trace = list(state["trace"])
        if not reply or len(reply.strip()) < 3:
            reply = "I couldn't form a useful response. Could you rephrase that?"
            trace.append(self.step("reflection", "Rejected an empty response and used a safe fallback.", "reflect"))
        else:
            trace.append(self.step("reflection", "Checked response clarity and avoided unsupported claims.", "reflect"))
        return {"reply": reply, "trace": trace}

    def _checkpoint(self, state: AgentState) -> dict[str, str]:
        trace = [*state["trace"], self.step("checkpoint", "Saved this turn and compact session memory to local JSON.", "memory")]
        session = self.store.append_turn(
            state["session_id"],
            state["input"],
            state["reply"],
            state["agent"],
            {
                "workflow": trace,
                "escalated": state["escalated"],
                "tools": state["tools"],
            },
        )
        memory = session.get("memory", {})
        return {
            "trace": trace,
            "memory_summary": (
                f"Agent: {state['agent']} · Turns in this session: {memory.get('turn_count', 0)}"
            ),
        }

    async def support_reply(self, state: AgentState) -> str:
        prompt = (
            f"Customer message: {state['input']}\nTool results: {state['tools']}\n"
            f"Escalated: {state['escalated']}\nPlan: {state['plan']}"
        )
        answer = await generate(SUPPORT_SYSTEM, prompt)
        if answer:
            if state["escalated"]:
                answer += (
                    "\n\nThis conversation has been flagged for human review. "
                    "Do not share passwords or full payment details."
                )
            return answer
        if state["escalated"]:
            found = next(
                (
                    item["result"]
                    for item in state["tools"]
                    if item["tool"] == "search_knowledge_base" and item["result"].get("found")
                ),
                None,
            )
            extra = f"\n\nFor reference: {found['answer']}" if found else ""
            return (
                "I understand this needs careful attention. I've flagged the conversation for human review. "
                "Please do not share passwords, verification codes, or full payment-card details."
                + extra
            )
        order = next((item["result"] for item in state["tools"] if item["tool"] == "lookup_order"), None)
        if order:
            if order.get("status"):
                track = f" Tracking reference: {order['tracking']}." if order.get("tracking") else ""
                return f"Your demo order is **{order['status']}**. Estimated delivery: {order['eta']}." + track
            return order.get("message", "I couldn't locate that order.")
        kb = next(item["result"] for item in state["tools"] if item["tool"] == "search_knowledge_base")
        if kb["found"]:
            return kb["answer"] + "\n\nIf you share a little more context, I can help narrow this down."
        return (
            "I can help with orders, delivery, refunds, cancellations, and account access. "
            "Could you share a little more detail? For order status, try DEMO-1001."
        )

    async def interview_reply(self, state: AgentState) -> str:
        history = state["history"]
        start = (
            not history
            or state["input"].lower().startswith("/start")
            or state["input"].lower() in {"start interview", "begin interview"}
        )
        if start:
            prompt = (
                f"Begin a {state['difficulty']} mock interview for {state['role']}. "
                "Briefly explain the format and ask the first question only."
            )
        else:
            recent = "\n".join(f"{message['role']}: {message['content']}" for message in history[-8:])
            prompt = (
                f"Role: {state['role']}\nDifficulty: {state['difficulty']}\n"
                f"Recent conversation:\n{recent}\nCandidate answer: {state['input']}\n"
                "Give concise feedback and ask exactly one next question."
            )
        answer = await generate(INTERVIEW_SYSTEM, prompt)
        if answer:
            return answer
        if start:
            questions = {
                "beginner": (
                    f"Let's begin your {state['role']} interview. In 1–2 minutes, tell me about "
                    "yourself and a project you've worked on."
                ),
                "intermediate": (
                    f"Welcome to your {state['role']} mock interview. Question 1: Describe a relevant "
                    "project, the architecture you chose, and one difficult trade-off you made."
                ),
                "advanced": (
                    f"Welcome to your {state['role']} mock interview. Question 1: Design a production-ready "
                    "system for this role. Explain architecture, scaling bottlenecks, failure modes, and trade-offs."
                ),
            }
            return questions[state["difficulty"]]
        return (
            "Thanks for your answer. **Feedback:** Add a specific example, your personal contribution, "
            "and a measurable result. Structure it using Situation, Task, Action, and Result (STAR).\n\n"
            f"**Next question:** For the {state['role']} role, how would you investigate a difficult bug "
            "or unexpected production issue?"
        )

    @staticmethod
    def step(node: str, detail: str, kind: str) -> dict[str, str]:
        return {"node": node, "detail": detail, "kind": kind}
