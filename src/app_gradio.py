# src/app_gradio.py

import os
from pathlib import Path
import urllib.parse
import requests

import gradio as gr

from .pdf_utils import extract_text_from_pdf
from .embeddings_index import index_resume_text, retrieve_relevant_snippets
from .hunter_client import find_recruiter_email
from .openai_email import parse_jd, generate_cold_email

# -----------------------------
# Config & constants
# -----------------------------
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "").strip()


# -----------------------------
# Helper functions
# -----------------------------
def build_gmail_link(to: str, subject: str, body: str) -> str:
    """Build a Gmail compose URL with everything pre-filled."""
    to = to or ""
    subject = subject or ""
    body = body or ""
    return (
        "https://mail.google.com/mail/?view=cm&fs=1"
        + "&to=" + urllib.parse.quote(to)
        + "&su=" + urllib.parse.quote(subject)
        + "&body=" + urllib.parse.quote(body)
    )


def send_via_n8n(to: str, subject: str, body: str,
                 job_title: str, company: str, jd_url: str) -> str:
    """Send the email + metadata to n8n webhook for sending/logging."""
    if not N8N_WEBHOOK_URL:
        return "⚠️ N8N_WEBHOOK_URL is not set in .env"

    payload = {
        "to": to,
        "subject": subject,
        "body": body,
        "job_title": job_title,
        "company": company,
        "jd_url": jd_url,
    }

    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 201, 204):
            return "✅ Email sent via n8n and logged (check your Gmail / Sheet)."
        else:
            return f"⚠️ n8n responded with {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        return f"❌ Error calling n8n: {e}"


def update_gmail_link(to: str, subject: str, body: str) -> str:
    """Rebuild the Gmail draft link when the user edits the text."""
    gmail_link = build_gmail_link(to or "", subject or "", body or "")
    return f"[✏️ Open this draft in Gmail]({gmail_link})"


def send_via_n8n_handler(to: str, subject: str, body: str,
                         job_title: str, company: str, jd_url: str) -> str:
    """Wrapper to call send_via_n8n from the Gradio button."""
    return send_via_n8n(to, subject, body, job_title, company, jd_url)


# -----------------------------
# Core pipeline
# -----------------------------
def cold_email_pipeline(resume_file, jd_text, recruiter_name, company_domain):
    if resume_file is None:
        # return 10 outputs (matching UI) even on error
        msg = "⚠️ Please upload a resume first."
        return msg, "", "", "", "", "", "", "", "", ""

    # 1. Path to uploaded resume & extract text
    resume_path = Path(str(resume_file))  # NamedString → path
    dest = UPLOAD_DIR / resume_path.name
    if resume_path != dest:
        dest.write_bytes(resume_path.read_bytes())

    resume_text = extract_text_from_pdf(str(dest))

    # 2. (Optional) index resume in vector DB for this user
    #    You can call this once per user; here it's demo-style
    index_resume_text(resume_text, user_id="user1")

    # 3. Parse JD with OpenAI
    jd_info = parse_jd(jd_text or "")

    # 4. Retrieve + rerank relevant resume snippets
    snippets = retrieve_relevant_snippets(jd_text or "", user_id="user1", top_k=5)

    # 5. Find recruiter email via Hunter
    recruiter_email = None
    if recruiter_name and company_domain:
        recruiter_email = find_recruiter_email(recruiter_name, company_domain)

    # 6. Generate cold email
    subject, body = generate_cold_email(jd_info, snippets, recruiter_name, recruiter_email)

    # For display
    jd_summary = f"""**Role:** {jd_info.get('role_title', '')}
**Company:** {jd_info.get('company_name', '')}
**Location:** {jd_info.get('location', '')}
**Top skills:** {', '.join(jd_info.get('top_skills', []))}
"""

    snippets_md = "\n".join(f"- {s['text']}" for s in snippets) if snippets else "_No strong matches found in resume._"

    email_info = f"**Recruiter email (from Hunter):** {recruiter_email or 'Not found'}"

    # Gmail link
    gmail_link = build_gmail_link(recruiter_email or "", subject, body)
    gmail_md = f"[✏️ Open this draft in Gmail]({gmail_link})"

    # Structured metadata for n8n
    job_title = jd_info.get("role_title", "")
    company = jd_info.get("company_name", "")
    jd_url = ""  # (optional) you can add a JD URL textbox later

    return (
        jd_summary,            # 1 - Markdown
        snippets_md,           # 2 - Markdown
        email_info,            # 3 - Markdown
        subject,               # 4 - subject textbox
        body,                  # 5 - body textbox
        gmail_md,              # 6 - Gmail link md
        recruiter_email or "", # 7 - hidden state
        job_title,             # 8 - hidden state
        company,               # 9 - hidden state
        jd_url,                # 10 - hidden state
    )


# -----------------------------
# Custom CSS for "enterprise" UI
# -----------------------------
custom_css = """
/* Overall page */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
}

body {
    background: radial-gradient(circle at top, #0f172a 0, #020617 55%, #000 100%);
}

/* Header */
.app-header h1 {
    font-size: 30px;
    font-weight: 700;
    letter-spacing: 0.02em;
}

.app-header p {
    opacity: 0.8;
}

/* Card styling */
.app-card {
    border-radius: 18px;
    border: 1px solid #1f2937;
    background: rgba(15, 23, 42, 0.96);
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.7);
    padding: 18px 20px;
}

/* Section titles inside cards */
.app-section-title {
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #9ca3af;
    margin-bottom: 4px;
}

/* Input labels */
.app-input .wrap > label,
.app-output .wrap > label {
    font-weight: 500;
    font-size: 13px;
    color: #e5e7eb;
}

/* Textboxes */
.app-input textarea,
.app-input input,
.app-output textarea {
    background: #020617 !important;
    border-radius: 10px !important;
}

/* Buttons */
.primary-btn button {
    background: linear-gradient(135deg, #2563eb, #22c55e);
    border-radius: 999px;
    font-weight: 600;
    font-size: 14px;
    height: 46px;
}

.secondary-btn button {
    border-radius: 999px;
    font-weight: 500;
    font-size: 14px;
    background: #020617;
}

/* Status bar */
.status-bar {
    font-size: 13px;
}
"""


# -----------------------------
# Gradio UI
# -----------------------------


with gr.Blocks(
    title="Cold Email Copilot",
    css=custom_css,
) as demo:

    # Header
    with gr.Row(elem_classes="app-header", equal_height=True):
        with gr.Column(scale=3):
            gr.Markdown(
                """
### 🧊 Cold Email Copilot  
Turn any LinkedIn job + your resume into a recruiter-ready cold email in seconds.

Upload your resume, paste the JD, confirm the recruiter, then review & send — all from one place.
"""
            )
        with gr.Column(scale=1, min_width=0):
            gr.Markdown(
                """
<div style="text-align:right; opacity:0.8; font-size:13px;">
Built with <b>Gradio</b> · <b>OpenAI</b> · <b>Pinecone</b> · <b>Hunter</b> · <b>n8n</b>
</div>
"""
            )

    # Main two-column layout
    with gr.Row():
        # LEFT: Inputs
        with gr.Column(scale=1, elem_classes="app-card app-input"):
            gr.Markdown("#### Job & Recruiter Details")

            resume_file = gr.File(
                label="Upload your resume (PDF)",
                file_count="single",
            )

            jd_text = gr.Textbox(
                label="Paste Job Description",
                lines=14,
                placeholder="Paste the full job description from LinkedIn or the careers site…",
            )

            recruiter_name = gr.Textbox(
                label="Recruiter name (from LinkedIn)",
                placeholder="e.g., Natalya Lowe",
            )

            company_domain = gr.Textbox(
                label="Company domain (e.g., schnucks.com)",
                placeholder="e.g., kiageorgia.com",
            )

            run_btn = gr.Button(
                "⚙️ Generate Cold Email",
                variant="primary",
                elem_classes="primary-btn",
            )

        # RIGHT: Outputs
        with gr.Column(scale=2, elem_classes="app-card app-output"):
            gr.Markdown("#### Generated Email Preview")

            jd_out = gr.Markdown(label="JD Summary")

            snippets_out = gr.Markdown(
                label="Top matching resume snippets",
            )

            recruiter_email_out = gr.Markdown(
                label="Recruiter email (via Hunter)",
            )

            subject_box = gr.Textbox(
                label="Email subject",
                lines=1,
                placeholder="Subject line that will appear in recruiter’s inbox",
            )

            body_box = gr.Textbox(
                label="Email body (editable)",
                lines=12,
                placeholder="Your cold email draft will appear here. Tweak anything before sending.",
            )

            gmail_link_md = gr.Markdown(
                label="Open draft in Gmail",
            )

            status_out = gr.Markdown(
                label="Status / Messages",
                elem_classes="status-bar",
            )

            # Hidden state values for n8n
            recruiter_email_state = gr.State()
            job_title_state = gr.State()
            company_state = gr.State()
            jd_url_state = gr.State()

            with gr.Row():
                send_btn = gr.Button(
                    "🚀 Send via n8n",
                    variant="primary",
                    elem_classes="primary-btn",
                )
                edit_gmail_btn = gr.Button(
                    "✏️ Update Gmail link with my edits",
                    variant="secondary",
                    elem_classes="secondary-btn",
                )

    # --- Wire up callbacks ---

    # Generate button
    run_btn.click(
        cold_email_pipeline,
        inputs=[resume_file, jd_text, recruiter_name, company_domain],
        outputs=[
            jd_out,                # 1
            snippets_out,          # 2
            recruiter_email_out,   # 3
            subject_box,           # 4
            body_box,              # 5
            gmail_link_md,         # 6
            recruiter_email_state, # 7
            job_title_state,       # 8
            company_state,         # 9
            jd_url_state,          # 10
        ],
    )

    # Update Gmail link when user has edited subject/body
    edit_gmail_btn.click(
        update_gmail_link,
        inputs=[recruiter_email_state, subject_box, body_box],
        outputs=[gmail_link_md],
    )

    # Send via n8n
    send_btn.click(
        send_via_n8n_handler,
        inputs=[
            recruiter_email_state,
            subject_box,
            body_box,
            job_title_state,
            company_state,
            jd_url_state,
        ],
        outputs=[status_out],
    )


if __name__ == "__main__":
    demo.launch()