# src/openai_email.py
import json
from typing import List, Dict, Tuple
from .config import openai_client

JD_SYSTEM_PROMPT = """
You are a helpful assistant that extracts structured info from job descriptions.
Return a SHORT JSON with keys:
- role_title
- company_name
- location
- top_skills (list of up to 8 skills/keywords)
Do NOT include explanation outside of JSON.
"""

EMAIL_SYSTEM_PROMPT = """
You are an assistant that writes concise, personalized cold emails to recruiters
about a specific role. The tone should be professional, friendly, and to the point.
"""

def parse_jd(jd_text: str) -> Dict:
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": JD_SYSTEM_PROMPT},
            {"role": "user", "content": jd_text}
        ],
        temperature=0.2
    )
    content = response.choices[0].message.content
    try:
        data = json.loads(content)
    except Exception:
        data = {"role_title": "", "company_name": "", "location": "", "top_skills": []}
    return data

def generate_cold_email(
    jd_info: Dict,
    resume_snippets: List[Dict],
    recruiter_name: str,
    recruiter_email: str | None
) -> Tuple[str, str]:
    role = jd_info.get("role_title", "this role")
    company = jd_info.get("company_name", "")
    skills = jd_info.get("top_skills", [])

    snippets_text = "\n\n".join(
        f"- {s['text']}" for s in resume_snippets
    )

    user_prompt = f"""
Job description info:
Role: {role}
Company: {company}
Top skills: {skills}

Recruiter name: {recruiter_name}
Recruiter email: {recruiter_email or '(not found yet)'}

My most relevant experience (from my resume):
{snippets_text}

Write:
1) A clear, compelling subject line (on one line).
2) A short email body (120–180 words) that:
   - Greets the recruiter by name.
   - Mentions the role and company.
   - Highlights 2–3 concrete achievements from my experience.
   - Politely asks for a short call or for them to consider my application.

Format exactly as:

Subject: <subject line>
Body:
<email body>
"""

    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5
    )
    content = response.choices[0].message.content

    # very simple parse
    subject = "Cold application for " + (role or "the role")
    body = content
    if "Subject:" in content:
        lines = content.splitlines()
        first = lines[0]
        if first.lower().startswith("subject:"):
            subject = first[len("Subject:"):].strip()
            body = "\n".join(lines[2:])  # skip "Subject:" and "Body:" line if present

    return subject, body