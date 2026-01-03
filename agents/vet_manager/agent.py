#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        V E T   M A N A G E R                                  ║
║                        "Sushi & Astro's Agent"                                 ║
║                                                                               ║
║  Division III: LifeOS (Health & Leisure)                                      ║
║  Track cat vaccinations, food inventory, and care reminders                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Cats: Sushi and Astro

Features:
  - Track vaccination schedules
  - Food inventory and reorder reminders
  - Vet appointment reminders
  - Health notes

Usage:
  python vet_manager.py --action status
  python vet_manager.py --action add-food --brand "Blue Buffalo" --date today
  python vet_manager.py --action check
"""

import os
import sys
import json
import argparse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
PET_DATA_FILE = DATA_DIR / "pet_data.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Thresholds
FOOD_REORDER_DAYS = 25  # Alert if food purchase > X days ago
VACCINE_REMINDER_DAYS = 30  # Alert X days before due


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Pet:
    """A pet (cat)."""
    name: str
    species: str = "cat"
    birth_date: str = ""
    last_vet_visit: str = ""
    vaccinations: Dict[str, str] = field(default_factory=dict)  # {vaccine_name: due_date}
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "species": self.species,
            "birth_date": self.birth_date,
            "last_vet_visit": self.last_vet_visit,
            "vaccinations": self.vaccinations,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Pet":
        return cls(
            name=data.get("name", "Unknown"),
            species=data.get("species", "cat"),
            birth_date=data.get("birth_date", ""),
            last_vet_visit=data.get("last_vet_visit", ""),
            vaccinations=data.get("vaccinations", {}),
            notes=data.get("notes", [])
        )


@dataclass
class FoodPurchase:
    """A food purchase record."""
    date: str
    brand: str
    quantity: str = "1 bag"
    pet: str = "all"


# =============================================================================
# DATA PERSISTENCE
# =============================================================================

def load_pet_data() -> Dict[str, Any]:
    """Load pet data from file."""
    if PET_DATA_FILE.exists():
        try:
            with open(PET_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Default data for Sushi & Astro
    return {
        "pets": [
            {
                "name": "Sushi",
                "species": "cat",
                "birth_date": "",
                "last_vet_visit": "",
                "vaccinations": {
                    "Rabies": "",
                    "FVRCP": ""
                },
                "notes": []
            },
            {
                "name": "Astro",
                "species": "cat",
                "birth_date": "",
                "last_vet_visit": "",
                "vaccinations": {
                    "Rabies": "",
                    "FVRCP": ""
                },
                "notes": []
            }
        ],
        "food_purchases": [],
        "reminders": []
    }


def save_pet_data(data: Dict[str, Any]) -> None:
    """Save pet data to file."""
    with open(PET_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# =============================================================================
# ACTIONS
# =============================================================================

def get_status() -> str:
    """Get overall pet status."""
    data = load_pet_data()
    output = []
    
    output.append("=" * 60)
    output.append("🐱 VET MANAGER - Pet Status")
    output.append("=" * 60)
    output.append("")
    
    # Pets
    for pet_data in data.get("pets", []):
        pet = Pet.from_dict(pet_data)
        output.append(f"🐾 {pet.name}")
        
        if pet.last_vet_visit:
            output.append(f"   Last Vet: {pet.last_vet_visit}")
        else:
            output.append("   Last Vet: Not recorded")
        
        # Vaccinations
        output.append("   Vaccinations:")
        for vax, due in pet.vaccinations.items():
            if due:
                due_date = datetime.strptime(due, "%Y-%m-%d").date()
                days_until = (due_date - date.today()).days
                if days_until < 0:
                    status = f"⚠️ OVERDUE by {abs(days_until)} days"
                elif days_until < VACCINE_REMINDER_DAYS:
                    status = f"📅 Due in {days_until} days"
                else:
                    status = f"✅ Due: {due}"
                output.append(f"     • {vax}: {status}")
            else:
                output.append(f"     • {vax}: Not scheduled")
        
        output.append("")
    
    # Food status
    output.append("🍽️ Food Status:")
    food_purchases = data.get("food_purchases", [])
    if food_purchases:
        latest = food_purchases[-1]
        purchase_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
        days_ago = (date.today() - purchase_date).days
        
        if days_ago > FOOD_REORDER_DAYS:
            output.append(f"   ⚠️ Last purchase: {days_ago} days ago - TIME TO REORDER!")
        else:
            output.append(f"   ✅ Last purchase: {days_ago} days ago ({latest['brand']})")
    else:
        output.append("   📝 No purchases recorded - Add with: --action add-food")
    
    output.append("")
    output.append("=" * 60)
    
    return "\n".join(output)


def check_reminders() -> str:
    """Check for any due reminders or alerts."""
    data = load_pet_data()
    alerts = []
    
    # Check food
    food_purchases = data.get("food_purchases", [])
    if food_purchases:
        latest = food_purchases[-1]
        purchase_date = datetime.strptime(latest["date"], "%Y-%m-%d").date()
        days_ago = (date.today() - purchase_date).days
        
        if days_ago > FOOD_REORDER_DAYS:
            alerts.append(f"🍽️ Buy cat food! Last purchase was {days_ago} days ago.")
    else:
        alerts.append("🍽️ No food purchases recorded. Add one to track inventory.")
    
    # Check vaccinations
    for pet_data in data.get("pets", []):
        pet = Pet.from_dict(pet_data)
        for vax, due in pet.vaccinations.items():
            if due:
                try:
                    due_date = datetime.strptime(due, "%Y-%m-%d").date()
                    days_until = (due_date - date.today()).days
                    
                    if days_until < 0:
                        alerts.append(f"💉 {pet.name}'s {vax} is OVERDUE by {abs(days_until)} days!")
                    elif days_until < VACCINE_REMINDER_DAYS:
                        alerts.append(f"💉 {pet.name}'s {vax} due in {days_until} days")
                except:
                    pass
    
    if not alerts:
        return "✅ All good! No pet-related reminders."
    
    output = ["🚨 PET REMINDERS:", ""]
    output.extend(f"  • {alert}" for alert in alerts)
    
    return "\n".join(output)


def add_food_purchase(brand: str, purchase_date: str = None, quantity: str = "1 bag") -> str:
    """Record a food purchase."""
    data = load_pet_data()
    
    if "food_purchases" not in data:
        data["food_purchases"] = []
    
    # Parse date
    if purchase_date in [None, "today", ""]:
        purchase_date = date.today().isoformat()
    
    data["food_purchases"].append({
        "date": purchase_date,
        "brand": brand,
        "quantity": quantity
    })
    
    save_pet_data(data)
    
    return f"✅ Recorded food purchase: {brand} ({quantity}) on {purchase_date}"


def update_vaccine(pet_name: str, vaccine: str, due_date: str) -> str:
    """Update vaccination due date."""
    data = load_pet_data()
    
    for pet_data in data.get("pets", []):
        if pet_data["name"].lower() == pet_name.lower():
            if "vaccinations" not in pet_data:
                pet_data["vaccinations"] = {}
            pet_data["vaccinations"][vaccine] = due_date
            save_pet_data(data)
            return f"✅ Updated {pet_name}'s {vaccine} due date to {due_date}"
    
    return f"❌ Pet '{pet_name}' not found"


def add_note(pet_name: str, note: str) -> str:
    """Add a health note for a pet."""
    data = load_pet_data()
    
    for pet_data in data.get("pets", []):
        if pet_data["name"].lower() == pet_name.lower():
            if "notes" not in pet_data:
                pet_data["notes"] = []
            pet_data["notes"].append({
                "date": date.today().isoformat(),
                "note": note
            })
            save_pet_data(data)
            return f"✅ Added note for {pet_name}"
    
    return f"❌ Pet '{pet_name}' not found"


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Vet Manager - Pet care tracker for Sushi & Astro"
    )
    
    parser.add_argument(
        "--action", "-a",
        choices=["status", "check", "add-food", "update-vaccine", "add-note"],
        default="status",
        help="Action to perform"
    )
    
    parser.add_argument("--pet", "-p", type=str, help="Pet name (Sushi or Astro)")
    parser.add_argument("--brand", "-b", type=str, help="Food brand")
    parser.add_argument("--date", "-d", type=str, default="today", help="Date (YYYY-MM-DD or 'today')")
    parser.add_argument("--vaccine", "-v", type=str, help="Vaccine name")
    parser.add_argument("--note", "-n", type=str, help="Health note text")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.action == "status":
        result = get_status()
        
    elif args.action == "check":
        result = check_reminders()
        
    elif args.action == "add-food":
        if not args.brand:
            print("❌ --brand required for add-food")
            sys.exit(1)
        result = add_food_purchase(args.brand, args.date)
        
    elif args.action == "update-vaccine":
        if not args.pet or not args.vaccine or not args.date:
            print("❌ --pet, --vaccine, and --date required")
            sys.exit(1)
        result = update_vaccine(args.pet, args.vaccine, args.date)
        
    elif args.action == "add-note":
        if not args.pet or not args.note:
            print("❌ --pet and --note required")
            sys.exit(1)
        result = add_note(args.pet, args.note)
        
    else:
        result = "Unknown action"
    
    if args.json:
        print(json.dumps(load_pet_data(), indent=2))
    else:
        print(result)


if __name__ == "__main__":
    main()
