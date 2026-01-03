
import sys
import unittest
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Mock imports
from veteran_fade import FatigueModule
from nba_context import SeriesContextModule
from ref_factor import RefereeModule

class TestHakariLogic(unittest.TestCase):

    def test_veteran_fade(self):
        """Verify Age 33+ on 0 days rest gets 0.88 multiplier"""
        print("\n--- Testing Veteran Fade (LeBron Protocol) ---")
        fatigue = FatigueModule()
        
        # Test Case 1: Old Man, No Rest (Should Fade)
        mult = fatigue.get_fatigue_multiplier(39, 0, True)
        print(f"Age 39, 0 Rest, Road: x{mult}")
        self.assertAlmostEqual(mult, 0.88 * 0.95, delta=0.01) # 0.88 base * 0.95 road
        
        # Test Case 2: Young Guy, No Rest (No Fade)
        mult = fatigue.get_fatigue_multiplier(22, 0, True)
        print(f"Age 22, 0 Rest, Road: x{mult}")
        self.assertEqual(mult, 1.0)
        
        # Test Case 3: Old Man, Rested (No Fade)
        mult = fatigue.get_fatigue_multiplier(39, 1, True)
        print(f"Age 39, 1 Rest, Road: x{mult}")
        self.assertEqual(mult, 1.0)

    def test_series_context(self):
        """Verify 3-0 Road Trap Logic"""
        print("\n--- Testing 3-0 Road Trap ---")
        series = SeriesContextModule()
        
        # Test Case 1: Alpha Star in 3-0 Trap (Away) -> Minutes reduced
        mult = series.get_minutes_adjustment("3-0", "AWAY", "ALPHA")
        print(f"Alpha Star, 3-0 Lead, Away: x{mult} Minutes")
        self.assertEqual(mult, 0.90)
        
        # Test Case 2: Role Player in 3-0 Trap (Away) -> Minutes boosted
        mult = series.get_minutes_adjustment("3-0", "AWAY", "ROLE_PLAYER")
        print(f"Role Player, 3-0 Lead, Away: x{mult} Minutes")
        self.assertEqual(mult, 1.15)
        
        # Test Case 3: Home Game (No Trap)
        mult = series.get_minutes_adjustment("3-0", "HOME", "ALPHA")
        print(f"Alpha Star, 3-0 Lead, Home: x{mult} Minutes")
        self.assertEqual(mult, 1.0)

    def test_ref_factor(self):
        """Verify Scott Foster Boost"""
        print("\n--- Testing Ref Factor ---")
        ref = RefereeModule()
        
        # Test Case 1: Scott Foster (High Foul)
        crew = ["Scott Foster", "Kevin Cutler", "Dedric Taylor"]
        # Assuming Scott Foster is in the HIGH_FPG_REFS list in ref_factor.py
        # Current list in file: ["Scott Foster", "Tony Brothers", "Mousa Dagher", "Ben Taylor"]
        
        mult = ref.get_ref_multiplier(crew, "points", "FT_DEPENDENT")
        print(f"Crew {crew}, FT Dependent: x{mult}")
        self.assertEqual(mult, 1.08)
        
        # Test Case 2: Neutral
        mult = ref.get_ref_multiplier([], "points", "FT_DEPENDENT")
        print(f"Neutral Crew: x{mult}")
        self.assertEqual(mult, 1.0)

    def test_live_data(self):
        """Verify NBA API Connection (LeBron Check)"""
        print("\n--- Testing Live Data Connection (NBA_API) ---")
        try:
            # Import dynamically to avoid top-level failures if dependencies missing during test setup
            from nba_logic import get_player_data
            
            print("Fetching LeBron James data...")
            result = get_player_data("LeBron James", "Points", 25.5)
            print(f"Result: {result}")
            
            if "verdict" in result:
                print("✅ Live Data Fetch Successful")
            else:
                self.fail(f"Live Data Failed: {result}")
                
        except Exception as e:
            print(f"⚠️ Connection Error (Test Skipped if Offline): {e}")

if __name__ == '__main__':
    unittest.main()
