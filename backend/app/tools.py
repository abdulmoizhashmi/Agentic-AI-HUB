# Safe mock tools for demonstrating tool calling. Replace with real APIs before production.
FAQ = [
    (["refund", "return", "money back"], "Refund requests are reviewed within 3–5 business days after the returned item is received."),
    (["password", "login", "sign in", "account"], "Use 'Forgot password' on the sign-in screen. If you no longer have access to your email, a support specialist should verify your account."),
    (["shipping", "delivery", "tracking", "order"], "Standard delivery usually takes 3–5 business days. Tracking details are sent after the order ships."),
    (["cancel", "cancellation"], "Orders can usually be cancelled before fulfilment. Please share the order reference so the team can check its status.")
]
ORDERS = {
    "DEMO-1001": {"status": "shipped", "eta": "2–3 business days", "tracking": "TRACK-DEMO-1001"},
    "DEMO-1002": {"status": "processing", "eta": "3–5 business days", "tracking": None}
}

def search_knowledge_base(query):
    text = query.lower()
    for words, answer in FAQ:
        if any(word in text for word in words):
            return {"found": True, "answer": answer, "source": "mock_faq"}
    return {"found": False, "answer": "No exact FAQ match. Ask a clarifying question or offer human review.", "source": "mock_faq"}

def lookup_order(order_id):
    return ORDERS.get(order_id.upper(), {"found": False, "message": "Order not found in demo data. Try DEMO-1001 or DEMO-1002."})

def detect_escalation(text):
    triggers = ["lawyer", "legal action", "fraud", "stolen card", "safety issue", "human agent", "real person", "supervisor"]
    return any(t in text.lower() for t in triggers)
