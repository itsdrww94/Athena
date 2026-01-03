"""
DevLoop No-Op Tests
===================
Tests that DevLoop is properly disabled and doesn't execute anything.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDevLoopDisabled:
    """Test that DevLoop is disabled by default."""
    
    def test_devloop_disabled_by_default(self):
        """Test DevLoop is disabled."""
        from workers.devloop import DevLoop
        
        devloop = DevLoop()
        
        assert devloop.enabled is False
    
    def test_devloop_dry_run(self):
        """Test DevLoop dry run mode."""
        from workers.devloop import DevLoop, create_change_request
        
        devloop = DevLoop()
        
        request = create_change_request(
            description="Test change",
            files=["test.py"]
        )
        
        result = devloop.execute(request, dry_run=True)
        
        # Dry run should "succeed" without doing anything
        assert result.success is True
        assert result.tests_passed is True
        assert result.requires_approval is True
    
    def test_devloop_blocked_when_disabled(self):
        """Test DevLoop blocks execution when disabled."""
        from workers.devloop import DevLoop, create_change_request
        
        devloop = DevLoop()
        
        request = create_change_request(description="Test")
        
        # Not dry_run, but DevLoop is disabled
        result = devloop.execute(request, dry_run=False)
        
        assert result.success is False
        assert "disabled" in result.error.lower()


class TestChangeRequest:
    """Test ChangeRequest dataclass."""
    
    def test_create_change_request(self):
        """Test creating a change request."""
        from workers.devloop import create_change_request
        
        request = create_change_request(
            description="Add new feature",
            files=["core/feature.py", "tests/test_feature.py"]
        )
        
        assert request.description == "Add new feature"
        assert len(request.files_to_modify) == 2
        assert len(request.id) == 12  # UUID hex[:12]
    
    def test_change_request_has_timestamp(self):
        """Test change request has timestamp."""
        from workers.devloop import create_change_request
        
        request = create_change_request(description="Test")
        
        assert request.created_at is not None
        assert len(request.created_at) > 10  # ISO format


class TestDevLoopResult:
    """Test DevLoopResult dataclass."""
    
    def test_result_structure(self):
        """Test DevLoopResult structure."""
        from workers.devloop import DevLoopResult
        
        result = DevLoopResult(
            request_id="abc123",
            branch_name="devloop/abc123",
            success=True,
            tests_passed=True,
            changes_made=["file1.py", "file2.py"]
        )
        
        assert result.success is True
        assert result.requires_approval is True  # Default
        assert len(result.changes_made) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
