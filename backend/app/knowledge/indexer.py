"""
Knowledge Base Indexer: Chunking and Embedding Policies
========================================================

Takes policy markdown documents, chunks them by heading,
and stores them in ChromaDB with embeddings.

KEY CONCEPT - Chunking Strategy:
We chunk by heading (##) so each chunk is a self-contained
policy section. This is better than fixed-size chunking because:
1. Each chunk is semantically coherent (one topic)
2. Metadata (section name) is preserved
3. The LLM gets complete policy rules, not fragments
"""

import os
import re
from pathlib import Path

from app.config import get_settings
from app.knowledge.retriever import embed_texts, _get_chroma_collection


def chunk_markdown_by_heading(text: str, source: str) -> list[dict]:
    """
    Split a markdown document into chunks at ## headings.
    Each chunk includes the heading as metadata.
    
    KEY CONCEPT - Contextual Chunking:
    Instead of blindly splitting every N characters, we split
    at semantic boundaries (headings). Each chunk knows:
    - Which document it came from (source)
    - Which section it covers (section)
    - The version and effective date (if present)
    """
    chunks = []
    
    # Extract document metadata from front matter or first line
    lines = text.strip().split("\n")
    doc_title = ""
    version = "1.0"
    effective_date = ""
    
    for line in lines[:5]:
        if line.startswith("# ") and not line.startswith("## "):
            doc_title = line[2:].strip()
        if "version:" in line.lower():
            version = line.split(":")[-1].strip()
        if "effective:" in line.lower() or "date:" in line.lower():
            effective_date = line.split(":")[-1].strip()
    
    # Split by ## headings
    sections = re.split(r'\n(?=## )', text)
    
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        
        # Extract section heading
        section_heading = ""
        if section.startswith("## "):
            first_line = section.split("\n")[0]
            section_heading = first_line[3:].strip()
        elif section.startswith("# ") and i == 0:
            section_heading = "Overview"
        
        # Skip very short chunks (likely just headings)
        if len(section) < 50:
            continue
        
        chunk_id = f"{source}_{i}"
        chunks.append({
            "id": chunk_id,
            "text": section,
            "source": source,
            "section": section_heading or f"Section {i+1}",
            "version": version,
            "effective_date": effective_date,
            "doc_title": doc_title,
        })
    
    return chunks


def index_policies(policies_dir: str = None):
    """
    Read all policy markdown files, chunk them, embed, and store in ChromaDB.
    
    This is run once at startup (or when policies change).
    """
    if policies_dir is None:
        policies_dir = os.path.join(os.path.dirname(__file__), "policies")
    
    settings = get_settings()
    collection = _get_chroma_collection()
    
    # Skip if already indexed
    if collection.count() > 0:
        print(f"⚡ Knowledge base already indexed ({collection.count()} chunks), skipping...")
        return
    
    # Find all markdown files
    policy_files = sorted(Path(policies_dir).glob("*.md"))
    if not policy_files:
        print("⚠️ No policy files found in", policies_dir)
        return
    
    all_chunks = []
    for policy_file in policy_files:
        text = policy_file.read_text(encoding="utf-8")
        source = policy_file.stem  # filename without extension
        chunks = chunk_markdown_by_heading(text, source)
        all_chunks.extend(chunks)
        print(f"  📄 {policy_file.name}: {len(chunks)} chunks")
    
    if not all_chunks:
        print("⚠️ No chunks generated from policy files")
        return
    
    print(f"📚 Total chunks: {len(all_chunks)}. Generating embeddings...")
    
    # Generate embeddings in batches (API limit friendly)
    batch_size = 20
    all_ids = []
    all_texts = []
    all_metadatas = []
    all_embeddings = []
    
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        texts = [c["text"] for c in batch]
        
        embeddings = embed_texts(texts)
        
        for chunk, embedding in zip(batch, embeddings):
            all_ids.append(chunk["id"])
            all_texts.append(chunk["text"])
            all_metadatas.append({
                "id": chunk["id"],
                "source": chunk["source"],
                "section": chunk["section"],
                "version": chunk["version"],
                "effective_date": chunk["effective_date"],
                "doc_title": chunk["doc_title"],
            })
            all_embeddings.append(embedding)
    
    # Store in ChromaDB
    collection.add(
        ids=all_ids,
        documents=all_texts,
        metadatas=all_metadatas,
        embeddings=all_embeddings,
    )
    
    print(f"✅ Indexed {len(all_ids)} policy chunks into ChromaDB")


if __name__ == "__main__":
    index_policies()
