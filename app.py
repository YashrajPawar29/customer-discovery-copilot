"""Customer Discovery Copilot - Streamlit app.

Run with:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import streamlit as st

from discovery import ai
from discovery.heuristics import (LABEL_COMPLIMENT, LABEL_EVIDENCE, LABEL_OPINION,
                                  analyze_interview, coaching_prompts, demo_summary,
                                  themes)

SAMPLES = Path(__file__).parent / "sample_interviews"

st.set_page_config(page_title="Customer Discovery Copilot", page_icon="🔎", layout="wide")
st.title("🔎 Customer Discovery Copilot")
st.caption("Turn raw customer interviews into evidence: what people *did*, not what they "
           "*said they'd do*.")

with st.sidebar:
    st.header("Your venture")
    hypothesis = st.text_area(
        "Problem hypothesis",
        "College students waste hours finding on-campus jobs because listings are out of date.",
        height=110)
    use_samples = st.checkbox("Load sample interviews", value=True)
    uploads = st.file_uploader("Upload transcripts (.txt)", type=["txt"],
                               accept_multiple_files=True)
    st.markdown("**Format:** one line per turn, e.g.  \n`Interviewer: ...`  \n`Customer: ...`")
    st.divider()
    mode_ai = st.toggle("Use Claude for deep synthesis", value=False,
                        disabled=not ai.is_available(),
                        help="Set ANTHROPIC_API_KEY to enable. Offline rules are used otherwise.")

interviews = {}
if use_samples:
    for p in sorted(SAMPLES.glob("*.txt")):
        interviews[p.stem] = p.read_text()
for f in uploads or []:
    interviews[Path(f.name).stem] = f.read().decode("utf-8", errors="ignore")

if not interviews:
    st.info("Upload at least one transcript, or tick **Load sample interviews**.")
    st.stop()

analyses = [analyze_interview(name, text) for name, text in interviews.items()]

st.subheader("Evidence scorecard")
st.write(demo_summary(analyses))
rows = []
for a in analyses:
    c = a.label_counts
    rows.append({"Interview": a.name,
                 "Evidence": c.get(LABEL_EVIDENCE, 0),
                 "Opinion": c.get(LABEL_OPINION, 0),
                 "Compliments": c.get(LABEL_COMPLIMENT, 0),
                 "Pain signals": len(a.pains),
                 "Weak questions": len(a.question_flags),
                 "Evidence %": round(a.evidence_ratio * 100)})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

tab_coach, tab_themes, tab_q, tab_raw, tab_ai = st.tabs(
    ["🧭 Coaching questions", "🧩 Recurring themes", "❓ Interview technique",
     "📄 Statement by statement", "🤖 Claude synthesis"])

with tab_coach:
    st.markdown("Questions a coach would ask your team before the next workshop:")
    for q in coaching_prompts(analyses):
        st.markdown(f"- {q}")

with tab_themes:
    found = themes(analyses)
    if not found:
        st.write("No pain words repeat across interviews yet.")
    for word, n, names in found:
        st.markdown(f"**{word}** - in {n} interviews ({', '.join(names)})")
    st.caption("Words customers used in more than one interview - a first hint at shared problems.")

with tab_q:
    for a in analyses:
        with st.expander(f"{a.name} - {len(a.question_flags)} weak question(s)"):
            for f in a.question_flags:
                st.error(f"**{f.issue}:** “{f.question}”  \n{f.advice}")
            for q in a.strong_questions:
                st.success(f"Good question: “{q}”")

with tab_raw:
    colour = {LABEL_EVIDENCE: "🟢", LABEL_OPINION: "🟡", LABEL_COMPLIMENT: "🔴"}
    for a in analyses:
        with st.expander(a.name):
            for label, text in a.statements:
                st.markdown(f"{colour.get(label, '⚪')} *{label}* - {text}")

with tab_ai:
    if not mode_ai:
        st.info("Turn on **Use Claude for deep synthesis** in the sidebar (needs an API key). "
                "Claude clusters pains, quotes customers, and maps which assumptions were "
                "supported, contradicted, or still untested.")
    elif st.button("Run synthesis", type="primary"):
        with st.spinner("Claude is reading the interviews..."):
            try:
                result = ai.synthesize(interviews, hypothesis)
            except Exception as e:  # show the error in the UI rather than crash
                st.error(str(e))
                st.stop()
        st.markdown(f"### Summary\n{result['summary']}")
        st.markdown("### Pain points")
        st.dataframe(pd.DataFrame(result["pain_points"]), use_container_width=True,
                     hide_index=True)
        st.markdown("### Assumptions")
        st.dataframe(pd.DataFrame(result["assumptions"]), use_container_width=True,
                     hide_index=True)
        st.warning(f"**Riskiest assumption:** {result['riskiest_assumption']}")
        st.success(f"**Cheapest next test:** {result['cheapest_next_test']}")
        st.markdown("### Ask next time")
        for q in result["next_interview_questions"]:
            st.markdown(f"- {q}")
        st.markdown("### Coach's questions for the team")
        for q in result["coaching_questions"]:
            st.markdown(f"- {q}")
