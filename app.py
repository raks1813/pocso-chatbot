import streamlit as st
import pandas as pd
import re
import os
st.markdown("""
<style>
body {
    background-color: #0b0f19;
    color: #ffffff;
}

.block {
    background-color: #111827;
    padding: 20px;
    border-radius: 10px;
    border-left: 5px solid #3b82f6;
    margin-bottom: 15px;
    color: white;
}

.section-box {
    background-color: #1f2937;
    color: #ffffff;
    padding: 12px;
    border-radius: 8px;
    margin: 6px 0;
    font-weight: bold;
}

.case-box {
    background-color: #1e293b;
    color: #ffffff;
    padding: 10px;
    border-radius: 8px;
    margin-bottom: 8px;
}

h1, h2, h3 {
    color: #93c5fd;
}
</style>
""", unsafe_allow_html=True)
from openai import OpenAI

st.set_page_config(page_title="POCSO Legal AI", layout="wide")

# -------------------- LOAD DATASET --------------------
@st.cache_data
def load_cases():
    return pd.read_excel("cases.xlsx")

cases_df = load_cases()

# -------------------- OPENAI --------------------
def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

# -------------------- BASIC EXTRACTION --------------------
def extract_victim_age(text):
    import re
    text = text.lower()

    # explicitly capture victim/minor/girl age
    m = re.search(r"(girl|boy|child|minor|victim)[^0-9]{0,15}(\d{1,2})", text)
    if m:
        return int(m.group(2))

    # capture "15 year old girl"
    m = re.search(r"(\d{1,2})\s*year[s]?\s*old\s*(girl|boy|child|minor)", text)
    if m:
        return int(m.group(1))

    # capture "minor aged 15"
    m = re.search(r"(minor|victim)[^0-9]{0,10}aged\s*(\d{1,2})", text)
    if m:
        return int(m.group(2))

    return None

# -------------------- RULE ENGINE --------------------
def check_penetration(text):
    keywords = [
        "rape", "penetration", "penetrated",
        "intercourse", "inserted", "oral sex",
        "forced himself", "forced herself"
    ]
    return any(k in text.lower() for k in keywords)

def check_touching(text):
    keywords = [
        "touched", "fondled", "groped", "kissed",
        "grabbed", "pressed", "hugged"
    ]
    return any(k in text.lower() for k in keywords)

def get_aggravating_keywords():
    factors = set()
    if "aggravating" in cases_df.columns:
        for item in cases_df["aggravating"].dropna():
            for word in str(item).split(","):
                factors.add(word.strip().lower())
    return list(factors)

AGGRAVATED_WORDS = get_aggravating_keywords()

def check_aggravated(text):
    import re
    text = text.lower()

    # direct keywords (still useful)
    keywords = [
        "father", "mother", "uncle", "aunt", "brother", "sister",
        "relative", "guardian", "stepfather",
        "teacher", "police", "doctor", "caretaker",
        "threat", "weapon", "injury", "repeated", "threatened"
    ]

    if any(word in text for word in keywords):
        return True

    # 🔥 pattern-based trust detection
    trust_patterns = [
        r"someone (the )?victim trusted",
        r"known to (her|him)",
        r"close (family|relative|person)",
        r"in a position of trust",
        r"family friend",
        r"staying with",
        r"living with",
        r"under (his|her) care",
        r"caretaking",
        r"looked after (her|him)",
        r"entrusted with (her|him)",
    ]

    for pattern in trust_patterns:
        if re.search(pattern, text):
            return True
    if detect_power_imbalance(text):
        return True

    return False
# -------------------- CASE MATCHING --------------------
def match_cases(user_input):
    matches = []
    user_words = user_input.lower().split()

    for _, row in cases_df.iterrows():
        facts = str(row.get("facts_summary", "")).lower()

        score = sum(1 for word in user_words if word in facts)

        if score > 3:
            matches.append({
                "case": row.get("case_name", "Unknown"),
                "sections": row.get("sections", ""),
                "aggravating": row.get("aggravating", "")
            })

    return matches[:3]

def detect_power_imbalance(text):
    import re
    text = text.lower()

    score = 0

    # authority / control
    authority_patterns = [
        r"teacher", r"police", r"doctor", r"employer", r"boss",
        r"guardian", r"caretaker", r"custody", r"warden",
        r"in charge", r"supervisor"
    ]

    # economic dependency
    economic_patterns = [
        r"paid", r"money", r"financial", r"dependent",
        r"provided (food|shelter|fees)", r"sponsored",
        r"employer", r"salary"
    ]

    # physical dominance / coercion
    physical_patterns = [
        r"stronger", r"overpowered", r"forced", r"restrained",
        r"threat", r"weapon", r"violence", r"intimidation",
        r"beat", r"injury"
    ]

    # age gap (very important)
    ages = re.findall(r"(\d{1,2})", text)
    if len(ages) >= 2:
        ages = [int(a) for a in ages]
        if max(ages) - min(ages) >= 10:
            score += 1

    # check all patterns
    for group in [authority_patterns, economic_patterns, physical_patterns]:
        if any(re.search(p, text) for p in group):
            score += 1

    return score >= 2  # threshold (tune if needed)

def extract_victim_age(text):
    import re
    text = text.lower()

    # patterns where victim is explicitly mentioned
    patterns = [
        r"(girl|boy|child|minor|victim)[^0-9]{0,20}(\d{1,2})",
        r"(\d{1,2})\s*year[s]?\s*old\s*(girl|boy|child|minor)",
        r"(minor|victim)[^0-9]{0,10}aged\s*(\d{1,2})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            for g in m.groups():
                if g and g.isdigit():
                    return int(g)

    # fallback → choose smallest age (usually victim)
    ages = re.findall(r"\b(\d{1,2})\b", text)
    if ages:
        return min([int(a) for a in ages])

    return None

def extract_roles(text):
    text = text.lower()

    victim_words = ["girl", "boy", "child", "minor", "victim"]
    accused_words = ["man", "male", "accused", "person"]

    victim_present = any(word in text for word in victim_words)
    accused_present = any(word in text for word in accused_words)

    return victim_present, accused_present

def detect_entities_and_timeline(text):
    import re
    text = text.lower()

    # victim indicators
    victim_words = ["girl", "boy", "child", "minor", "victim"]
    accused_words = ["man", "men", "accused", "person", "persons"]

    # count occurrences
    victim_count = sum(text.count(word) for word in victim_words)
    accused_count = sum(text.count(word) for word in accused_words)

    multiple_victims = victim_count > 1
    multiple_accused = accused_count > 1

    # repeated offence detection
    repeat_patterns = [
        "repeated", "again", "multiple times", "several times",
        "on many occasions", "continuously", "frequently",
        "daily", "over a period", "for months", "for years"
    ]

    repeated = any(p in text for p in repeat_patterns)

    return multiple_victims, multiple_accused, repeated

# -------------------- CLASSIFICATION --------------------
def check_sexual_intent(text):
    text = text.lower()

    keywords = [
        "sexual", "intent", "arousal", "porn",
        "private parts", "genitals", "breast",
        "kissed", "fondled", "groped",
        "molest", "molestation"
    ]

    return any(word in text for word in keywords)

def classify_offence(text):
    age = extract_victim_age(text)
    penetration = check_penetration(text)
    touching = check_touching(text)
    aggravated = check_aggravated(text)
    sexual_intent = check_sexual_intent(text)

    # NEW
    multiple_victims, multiple_accused, repeated = detect_entities_and_timeline(text)

    sections = []
    reasoning = []

    if age is not None and age < 18:
        reasoning.append("Victim is a minor.")

        if multiple_victims:
            reasoning.append("Multiple victims detected.")

        if multiple_accused:
            reasoning.append("Multiple accused detected.")

        if repeated:
            reasoning.append("Repeated offence / continuing act detected.")
            aggravated = True  # 🔥 important

        if penetration:
            if aggravated:
                sections.append("Section 5 → Aggravated Penetrative Sexual Assault")
                sections.append("Punishment: Section 6")
            else:
                sections.append("Section 3 → Penetrative Sexual Assault")
                sections.append("Punishment: Section 4")

        elif touching and sexual_intent:
            if aggravated:
                sections.append("Section 9 → Aggravated Sexual Assault")
                sections.append("Punishment: Section 10")
            else:
                sections.append("Section 7 → Sexual Assault")
                sections.append("Punishment: Section 8")

        else:
            sections.append("Facts may be insufficient to classify.")

    else:
        sections.append("POCSO may not apply (victim not clearly a minor).")

    return {
        "age": age,
        "penetration": penetration,
        "touching": touching,
        "aggravated": aggravated,
        "sections": sections,
        "reasoning": reasoning,
        "multiple_victims": multiple_victims,
        "multiple_accused": multiple_accused,
        "repeated": repeated
    }
# -------------------- AI REASONING --------------------
def ai_analysis(user_input, rule_output, matched_cases):
    client = get_client()
    if not client:
        return "AI unavailable (check API key)."

    case_text = "\n".join([
        f"{c['case']} → Sections: {c['sections']}, Aggravating: {c['aggravating']}"
        for c in matched_cases
    ])

    prompt = f"""
Analyse the case under POCSO Sections 3–8.

Facts:
{user_input}

Rule Findings:
{rule_output}

Relevant Cases:
{case_text}

Provide structured legal reasoning:
1. Facts
2. Ingredients
3. Section applicability
4. Legal reasoning
5. Conclusion
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text

# -------------------- UI --------------------
st.title("⚖️ POCSO Legal Analysis System")
st.caption("Hybrid Rule-Based + AI Legal Reasoning Engine")

user_input = st.text_area("📝 Enter Case Facts", height=150)

if st.button("🔍 Analyse Case"):

    rule_output = classify_offence(user_input)
    matched = match_cases(user_input)

    # ---------------- FACTS ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("📌 Facts Presented")
    st.write(user_input)
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- ISSUES ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("⚖️ Issues for Determination")

    if rule_output["penetration"]:
        st.write("- Whether penetrative sexual assault occurred")
    elif rule_output["touching"]:
        st.write("- Whether sexual assault (non-penetrative) occurred")
    else:
        st.write("- Whether facts disclose an offence under POCSO")

    if rule_output["aggravated"]:
        st.write("- Whether aggravating circumstances exist")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- FINDINGS ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("🔎 Findings")

    st.write(f"**Age Detected:** {rule_output['age']}")
    st.write(f"**Penetration:** {rule_output['penetration']}")
    st.write(f"**Touching:** {rule_output['touching']}")
    st.write(f"**Aggravated Factors:** {rule_output['aggravated']}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- LAW ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("📚 Applicable Law")

    if rule_output["sections"]:
        for sec in rule_output["sections"]:
            st.markdown(f'<div class="section-box">{sec}</div>', unsafe_allow_html=True)
    else:
        st.warning("No clear section determined.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- REASONING ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("📖 Rule-Based Reasoning")

    for r in rule_output["reasoning"]:
        st.write(f"- {r}")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- CASE LAW ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("📚 Similar Case References")

    if matched:
        for m in matched:
            st.markdown(
                f'<div class="case-box"><b>{m["case"]}</b><br>Sections: {m["sections"]}<br>Aggravating: {m["aggravating"]}</div>',
                unsafe_allow_html=True
            )
    else:
        st.write("No close matches found.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---------------- AI ----------------
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("🤖 AI Legal Reasoning")

    try:
        with st.spinner("Analysing..."):
            st.write(ai_analysis(user_input, rule_output, matched))
    except:
        st.warning("AI unavailable.")

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.caption("⚠️ This tool is for academic purposes and does not constitute legal advice.")