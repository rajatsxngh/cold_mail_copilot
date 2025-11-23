# 🧊 Cold Email Copilot

Paste a job description, upload your resume, and get a **personalized cold email to the recruiter** – with the recruiter’s email auto-fetched via Hunter and an option to send via Gmail/n8n.

---

## 💼 Problem

As an international master’s student in the US, applying to internships and jobs is **very time-consuming**:

- You need to **personalize every message** to stand out.
- You often have to **manually find recruiter emails** from LinkedIn/Hunter.
- You’re juggling **coursework, projects, networking, and recruiting** at the same time.

This makes consistent cold outreach hard, even though it’s one of the most important parts of getting interviews.

**Cold Email Copilot** automates the boring parts:

> **Paste JD + upload resume → get a recruiter-specific email ready in Gmail, with the correct email address filled in.**

---

## ✨ What the app does

1. **Upload your resume (PDF)**  
2. **Paste the Job Description (JD)** into a textbox  
3. **Enter recruiter name + company domain** (e.g., `natalya lowe`, `kiageorgia.com`)  
4. Click **“Generate Cold Email”**

Under the hood, the app:

- Extracts text from your resume
- Splits it into chunks and builds embeddings
- Indexes chunks in a **Pinecone** vector database
- Parses the JD using **OpenAI** (role, company, skills, etc.)
- Searches Pinecone for the most relevant resume snippets and **reranks** them with a **CrossEncoder**
- Calls **Hunter.io** with recruiter name + domain to find the recruiter email
- Uses **OpenAI** again to generate a personalized:
  - **Subject line**
  - **Email body**

On the UI you get:

- Parsed JD summary (role, company, top skills)
- Top matching resume snippets
- Recruiter email (from Hunter)
- Editable **subject** & **email body**
- A **“Open this draft in Gmail”** link (pre-filled To + Subject + Body)
- A **“Send via n8n”** button to actually send + log the email automatically

---

## 🧱 Tech Stack

### Frontend / UI

- **[Gradio](https://www.gradio.app/)** – lightweight web UI:
  - File upload for resume
  - Textboxes for JD & recruiter info
  - Buttons for “Generate”, “Send via n8n”, “Update Gmail link”
  - Dark theme with dashboard-like layout

### Backend (Python)

Located in `src/`:

- `app_gradio.py`
  - Wires up all components into the Gradio app
  - Handles the “Generate Cold Email” button
  - Builds Gmail draft links
  - Calls the n8n webhook (`send_via_n8n_handler`)

- `pdf_utils.py`
  - Extracts text from the uploaded resume PDF

- `embeddings_index.py`
  - Splits resume text into overlapping chunks
  - Creates embeddings with `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")`
  - Stores vectors in **Pinecone**
  - Retrieves the most relevant chunks for a JD
  - **Reranks** them using `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")`

- `openai_email.py`
  - `parse_jd`: uses OpenAI to parse the JD into structured info (role, company, skills, requirements)
  - `generate_cold_email`: uses OpenAI to write a personalized subject + email body that:
    - Matches the JD
    - Uses the top resume snippets
    - Mentions the recruiter by name if available

- `hunter_client.py`
  - Wraps the **Hunter.io Email Finder** API
  - Uses recruiter name + company domain to find the best-matching email

- `config.py`
  - Sets up the **Pinecone** client and index (read this file to see exactly which env variables it expects)

### External Services

- **SentenceTransformers**
  - `all-MiniLM-L6-v2` – dense embeddings for resume chunks / JD

- **CrossEncoder**
  - `ms-marco-MiniLM-L-6-v2` – reranks top Pinecone results using the JD + chunk pairs

- **Pinecone**
  - Vector database for storing resume chunks per user

- **OpenAI API**
  - JD parsing
  - Cold email generation

- **Hunter.io**
  - Recruiter email lookup

- **n8n**
  - Webhook receiver
  - Gmail integration (send email)
  - Optional logging (Google Sheets / DB, etc.)

---

## 🧩 Project Structure

```text
cold_mail_copilot/
├─ src/
│  ├─ app_gradio.py        # Gradio UI + orchestration + n8n handler
│  ├─ config.py            # Pinecone config/client
│  ├─ embeddings_index.py  # chunking, embeddings, Pinecone, reranking
│  ├─ hunter_client.py     # Hunter.io API wrapper
│  ├─ openai_email.py      # JD parsing + cold email generation (OpenAI)
│  ├─ pdf_utils.py         # PDF text extraction
│  └─ __init__.py
├─ requirements.txt
├─ .gitignore
└─ README.md
```
.env and venv/ are intentionally not committed (see .gitignore)


## ⚙️ Setup & Installation


1️⃣ Clone the repo
```
git clone https://github.com/<your-username>/cold_mail_copilot.git
cd cold_mail_copilot
```
2️⃣ Create & activate a virtual environment
```
python3 -m venv venv
source venv/bin/activate    # macOS / Linux
# .\venv\Scripts\activate   # Windows PowerShell
```
3️⃣ Install dependencies
```
pip install -r requirements.txt
```

4️⃣ Create a .env file
Create a file named .env in the project root with your keys and config.
Adjust names if your config.py expects different ones.
Example:
```
# OpenAI
OPENAI_API_KEY=your_openai_key_here

# Pinecone
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=cold-email-resumes
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Hunter.io
HUNTER_API_KEY=your_hunter_api_key_here

# n8n webhook (for "Send via n8n" button)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/cold-email
```
⚠️ Never commit .env – it’s already ignored by .gitignore.

5️⃣ Run the Gradio app
```
python -m src.app_gradio
```
You should see something like:
```
Running on local URL:  http://127.0.0.1:7860
```
Open that URL in your browser.

---


## 🔁 Optional: n8n Workflow (Send via Gmail + Log)

If you want the “Send via n8n” button to actually send emails:

1️⃣ Start n8n
```
npx n8n
```
Open the n8n UI (usually at http://localhost:5678).

2️⃣ Create the workflow
#### 1.	Webhook node
	•	Method: POST
	•	Path: cold-email
	•	This gives you a URL like: http://localhost:5678/webhook/cold-email
	•	Make sure this matches N8N_WEBHOOK_URL in your .env.
	
####  2.	Gmail node
	•	Connect it after the Webhook node.
	•	Map fields from the webhook JSON:
	•	To ← {{$json["to"]}}
	•	Subject ← {{$json["subject"]}}
	•	Body ← {{$json["body"]}}
	•	Use your Gmail OAuth credential inside n8n.
#### 	3.	(Optional) Logging node (e.g., Google Sheets / DB)
	•	Insert between or after nodes to log:
	•	to, subject, job_title, company, jd_url, timestamp
####	4.	Activate the workflow (toggle at top right).

#### Now, when you click “Send via n8n” in the app:
	•	The app posts {to, subject, body, job_title, company, jd_url} to the webhook.
	•	n8n sends the email via Gmail.
	•	(Optional) n8n logs it to your chosen storage.

  ---
  ## ⚠️ Disclaimer

This is a personal learning project focused on:
	•	RAG-style retrieval with reranking
	•	Practical automation (n8n + Gmail)
	•	Realistic job-search use case

Always review and edit each email before sending and respect company / recruiter communication norms and privacy policies.

