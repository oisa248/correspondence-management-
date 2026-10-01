"""All three workflows as state machines: type -> status -> available actions.
who: role names, or @originator / @approver / @dept (the assigned person)."""
PREFIX = {"incoming": "IN", "memo": "MEMO", "outgoing": "OUT"}
EXEC = ["ceo", "cto", "coo", "cco"]
CREATORS = {
    "incoming": ["record_officer"],
    "memo": EXEC + ["director", "department"],
    "outgoing": EXEC + ["department"],
}

def t(key, label, who, to=None, **kw): return dict(key=key, label=label, who=who, to=to, **kw)
def USER(name, label, roles=None): return dict(name=name, label=label, kind="user", roles=roles)
def TEXT(name, label, optional=False): return dict(name=name, label=label, kind="text", optional=optional)

SUBMIT = t("submit", "Send draft to Record Officer", ["@originator"], "ro_review")

WORKFLOWS = {
    "incoming": {"start": "registered", "states": {
        "registered": [t("route_to_ceo", "Route to CEO", ["record_officer"], "with_ceo")],
        "with_ceo": [t("assign", "Assign to department", ["ceo"], "with_department",
                       fields=[USER("assignee_id", "Responsible department", ["department"])])],
        "with_department": [
            t("update_progress", "Post progress update", ["@dept", "ceo", "record_officer"], None, note=True),
            t("complete", "Mark completed", ["@dept", "ceo"], "completed")],
    }},
    "memo": {"start": "draft", "states": {
        "draft": [SUBMIT],
        "ro_review": [t("finalize", "Finalize memo", ["record_officer"], "originator_review", ref=True)],
        "originator_review": [
            t("approve", "Approve and sign", ["@originator"], "approved", sign=True),
            t("reject", "Reject for revision", ["@originator"], "ro_review", note=True)],
        "approved": [
            t("distribute", "Send to recipient", ["record_officer", "@originator"], "sent",
              fields=[USER("assignee_id", "Recipient")]),
            t("complete", "Mark completed", ["@originator", "record_officer"], "completed")],
        "sent": [t("complete", "Mark completed", ["@originator", "@dept"], "completed")],
    }},
    "outgoing": {"start": "draft", "states": {
        "draft": [SUBMIT],
        "ro_review": [t("finalize", "Finalize and add official stamp", ["record_officer"], "pending_approval",
                        stamp=True, fields=[USER("approver_id", "Send for approval to", EXEC)])],
        "pending_approval": [
            t("approve", "Approve and sign", ["@approver"], "signed", sign=True,
              fields=[TEXT("category", "Category")]),
            t("reject", "Reject for revision", ["@approver"], "ro_review", note=True)],
        "signed": [t("register", "Add date and reference no., register", ["record_officer"], "registered",
                     ref=True, fields=[TEXT("cc", "CC recipients", optional=True)])],
        "registered": [t("distribute", "Send copies to CC recipients", ["record_officer"], "distributed")],
        "distributed": [t("complete", "Mark completed", ["@originator"], "completed")],
    }},
}

def allowed(who, item, u):
    return (u["role"] in who
            or ("@originator" in who and item["created_by"] == u["id"])
            or ("@approver" in who and item["approver_id"] == u["id"])
            or ("@dept" in who and item["assignee_id"] == u["id"]))

def actions_for(item, u):
    return [a for a in WORKFLOWS[item["type"]]["states"].get(item["status"], []) if allowed(a["who"], item, u)]

def visible(item, u):
    return u["role"] in ("record_officer", "ceo") or u["id"] in (
        item["created_by"], item["approver_id"], item["assignee_id"])
