"""
Athena Notion Service
======================
Integration with Notion API for databases and pages.

Setup:
1. Create a Notion integration at https://www.notion.so/my-integrations
2. Add NOTION_API_KEY to .env
3. Share your databases with the integration (click Share → Add connection)
4. Add database IDs to .env (NOTION_FINANCE_DB_ID, NOTION_JOURNAL_DB_ID)
"""

import os
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger("athena.notion")

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Expense:
    """A financial expense entry."""
    amount: float
    category: str
    description: str
    date: date = field(default_factory=date.today)
    vendor: Optional[str] = None
    payment_method: str = "Cash"
    tags: List[str] = field(default_factory=list)
    
    def to_notion_properties(self) -> Dict[str, Any]:
        """Convert to Notion API property format."""
        props = {
            "Name": {"title": [{"text": {"content": self.description}}]},
            "Amount": {"number": self.amount},
            "Category": {"select": {"name": self.category}},
            "Date": {"date": {"start": self.date.isoformat()}},
        }
        
        if self.vendor:
            props["Vendor"] = {"rich_text": [{"text": {"content": self.vendor}}]}
        
        if self.payment_method:
            props["Payment Method"] = {"select": {"name": self.payment_method}}
        
        if self.tags:
            props["Tags"] = {"multi_select": [{"name": tag} for tag in self.tags]}
        
        return props


@dataclass 
class BudgetStatus:
    """Budget status summary."""
    total_spent: float
    budget_limit: float
    remaining: float
    period: str  # e.g., "December 2025"
    by_category: Dict[str, float] = field(default_factory=dict)
    
    @property
    def percent_used(self) -> float:
        if self.budget_limit <= 0:
            return 100.0
        return (self.total_spent / self.budget_limit) * 100


# =============================================================================
# NOTION SERVICE
# =============================================================================

class NotionService:
    """Service for interacting with Notion API."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotionService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.api_key = os.getenv("NOTION_API_KEY", "")
        self.finance_db_id = os.getenv("NOTION_FINANCE_DB_ID", "")
        self.journal_db_id = os.getenv("NOTION_JOURNAL_DB_ID", "")
        
        self.client = None
        self._initialized = True
    
    @property
    def is_configured(self) -> bool:
        """Check if Notion is properly configured."""
        return bool(self.api_key)
    
    def initialize(self) -> bool:
        """Initialize the Notion client."""
        if not self.is_configured:
            logger.warning("Notion API key not set")
            return False
        
        try:
            from notion_client import Client
            self.client = Client(auth=self.api_key)
            logger.info("Notion service initialized")
            return True
        except ImportError:
            logger.error("notion-client not installed. Run: pip install notion-client")
            return False
        except Exception as e:
            logger.error(f"Notion initialization failed: {e}")
            return False
    
    def _ensure_client(self) -> bool:
        """Ensure client is initialized."""
        if self.client is None:
            return self.initialize()
        return True
    
    # =========================================================================
    # EXPENSE TRACKING
    # =========================================================================
    
    def log_expense(self, expense: Expense) -> Dict[str, Any]:
        """
        Log an expense to the Finance database.
        
        Args:
            expense: Expense object to log
            
        Returns:
            Result dict with success status and page ID
        """
        if not self._ensure_client():
            return {"success": False, "error": "Notion not initialized"}
        
        if not self.finance_db_id:
            return {"success": False, "error": "NOTION_FINANCE_DB_ID not set in .env"}
        
        try:
            response = self.client.pages.create(
                parent={"database_id": self.finance_db_id},
                properties=expense.to_notion_properties()
            )
            
            return {
                "success": True,
                "page_id": response["id"],
                "url": response.get("url", ""),
                "message": f"Logged ${expense.amount:.2f} for {expense.category}"
            }
            
        except Exception as e:
            logger.error(f"Failed to log expense: {e}")
            return {"success": False, "error": str(e)}
    
    def get_expenses(self, 
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None,
                     category: Optional[str] = None,
                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        Query expenses from the Finance database.
        
        Args:
            start_date: Filter from this date
            end_date: Filter to this date
            category: Filter by category
            limit: Max results
            
        Returns:
            List of expense records
        """
        if not self._ensure_client():
            return []
        
        if not self.finance_db_id:
            return []
        
        # Build filter
        filters = []
        
        if start_date:
            filters.append({
                "property": "Date",
                "date": {"on_or_after": start_date.isoformat()}
            })
        
        if end_date:
            filters.append({
                "property": "Date", 
                "date": {"on_or_before": end_date.isoformat()}
            })
        
        if category:
            filters.append({
                "property": "Category",
                "select": {"equals": category}
            })
        
        # Construct query
        query_params = {
            "database_id": self.finance_db_id,
            "page_size": min(limit, 100),
            "sorts": [{"property": "Date", "direction": "descending"}]
        }
        
        if filters:
            if len(filters) == 1:
                query_params["filter"] = filters[0]
            else:
                query_params["filter"] = {"and": filters}
        
        try:
            response = self.client.databases.query(**query_params)
            
            expenses = []
            for page in response.get("results", []):
                props = page.get("properties", {})
                
                # Extract values from Notion property format
                expense = {
                    "id": page["id"],
                    "description": self._get_title(props.get("Name", {})),
                    "amount": props.get("Amount", {}).get("number", 0),
                    "category": self._get_select(props.get("Category", {})),
                    "date": self._get_date(props.get("Date", {})),
                    "vendor": self._get_rich_text(props.get("Vendor", {})),
                }
                expenses.append(expense)
            
            return expenses
            
        except Exception as e:
            logger.error(f"Failed to query expenses: {e}")
            return []
    
    def get_budget_status(self, 
                          month: Optional[int] = None,
                          year: Optional[int] = None,
                          budget_limit: float = 2000.0) -> BudgetStatus:
        """
        Get budget status for a month.
        
        Args:
            month: Month (1-12), defaults to current
            year: Year, defaults to current
            budget_limit: Monthly budget limit
            
        Returns:
            BudgetStatus object
        """
        today = date.today()
        month = month or today.month
        year = year or today.year
        
        # Get first and last day of month
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        # Query expenses for the month
        expenses = self.get_expenses(start_date=start_date, end_date=end_date, limit=200)
        
        # Calculate totals
        total_spent = 0.0
        by_category: Dict[str, float] = {}
        
        for exp in expenses:
            amount = exp.get("amount", 0)
            category = exp.get("category", "Other")
            
            total_spent += amount
            by_category[category] = by_category.get(category, 0) + amount
        
        period = f"{date(year, month, 1).strftime('%B %Y')}"
        
        return BudgetStatus(
            total_spent=total_spent,
            budget_limit=budget_limit,
            remaining=budget_limit - total_spent,
            period=period,
            by_category=by_category
        )
    
    # =========================================================================
    # JOURNAL ENTRIES
    # =========================================================================
    
    def log_journal_entry(self, content: str, mood: Optional[str] = None, tags: List[str] = None) -> Dict[str, Any]:
        """Log a journal entry."""
        if not self._ensure_client():
            return {"success": False, "error": "Notion not initialized"}
        
        if not self.journal_db_id:
            return {"success": False, "error": "NOTION_JOURNAL_DB_ID not set"}
        
        try:
            properties = {
                "Name": {"title": [{"text": {"content": f"Entry - {datetime.now().strftime('%Y-%m-%d %H:%M')}"}}]},
                "Date": {"date": {"start": datetime.now().isoformat()}},
            }
            
            if mood:
                properties["Mood"] = {"select": {"name": mood}}
            
            if tags:
                properties["Tags"] = {"multi_select": [{"name": tag} for tag in tags]}
            
            # Create page with content block
            response = self.client.pages.create(
                parent={"database_id": self.journal_db_id},
                properties=properties,
                children=[
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content}}]
                        }
                    }
                ]
            )
            
            return {
                "success": True,
                "page_id": response["id"],
                "url": response.get("url", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to log journal: {e}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # PAGE ANALYSIS
    # =========================================================================
    
    def search_page(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for a page by title.
        """
        if not self._ensure_client():
            return []
            
        try:
            response = self.client.search(
                query=query,
                filter={"value": "page", "property": "object"}
            )
            
            results = []
            for page in response.get("results", []):
                title = self._get_title(page.get("properties", {}).get("title", {})) or \
                        self._get_title(page.get("properties", {}).get("Name", {}))
                
                results.append({
                    "id": page["id"],
                    "title": title,
                    "url": page.get("url", "")
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search page: {e}")
            return []

    def get_page_content(self, page_id: str) -> str:
        """
        Get text content of a page (first 50 blocks).
        """
        if not self._ensure_client():
            return ""
            
        try:
            response = self.client.blocks.children.list(block_id=page_id, page_size=50)
            
            content = []
            for block in response.get("results", []):
                btype = block.get("type")
                if not btype or btype not in block:
                    continue
                
                text_objs = block[btype].get("rich_text", [])
                text = "".join([t.get("text", {}).get("content", "") for t in text_objs])
                
                if text:
                    if btype == "heading_1":
                        content.append(f"# {text}")
                    elif btype == "heading_2":
                        content.append(f"## {text}")
                    elif btype == "heading_3":
                        content.append(f"### {text}")
                    elif btype == "to_do":
                        checked = "[x]" if block["to_do"].get("checked") else "[ ]"
                        content.append(f"{checked} {text}")
                    elif btype == "bulleted_list_item":
                        content.append(f"* {text}")
                    else:
                        content.append(text)
            
            return "\n".join(content)
            
        except Exception as e:
            logger.error(f"Failed to get page content: {e}")
            return f"Error reading page: {e}"
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _get_title(self, prop: Dict) -> str:
        """Extract title text from Notion property."""
        title = prop.get("title", [])
        if title:
            return title[0].get("text", {}).get("content", "")
        return ""
    
    def _get_rich_text(self, prop: Dict) -> str:
        """Extract rich text from Notion property."""
        texts = prop.get("rich_text", [])
        if texts:
            return texts[0].get("text", {}).get("content", "")
        return ""
    
    def _get_select(self, prop: Dict) -> str:
        """Extract select value from Notion property."""
        select = prop.get("select")
        if select:
            return select.get("name", "")
        return ""
    
    def _get_date(self, prop: Dict) -> Optional[str]:
        """Extract date from Notion property."""
        date_obj = prop.get("date")
        if date_obj:
            return date_obj.get("start")
        return None


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_notion_instance: Optional[NotionService] = None

def get_notion_service() -> NotionService:
    """Get or create the Notion service singleton."""
    global _notion_instance
    if _notion_instance is None:
        _notion_instance = NotionService()
    return _notion_instance
