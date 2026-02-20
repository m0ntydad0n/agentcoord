import pytest
import tempfile
import os
import time
import threading
import json
from unittest.mock import patch, MagicMock
from agentcoord.locks import FileLock


class TestFileLock:
    @pytest.fixture
    def temp_lock_file(self):
        """Create a temporary file for lock testing"""
        fd, path = tempfile.mkstemp(suffix='.lock')
        os.close(fd)
        os.unlink(path)  # Remove the file, we just want the path
        yield path
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    def test_lock_creation(self, temp_lock_file):
        """Test basic lock creation"""
        lock = FileLock(temp_lock_file)
        assert lock.lock_file == temp_lock_file
        assert lock.timeout == 10  # default timeout
        assert lock.ttl == 300     # default TTL

    def test_lock_creation_with_params(self, temp_lock_file):
        """Test lock creation with custom parameters"""
        lock = FileLock(temp_lock_file, timeout=30, ttl=600)
        assert lock.timeout == 30
        assert lock.ttl == 600

    def test_acquire_lock_success(self, temp_lock_file):
        """Test successful lock acquisition"""
        lock = FileLock(temp_lock_file)
        
        assert lock.acquire() is True
        assert os.path.exists(temp_lock_file)
        
        # Verify lock file contains process info
        with open(temp_lock_file, 'r') as f:
            lock_data = json.load(f)
        
        assert 'pid' in lock_data
        assert 'acquired_at' in lock_data
        assert 'expires_at' in lock_data
        assert lock_data['pid'] == os.getpid()

    def test_acquire_lock_already_held(self, temp_lock_file):
        """Test acquiring lock when already held by same process"""
        lock = FileLock(temp_lock_file)
        
        assert lock.acquire() is True
        assert lock.acquire() is True  # Should succeed for same process

    def test_acquire_lock_blocked_by_other_process(self, temp_lock_file):
        """Test acquiring lock blocked by another process"""
        # Create lock file with different PID
        other_pid = os.getpid() + 1000  # Fake different PID
        lock_data = {
            'pid': other_pid,
            'acquired_at': time.time(),
            'expires_at': time.time() + 300
        }
        
        with open(temp_lock_file, 'w') as f:
            json.dump(lock_data, f)
        
        lock = FileLock(temp_lock_file, timeout=1)  # Short timeout
        assert lock.acquire() is False

    def test_acquire_lock_expired_ttl(self, temp_lock_file):
        """Test acquiring lock when existing lock has expired"""
        # Create expired lock file
        other_pid = os.getpid() + 1000
        lock_data = {
            'pid': other_pid,
            'acquired_at': time.time() - 400,
            'expires_at': time.time() - 100  # Expired
        }
        
        with open(temp_lock_file, 'w') as f:
            json.dump(lock_data, f)
        
        lock = FileLock(temp_lock_file)
        assert lock.acquire() is True  # Should acquire expired lock

    def test_release_lock_success(self, temp_lock_file):
        """Test successful lock release"""
        lock = FileLock(temp_lock_file)
        
        assert lock.acquire() is True
        assert os.path.exists(temp_lock_file)
        
        assert lock.release() is True
        assert not os.path.exists