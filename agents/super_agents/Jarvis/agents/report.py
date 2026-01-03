import json
from typing import Dict, Any

class ReportAgent:
    """
    Agent 6: The Clerk.
    Generates HTML or interacts with Notion API.
    """
    
    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def generate_network_graph(self, case_id: str, data: Dict[str, Any]) -> str:
        """
        Generates an interactive network graph using PyVis.
        Returns the filename of the graph.
        """
        try:
            from pyvis.network import Network
            
            # Initialize Network
            net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
            
            # Extract entities and relationships from data
            confirmed = data.get("triage", {}).get("confirmed", [])
            
            # Central Node (Target)
            target = data.get("target", "Target")
            net.add_node(target, title=target, color="#ff0000", size=30)
            
            for item in confirmed:
                # Node for the finding
                val = item.get("value", "Unknown")
                typ = item.get("type", "finding")
                tool = item.get("tool", "unknown")
                
                # Create node
                # Use value as ID, but make it unique if needed
                net.add_node(val, title=f"{typ}\nVia: {tool}", label=val[:20], color="#00ff00")
                
                # Edge from Target to Finding
                net.add_edge(target, val, title=typ)
                
            # Save
            filename = f"graph_{case_id}.html"
            output_path = f"{self.output_dir}/{filename}"
            net.save_graph(output_path)
            return filename
            
        except ImportError:
            print("[ReportAgent] PyVis not installed. Skipping graph.")
            return None
        except Exception as e:
            print(f"[ReportAgent] Graph generation failed: {e}")
            return None

    def generate_html_report(self, case_id: str, data: Dict[str, Any]) -> str:
        """
        Basic HTML generator (Option A).
        """
        html = f"""
        <html>
        <head><title>JARVIS Casefile: {case_id}</title></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>JARVIS Investigation Report</h1>
            <h3>Run ID: {case_id}</h3>
            
            <hr>
            <h2>Execute Summary</h2>
            <p>Risk Score: {data.get("risk", {}).get("total_risk_score", "N/A")}</p>
            
            <hr>
            <h2>Visual Intelligence</h2>
            <!-- GRAPH_LINK_PLACEHOLDER -->
            <p><a href="graph_{case_id}.html" target="_blank" style="font-size: 18px; color: #007bff;">Open Interactive Network Graph</a></p>
            
            <hr>
            <h2>Confimed Findings</h2>
            <ul>
        """
        
        for item in data.get("triage", {}).get("confirmed", []):
            html += f"<li>{item}</li>"
            
        html += """
            </ul>
        </body>
        </html>
        """
        
        # Generate Graph
        graph_file = self.generate_network_graph(case_id, data)
        
        # Save to file
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"{case_id}.html"
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[ReportAgent] Report saved to: {file_path}")
        except Exception as e:
            print(f"[ReportAgent] Failed to save report: {e}")
            
        return html

    def generate_notion_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepares JSON for Notion API (Option B).
        """
        return {
            "parent": {"database_id": "TODO"},
            "properties": {
                "Name": {"title": [{"text": {"content": "JARVIS Report"}}]}
            }
        }
