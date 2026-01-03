#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                       T H E   S O C I O L O G I S T                           ║
║                    Engine B: Relationships & Sentiment                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Quantifies social health and identifies relationship trends.

Analysis:
1. Reciprocity Ratio - Who puts in more effort
2. Sentiment Velocity - Relationship trajectory over time
3. Initiation Rate - Who starts conversations
4. Inner Circle Detection - Most engaged contacts
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import statistics

from .utils import normalize_timestamp, clean_pii


class Sociologist:
    """
    Analyzes social communication patterns and relationship health.
    """
    
    def __init__(self, user_name: str = None):
        self.user_name = user_name  # Will be detected if not provided
        self.messages = []  # List of (timestamp, sender, recipient, content, thread_id)
        self.contacts = defaultdict(lambda: {
            "sent": 0,
            "received": 0,
            "messages": [],
            "timestamps": []
        })
    
    def add_message(self, timestamp: datetime, sender: str, recipient: str = None,
                    content: str = "", thread_id: str = None) -> None:
        """Add a message for analysis."""
        if timestamp and sender:
            self.messages.append({
                "timestamp": timestamp,
                "sender": sender,
                "recipient": recipient or "unknown",
                "content": content,
                "thread_id": thread_id
            })
            
            # Track by contact
            is_user = self._is_user(sender)
            other = recipient if is_user else sender
            
            if other:
                if is_user:
                    self.contacts[other]["sent"] += 1
                else:
                    self.contacts[other]["received"] += 1
                
                self.contacts[other]["messages"].append(content)
                self.contacts[other]["timestamps"].append(timestamp)
    
    def _is_user(self, name: str) -> bool:
        """Check if the sender is the user (vs a contact)."""
        if not name:
            return False
        
        if self.user_name:
            return name.lower() == self.user_name.lower()
        
        # Heuristics for common user identifiers
        user_indicators = ["you", "me", "drew", "owner"]
        return any(ind in name.lower() for ind in user_indicators)
    
    def detect_user_name(self) -> Optional[str]:
        """Auto-detect the user's name from message patterns."""
        sender_counts = defaultdict(int)
        
        for msg in self.messages:
            sender_counts[msg["sender"]] += 1
        
        # User is likely the most frequent sender
        if sender_counts:
            most_common = max(sender_counts.items(), key=lambda x: x[1])
            self.user_name = most_common[0]
            return self.user_name
        
        return None
    
    def get_top_contacts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most engaged contacts by total message volume."""
        contact_scores = []
        
        for name, data in self.contacts.items():
            total = data["sent"] + data["received"]
            contact_scores.append({
                "name": name,
                "total_messages": total,
                "sent": data["sent"],
                "received": data["received"]
            })
        
        return sorted(contact_scores, key=lambda x: x["total_messages"], reverse=True)[:limit]
    
    def get_reciprocity_ratio(self, contact: str = None) -> Dict[str, Any]:
        """
        Calculate message reciprocity (who puts in more effort).
        
        Ratio > 1.0 = User sends more
        Ratio < 1.0 = Contact sends more
        Ratio = 1.0 = Balanced
        """
        if contact:
            contacts_to_check = {contact: self.contacts.get(contact, {})}
        else:
            contacts_to_check = dict(self.contacts)
        
        results = {}
        
        for name, data in contacts_to_check.items():
            sent = data.get("sent", 0)
            received = data.get("received", 0)
            
            if received == 0:
                ratio = float('inf') if sent > 0 else 0
            else:
                ratio = sent / received
            
            flag = None
            if ratio > 2.0:
                flag = "⚠️ High effort / Low return"
            elif ratio < 0.5:
                flag = "💤 Low engagement from you"
            elif 0.8 <= ratio <= 1.2:
                flag = "✅ Balanced"
            
            results[name] = {
                "sent": sent,
                "received": received,
                "ratio": round(ratio, 2) if ratio != float('inf') else "∞",
                "flag": flag
            }
        
        return results
    
    def get_sentiment_analysis(self, contact: str = None) -> Dict[str, Any]:
        """
        Analyze sentiment of messages using TextBlob or VADER.
        
        Returns sentiment scores and trend over time.
        """
        try:
            from textblob import TextBlob
            use_textblob = True
        except ImportError:
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                vader = SentimentIntensityAnalyzer()
                use_textblob = False
            except ImportError:
                return {"error": "Install textblob or vaderSentiment for sentiment analysis"}
        
        if contact:
            messages = self.contacts.get(contact, {}).get("messages", [])
            contacts_to_analyze = {contact: messages}
        else:
            contacts_to_analyze = {name: data["messages"] 
                                   for name, data in self.contacts.items()}
        
        results = {}
        
        for name, messages in contacts_to_analyze.items():
            if not messages:
                continue
            
            sentiments = []
            for msg in messages[-500:]:  # Last 500 messages
                msg_clean = clean_pii(msg)
                
                if use_textblob:
                    blob = TextBlob(msg_clean)
                    sentiments.append(blob.sentiment.polarity)  # -1 to 1
                else:
                    scores = vader.polarity_scores(msg_clean)
                    sentiments.append(scores["compound"])  # -1 to 1
            
            if sentiments:
                avg_sentiment = statistics.mean(sentiments)
                
                # Calculate trend (slope of sentiment over time)
                if len(sentiments) >= 10:
                    first_half = statistics.mean(sentiments[:len(sentiments)//2])
                    second_half = statistics.mean(sentiments[len(sentiments)//2:])
                    trend = second_half - first_half
                else:
                    trend = 0
                
                # Interpret
                if avg_sentiment > 0.2:
                    mood = "positive"
                elif avg_sentiment < -0.2:
                    mood = "negative"
                else:
                    mood = "neutral"
                
                if trend < -0.15:
                    trend_desc = "⚠️ Drifting apart"
                elif trend > 0.15:
                    trend_desc = "📈 Relationship improving"
                else:
                    trend_desc = "Stable"
                
                results[name] = {
                    "avg_sentiment": round(avg_sentiment, 3),
                    "mood": mood,
                    "trend": round(trend, 3),
                    "trend_description": trend_desc,
                    "messages_analyzed": len(sentiments)
                }
        
        return results
    
    def get_initiation_rate(self, contact: str = None, gap_hours: int = 24) -> Dict[str, Any]:
        """
        Calculate who initiates conversations after gaps.
        
        A conversation is "initiated" if it's the first message after a gap of X hours.
        """
        if contact:
            contacts_to_check = [contact]
        else:
            contacts_to_check = list(self.contacts.keys())
        
        results = {}
        
        for name in contacts_to_check:
            data = self.contacts.get(name, {})
            timestamps = sorted(data.get("timestamps", []))
            
            if len(timestamps) < 2:
                continue
            
            user_initiations = 0
            contact_initiations = 0
            
            # Find messages after gaps
            for i in range(1, len(timestamps)):
                gap = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                
                if gap >= gap_hours:
                    # Find who sent the first message after the gap
                    for msg in self.messages:
                        if msg["timestamp"] == timestamps[i]:
                            if self._is_user(msg["sender"]):
                                user_initiations += 1
                            else:
                                contact_initiations += 1
                            break
            
            total = user_initiations + contact_initiations
            if total > 0:
                user_rate = (user_initiations / total) * 100
                
                if user_rate > 70:
                    flag = "⚠️ You always reach out first"
                elif user_rate < 30:
                    flag = "They usually reach out first"
                else:
                    flag = "✅ Balanced initiation"
                
                results[name] = {
                    "user_initiations": user_initiations,
                    "contact_initiations": contact_initiations,
                    "user_rate_pct": round(user_rate, 1),
                    "flag": flag
                }
        
        return results
    
    def get_inner_circle(self, top_n: int = 5) -> Dict[str, Any]:
        """
        Identify the user's inner circle based on engagement patterns.
        
        Scores based on: frequency, reciprocity, recency
        """
        scores = {}
        now = datetime.now()
        
        for name, data in self.contacts.items():
            sent = data.get("sent", 0)
            received = data.get("received", 0)
            total = sent + received
            
            if total < 5:  # Need minimum engagement
                continue
            
            # Frequency score (normalized)
            freq_score = min(total / 100, 1.0) * 40
            
            # Reciprocity score
            if sent > 0 and received > 0:
                ratio = min(sent/received, received/sent)  # Closer to 1 = better
                recip_score = ratio * 30
            else:
                recip_score = 0
            
            # Recency score
            timestamps = data.get("timestamps", [])
            if timestamps:
                most_recent = max(timestamps)
                days_ago = (now - most_recent).days
                recency_score = max(0, 30 - days_ago)  # Full points if today
            else:
                recency_score = 0
            
            scores[name] = {
                "total_score": freq_score + recip_score + recency_score,
                "frequency": round(freq_score, 1),
                "reciprocity": round(recip_score, 1),
                "recency": round(recency_score, 1),
                "total_messages": total
            }
        
        # Sort and get top N
        sorted_contacts = sorted(scores.items(), key=lambda x: x[1]["total_score"], reverse=True)
        
        inner_circle = [name for name, _ in sorted_contacts[:top_n]]
        drift_risk = [name for name, data in sorted_contacts 
                      if data["recency"] < 10 and data["total_score"] > 30]
        
        return {
            "inner_circle": inner_circle,
            "drift_risk": drift_risk[:5],
            "scores": dict(sorted_contacts[:top_n * 2])
        }
    
    def analyze(self) -> Dict[str, Any]:
        """
        Run full sociological analysis.
        
        Returns:
            Complete social health profile
        """
        if not self.user_name:
            self.detect_user_name()
        
        top_contacts = self.get_top_contacts(10)
        top_names = [c["name"] for c in top_contacts[:5]]
        
        return {
            "engine": "sociologist",
            "messages_analyzed": len(self.messages),
            "contacts_found": len(self.contacts),
            "detected_user": self.user_name,
            "top_contacts": top_contacts,
            "inner_circle": self.get_inner_circle(),
            "reciprocity": {name: self.get_reciprocity_ratio(name).get(name) 
                           for name in top_names},
            "sentiment": self.get_sentiment_analysis(),
            "initiation": self.get_initiation_rate()
        }
