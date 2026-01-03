from typing import List, Dict, Any
import os
import glob

class KnowledgeAgent:
    """
    Agent 7: The Librarian (Local RAG)
    """
    
    def __init__(self, knowledge_dir: str = "data/knowledge"):
        self.knowledge_dir = knowledge_dir
        
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Scans local markdown/text files for the query.
        Returns snippets.
        """
        results = []
        if not os.path.exists(self.knowledge_dir):
            return [{"error": f"Directory not found: {self.knowledge_dir}"}]
            
        # Recursive search for MD/TXT
        files = glob.glob(f"{self.knowledge_dir}/**/*.md", recursive=True) + \
                glob.glob(f"{self.knowledge_dir}/**/*.txt", recursive=True)
                
        print(f"[KnowledgeAgent] Scanning {len(files)} files for '{query}'...")
        
        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                if query.lower() in content.lower():
                    # Simple Snippet Extraction
                    idx = content.lower().find(query.lower())
                    start = max(0, idx - 100)
                    end = min(len(content), idx + 200)
                    snippet = "..." + content[start:end].replace("\n", " ") + "..."
                    
                    results.append({
                        "file": os.path.basename(file_path),
                        "path": file_path,
                        "snippet": snippet
                    })
            except Exception as e:
                print(f"[KnowledgeAgent] Error reading {file_path}: {e}")
                
        # Rank by relevance? (Naive, just return all)
        return results[:5] # Top 5
