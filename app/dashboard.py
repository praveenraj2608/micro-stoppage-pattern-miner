"""Streamlit dashboard — a thin client over the FastAPI backend.

Accessibility notes:
  * status uses text + icon, never colour alone (WCAG 1.4.1)
  * high-contrast native Streamlit theme; legible default font sizes
  * every finding carries a plain-language explanation (explainability)
"""
from __future__ import annotations

import requests
import streamlit as st

# Config base URL (kept simple; matches config.yaml default).
API = st.sidebar.text_input("API base URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Micro-Stoppage Pattern Miner", layout="wide")
st.title("Micro-Stoppage Pattern Miner")
st.caption("Linking short interruptions to recurring causes — contract manufacturing pilot")


def api_get(path):
    try:
        return requests.get(f"{API}{path}", timeout=30).json()
    except Exception as e:
        st.error(f"Cannot reach API at {API} — is FastAPI running? ({e})")
        return None


def api_post(path, **kw):
    try:
        return requests.post(f"{API}{path}", timeout=60, **kw).json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


col_run, col_info = st.columns([1, 3])
with col_run:
    if st.button("Run miner", type="primary"):
        with st.spinner("Mining recurring causes..."):
            api_post("/run")
        st.success("Run complete.")

findings = api_get("/findings") or []
conv = api_get("/metrics") or {}

# --- Top-line conversion metric (the judged value) ---
st.subheader("Hidden downtime converted to verified corrective actions")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Recurring causes found", conv.get("total_findings", 0))
m2.metric("Verified actions", conv.get("verified_actions", 0))
m3.metric("Recoverable min (verified)", conv.get("verified_recoverable_min", 0.0))
m4.metric("Recoverable min (all)", conv.get("total_recoverable_min", 0.0))

st.divider()

if not findings:
    st.info("No findings yet. Click **Run miner** (ensure synthetic data is generated).")
    st.stop()

st.subheader("Ranked recurring causes")
for f in findings:
    v = f.get("verification")
    status_icon = "•"
    status_txt = "Unreviewed"
    if v:
        if v["decision"] == "verified":
            status_icon, status_txt = "[VERIFIED]", "Verified"
        elif v["decision"] == "rejected":
            status_icon, status_txt = "[REJECTED]", "Rejected"

    with st.expander(
        f"#{f['rank']}  {f['cause_label'].title()}  —  ~{f['recoverable_min']} min  "
        f"({status_icon} {status_txt})",
        expanded=(f["rank"] == 1),
    ):
        st.write(f["plain_language"])
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Events", f["events"])
        c2.metric("Confidence", f"{int(f['confidence']*100)}%")
        c3.metric("Lift", f"{f['lift']}x")
        c4.metric("Impact score", f["impact"])
        st.write(f"**Context:** {f['context']}")
        if f["example_notes"]:
            st.write("**Example operator notes:** " +
                     ", ".join(f'"{n}"' for n in f["example_notes"]))
        st.write(f"**Suggested corrective action:** {f['suggested_action']}")

        st.markdown("**Verify this finding:**")
        owner = st.text_input("Action owner", key=f"owner_{f['finding_id']}")
        action = st.text_input("Corrective action", key=f"act_{f['finding_id']}",
                               value=f["suggested_action"])
        b1, b2 = st.columns(2)
        if b1.button("Verify & assign", key=f"v_{f['finding_id']}"):
            api_post(f"/findings/{f['finding_id']}/verify",
                     json={"decision": "verified", "verified_by": "pilot-user",
                           "action_owner": owner, "action_text": action})
            st.rerun()
        if b2.button("Reject", key=f"r_{f['finding_id']}"):
            api_post(f"/findings/{f['finding_id']}/verify",
                     json={"decision": "rejected", "verified_by": "pilot-user"})
            st.rerun()

st.divider()
with st.expander("Baseline comparison (current practice)"):
    base = api_get("/baseline") or {}
    st.write(f"Total micro-stoppage minutes (lumped, no cause): "
             f"**{base.get('lumped_bucket_min', 0)} min**")
    st.write(f"Distinct raw note strings (no unification): "
             f"**{base.get('distinct_raw_notes', 0)}**")
    st.write("Baseline attributes **0 min** to any recurring cause — that is the "
             "hidden downtime this tool surfaces.")
