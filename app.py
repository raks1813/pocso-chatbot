import os
import re

import streamlit as st
st.sidebar.title("About")
st.sidebar.info(
    "This tool analyses case facts under Sections 3–8 of the POCSO Act.\n\n"
    "For academic and research purposes only."
)
from openai import OpenAI


st.title("⚖️ POCSO Offence Detection System")
st.markdown("### Sections 3–8 Analysis Tool")
st.markdown(
    "Enter case facts to identify offences under the POCSO Act."
)


import os
from openai import OpenAI
def get_client():
    import os
    from openai import OpenAI
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_age(text):
    match = re.search(r"(\d{1,2})\s*years?", text.lower())
    if match:
        return int(match.group(1))
    return None


def check_penetration(text):
    keywords = [
        "penetration",
        "penetrated",
        "inserted",
        "rape",
        "penis",
        "object inserted",
        "oral sex",
    ]
    lowered = text.lower()
    return any(word in lowered for word in keywords)


def check_touching(text):
    keywords = [
        "touched",
        "touching",
        "fondled",
        "groped",
        "kissed",
        "hugged inappropriately",
    ]
    lowered = text.lower()
    return any(word in lowered for word in keywords)


def check_aggravated(text):
    keywords = [
        "father",
        "mother",
        "relative",
        "teacher",
        "police",
        "guardian",
        "custody",
        "authority",
        "threat",
        "weapon",
        "injury",
        "repeated",
    ]
    lowered = text.lower()
    return any(word in lowered for word in keywords)


def check_sexual_intent(text):
    keywords = [
        "sexual",
        "intent",
        "arousal",
        "porn",
        "private parts",
    ]
    lowered = text.lower()
    return any(word in lowered for word in keywords)


def classify_offence(text):
    age = extract_age(text)
    penetration = check_penetration(text)
    touching = check_touching(text)
    aggravated = check_aggravated(text)
    sexual_intent = check_sexual_intent(text)

    result = []

    if age is not None and age < 18:
        if penetration:
            if aggravated:
                result.append("Section 5 -> Aggravated Penetrative Sexual Assault")
                result.append("Punishment: Section 6")
            else:
                result.append("Section 3 -> Penetrative Sexual Assault")
                result.append("Punishment: Section 4")
        elif touching and sexual_intent:
            result.append("Section 7 -> Sexual Assault")
            result.append("Punishment: Section 8")
        else:
            result.append("Facts may be insufficient to classify Sections 3-8 confidently.")
    else:
        result.append("POCSO may not apply (victim not clearly a minor).")

    return result, age, penetration, touching, aggravated, sexual_intent


def ai_analysis(user_input):
    client = get_client()
    if client is None:
        return (
            "Set the `OPENAI_API_KEY` environment variable to enable AI legal reasoning. "
            "The rule-based analysis still works without it."
        )

    prompt = f"""
You are a legal analysis assistant for educational use only.
Analyse the given facts strictly under Sections 3, 4, 5, 6, 7, and 8 of the POCSO Act.
Do not go beyond the facts provided. If facts are unclear, say so explicitly.

Use this format:
1. Extracted Facts
2. Legal Ingredients
   - Age
   - Nature of Act
   - Sexual Intent
   - Aggravating Factors
3. Applicable Section(s)
4. Legal Reasoning
5. Conclusion

Facts:
{user_input}
""".strip()

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    return response.output_text


st.title("POCSO Offence Detection Chatbot (Sections 3-8)")
st.write("Analyse facts to detect possible offences under the POCSO Act with legal reasoning.")

user_input = st.text_area(
    "📝 Enter Case Facts",
    placeholder="Example: A 14 year old girl was assaulted by her teacher...",
    height=150
)
if st.button("🔍 Analyse Case"):

    result, age, penetration, touching, aggravated, sexual_intent = classify_offence(user_input)

    st.subheader("📊 Rule-Based Analysis")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Age", age if age else "Not Found")
        st.metric("Penetration", "Yes" if penetration else "No")

    with col2:
        st.metric("Touching", "Yes" if touching else "No")
        st.metric("Aggravated", "Yes" if aggravated else "No")

    st.markdown("### ⚖️ Suggested Sections")

    for item in result:
        st.success(item)

    st.subheader("🤖 AI Legal Reasoning")

    try:
        with st.spinner("Analysing legally..."):
            st.info(ai_analysis(user_input))
    except:
        st.warning("AI analysis unavailable (quota issue).")

st.markdown("---")
st.markdown("---")
st.caption("⚠️ This tool is for educational purposes only and does not constitute legal advice.")