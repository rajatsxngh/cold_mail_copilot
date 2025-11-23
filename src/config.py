# src/config.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "cold-email-copilot")
PINECONE_CLOUD = os.environ.get("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.environ.get("PINECONE_REGION", "us-east-1")

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")

# OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Pinecone client + index
pc = Pinecone(api_key=PINECONE_API_KEY)

# create index if not exists
if PINECONE_INDEX_NAME not in [ix["name"] for ix in pc.list_indexes()]:
    pc.create_index(
        name=PINECONE_INDEX_NAME,
        dimension=384,        # all-MiniLM-L6-v2
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
    )

pinecone_index = pc.Index(PINECONE_INDEX_NAME)