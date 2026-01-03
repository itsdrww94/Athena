from typing import List, Dict, Any

class EntityResolutionAgent:
    """
    Agent 3: The Librarian / Truth Keeper.
    Merges duplicates, detects conflicts.
    "Is 'john.doe' the same as 'johndoe'?"
    """
    
    def resolve_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Input: Raw list of entities from collectors.
        Output: Cleaned, deduplicated list with 'related_ids' or merged attributes.
        """
        resolved = []
        seen_values = {} # value -> index in resolved

        for e in entities:
            val = e.get("value", "").lower().strip()
            e_type = e.get("type", "")
            
            # Simple Exact Match Strategy
            # (Upgrade 1: Fuzzy matching goes here later)
            
            # Key by value + type + source/tool to prevent over-merging distinct findings
            unique_key = f"{val}|{e_type}|{e.get('tool', 'unknown')}|{e.get('source', 'unknown')}"
            
            if unique_key in seen_values:
                # Merge logic
                existing_idx = seen_values[unique_key]
                existing = resolved[existing_idx]
                
                # Update confidence if new source is higher (naive)
                if e.get("confidence", 0) > existing.get("confidence", 0):
                    existing["confidence"] = e["confidence"]
                
                # Append sources/provenance
                if "sources" not in existing:
                    existing["sources"] = []
                existing["sources"].append(e.get("source_id", "unknown"))
                
                # Check for conflicts 
                # (e.g. same handle, different platform -> might not be same person)
                # For now, assume same value = same entity
            else:
                seen_values[val] = len(resolved)
                e["sources"] = [e.get("source_id", "unknown")]
                resolved.append(e)
                
        return resolved

    def detect_conflicts(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans findings for contradictions.
        e.g. Finding A says 'User is in USA', Finding B says 'User is in UK' (timestamp overlap)
        """
        conflicts = []
        # Placeholder logic
        return conflicts
