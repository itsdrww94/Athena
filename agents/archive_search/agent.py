#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                     A R C H I V E   S E A R C H                               ║
║                   "The Knowledge Retriever"                                    ║
║                                                                               ║
║  Search your own ChatGPT history and notes before googling                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Features:
- BM25 search indexing of ChatGPT conversations
- Search your own past solutions
- Never forget what you already learned

Usage:
    python archive_search.py --query "fix python path"
    python archive_search.py --index    # Rebuild search index
    python archive_search.py --stats    # Show index statistics

Commands:
    /recall "how to fix python path"
"""

import os
import sys
import json
import argparse
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

ATHENA_DATA_DIR = Path.home() / "athena_data"
DNA_DIR = ATHENA_DATA_DIR / "me"
INDEX_DIR = ATHENA_DATA_DIR / "search_index"
INDEX_FILE = INDEX_DIR / "bm25_index.pkl"
DOCS_FILE = INDEX_DIR / "documents.pkl"

# Ensure directories exist
INDEX_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# BM25 SEARCH INDEX
# =============================================================================

class SearchIndex:
    """
    Simple BM25 search index for local knowledge retrieval.
    
    Falls back to simple TF-IDF if rank_bm25 not installed.
    """
    
    def __init__(self):
        self.documents = []   # List of (doc_id, text, metadata)
        self.bm25 = None
        self.tokenized_docs = []
    
    def tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        import re
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
        # Remove very short tokens
        return [t for t in tokens if len(t) > 2]
    
    def add_document(self, doc_id: str, text: str, metadata: Dict = None) -> None:
        """Add a document to the index."""
        self.documents.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata or {}
        })
    
    def build_index(self) -> int:
        """Build the BM25 index from documents."""
        if not self.documents:
            return 0
        
        # Tokenize all documents
        self.tokenized_docs = [
            self.tokenize(doc["text"]) for doc in self.documents
        ]
        
        # Try to use rank_bm25
        try:
            from rank_bm25 import BM25Okapi
            self.bm25 = BM25Okapi(self.tokenized_docs)
        except ImportError:
            print("⚠️ rank_bm25 not installed, using simple TF-IDF fallback")
            self.bm25 = None
        
        return len(self.documents)
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """Search the index and return top results."""
        query_tokens = self.tokenize(query)
        
        if not query_tokens:
            return []
        
        if self.bm25:
            # Use BM25
            scores = self.bm25.get_scores(query_tokens)
            
            # Get top-k
            top_indices = sorted(
                range(len(scores)),
                key=lambda i: scores[i],
                reverse=True
            )[:top_k]
            
            return [
                (self.documents[i], scores[i])
                for i in top_indices
                if scores[i] > 0
            ]
        else:
            # Simple TF matching fallback
            results = []
            query_set = set(query_tokens)
            
            for i, tokens in enumerate(self.tokenized_docs):
                token_set = set(tokens)
                overlap = len(query_set & token_set)
                if overlap > 0:
                    score = overlap / len(query_set)
                    results.append((self.documents[i], score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
    
    def save(self) -> bool:
        """Save index to disk."""
        try:
            with open(DOCS_FILE, 'wb') as f:
                pickle.dump(self.documents, f)
            
            with open(INDEX_FILE, 'wb') as f:
                pickle.dump({
                    'tokenized_docs': self.tokenized_docs,
                    'bm25': self.bm25
                }, f)
            
            return True
        except Exception as e:
            print(f"Error saving index: {e}")
            return False
    
    def load(self) -> bool:
        """Load index from disk."""
        try:
            if not DOCS_FILE.exists():
                return False
            
            with open(DOCS_FILE, 'rb') as f:
                self.documents = pickle.load(f)
            
            if INDEX_FILE.exists():
                with open(INDEX_FILE, 'rb') as f:
                    data = pickle.load(f)
                    self.tokenized_docs = data.get('tokenized_docs', [])
                    self.bm25 = data.get('bm25')
            
            return True
        except Exception as e:
            print(f"Error loading index: {e}")
            return False


# =============================================================================
# DATA LOADERS
# =============================================================================

def load_chatgpt_conversations(index: SearchIndex) -> int:
    """Load ChatGPT conversation exports into the index."""
    count = 0
    
    # Find conversation files
    conv_files = list(DNA_DIR.rglob("conversations.json"))
    
    for filepath in conv_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conversations = data if isinstance(data, list) else data.get("conversations", [])
            
            for conv in conversations:
                conv_id = conv.get("id", conv.get("conversation_id", str(count)))
                title = conv.get("title", "Untitled")
                create_time = conv.get("create_time", 0)
                
                # Extract all text from the conversation
                texts = []
                mapping = conv.get("mapping", {})
                
                for node_id, node in mapping.items():
                    message = node.get("message", {})
                    if message:
                        content = message.get("content", {})
                        
                        if isinstance(content, dict):
                            parts = content.get("parts", [])
                            for part in parts:
                                if isinstance(part, str):
                                    texts.append(part)
                        elif isinstance(content, str):
                            texts.append(content)
                
                if texts:
                    full_text = "\n".join(texts)
                    
                    # Create timestamp
                    try:
                        dt = datetime.fromtimestamp(create_time)
                        date_str = dt.strftime("%Y-%m-%d")
                    except:
                        date_str = "unknown"
                    
                    index.add_document(
                        doc_id=f"chatgpt_{conv_id}",
                        text=full_text[:10000],  # Limit size
                        metadata={
                            "source": "chatgpt",
                            "title": title,
                            "date": date_str,
                            "file": str(filepath)
                        }
                    )
                    count += 1
                    
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    return count


def load_text_notes(index: SearchIndex) -> int:
    """Load text/markdown notes into the index."""
    count = 0
    
    text_files = list(DNA_DIR.rglob("*.txt")) + \
                 list(DNA_DIR.rglob("*.md")) + \
                 list(ATHENA_DATA_DIR.rglob("notes/*.txt"))
    
    for filepath in text_files:
        try:
            content = filepath.read_text(encoding='utf-8')
            
            if len(content) > 100:  # Skip tiny files
                index.add_document(
                    doc_id=f"note_{filepath.stem}",
                    text=content[:10000],
                    metadata={
                        "source": "notes",
                        "filename": filepath.name,
                        "path": str(filepath)
                    }
                )
                count += 1
                
        except Exception as e:
            pass  # Skip unreadable files
    
    return count


def build_full_index() -> SearchIndex:
    """Build the complete search index from all sources."""
    print("🔍 Building search index...")
    
    index = SearchIndex()
    
    # Load ChatGPT
    chatgpt_count = load_chatgpt_conversations(index)
    print(f"   📚 ChatGPT: {chatgpt_count} conversations")
    
    # Load notes
    notes_count = load_text_notes(index)
    print(f"   📝 Notes: {notes_count} files")
    
    # Build BM25 index
    total = index.build_index()
    print(f"   ✅ Indexed {total} documents")
    
    # Save
    index.save()
    print(f"   💾 Index saved to {INDEX_DIR}")
    
    return index


# =============================================================================
# SEARCH INTERFACE
# =============================================================================

def search_archive(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search the knowledge archive.
    
    Returns list of matching documents with excerpts.
    """
    index = SearchIndex()
    
    # Try to load existing index
    if not index.load():
        print("⚠️ No index found. Building now...")
        index = build_full_index()
    
    # Search
    results = index.search(query, top_k=top_k)
    
    formatted = []
    for doc, score in results:
        # Extract relevant excerpt
        text = doc["text"]
        query_lower = query.lower()
        
        # Find best excerpt containing query terms
        sentences = text.split('.')
        best_excerpt = ""
        best_score = 0
        
        for sent in sentences:
            sent_lower = sent.lower()
            matches = sum(1 for word in query.split() if word.lower() in sent_lower)
            if matches > best_score and len(sent) < 500:
                best_score = matches
                best_excerpt = sent.strip()
        
        if not best_excerpt:
            best_excerpt = text[:300] + "..."
        
        formatted.append({
            "id": doc["id"],
            "source": doc["metadata"].get("source", "unknown"),
            "title": doc["metadata"].get("title", doc["metadata"].get("filename", "Unknown")),
            "date": doc["metadata"].get("date", "unknown"),
            "score": round(score, 3),
            "excerpt": best_excerpt[:400]
        })
    
    return formatted


def format_results(results: List[Dict], query: str) -> str:
    """Format search results for display."""
    if not results:
        return f"❌ No results found for: '{query}'"
    
    output = [f"🔍 **Found {len(results)} results for:** '{query}'\n"]
    
    for i, r in enumerate(results, 1):
        output.append(f"**{i}. {r['title']}** ({r['source']}, {r['date']})")
        output.append(f"   Score: {r['score']}")
        output.append(f"   \"{r['excerpt']}...\"")
        output.append("")
    
    return "\n".join(output)


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Archive Search - Knowledge Retriever")
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--index", action="store_true", help="Rebuild search index")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--top", type=int, default=5, help="Number of results")
    
    args = parser.parse_args()
    
    print("🧠 Archive Search - Knowledge Retriever")
    print("=" * 40)
    
    if args.index:
        build_full_index()
        
    elif args.stats:
        index = SearchIndex()
        if index.load():
            sources = defaultdict(int)
            for doc in index.documents:
                sources[doc["metadata"].get("source", "unknown")] += 1
            
            print(f"📊 Index Statistics:")
            print(f"   Total documents: {len(index.documents)}")
            for source, count in sources.items():
                print(f"   - {source}: {count}")
        else:
            print("❌ No index found. Run with --index to build.")
            
    elif args.query:
        results = search_archive(args.query, top_k=args.top)
        print(format_results(results, args.query))
        
    else:
        parser.print_help()
        print("\nExample:")
        print("  python archive_search.py --query 'fix python path'")
        print("  python archive_search.py --index")


if __name__ == "__main__":
    main()
