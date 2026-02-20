"""Tests for communication channel system."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from agentcoord.channels import (
    Message,
    MessagePriority,
    MessageType,
    CommunicationChannel,
    TerminalChannel,
    FileChannel,
    DashboardChannel,
    ChannelManager,
    RICH_AVAILABLE,
)


class TestMessage:
    """Test Message dataclass."""

    def test_message_creation_minimal(self):
        """Message can be created with minimal fields."""
        msg = Message(content="Test message", from_agent="agent-1")

        assert msg.content == "Test message"
        assert msg.from_agent == "agent-1"
        assert msg.to_agent is None
        assert msg.channel is None
        assert msg.priority == MessagePriority.NORMAL
        assert msg.message_type == MessageType.STATUS
        assert msg.thread_id is None

    def test_message_auto_timestamp(self):
        """Message auto-generates timestamp if not provided."""
        msg = Message(content="Test", from_agent="agent-1")

        assert msg.timestamp is not None
        assert isinstance(msg.timestamp, datetime)

    def test_message_custom_timestamp(self):
        """Message can have custom timestamp."""
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        msg = Message(content="Test", from_agent="agent-1", timestamp=custom_time)

        assert msg.timestamp == custom_time

    def test_message_auto_metadata_dict(self):
        """Message auto-initializes metadata as empty dict."""
        msg = Message(content="Test", from_agent="agent-1")

        assert msg.metadata is not None
        assert isinstance(msg.metadata, dict)
        assert len(msg.metadata) == 0

    def test_message_custom_metadata(self):
        """Message can have custom metadata."""
        metadata = {"key": "value", "count": 42}
        msg = Message(content="Test", from_agent="agent-1", metadata=metadata)

        assert msg.metadata == metadata
        assert msg.metadata["key"] == "value"
        assert msg.metadata["count"] == 42

    def test_message_all_fields(self):
        """Message can be created with all fields."""
        msg = Message(
            content="Full message",
            from_agent="agent-1",
            to_agent="agent-2",
            channel="engineering",
            priority=MessagePriority.HIGH,
            message_type=MessageType.ERROR,
            thread_id="thread-123",
            metadata={"error_code": 500},
        )

        assert msg.content == "Full message"
        assert msg.from_agent == "agent-1"
        assert msg.to_agent == "agent-2"
        assert msg.channel == "engineering"
        assert msg.priority == MessagePriority.HIGH
        assert msg.message_type == MessageType.ERROR
        assert msg.thread_id == "thread-123"
        assert msg.metadata["error_code"] == 500

    def test_message_priority_enum(self):
        """Message priority uses enum values."""
        msg = Message(content="Test", from_agent="agent-1", priority=MessagePriority.URGENT)

        assert msg.priority == MessagePriority.URGENT
        assert msg.priority.value == "urgent"

    def test_message_type_enum(self):
        """Message type uses enum values."""
        msg = Message(content="Test", from_agent="agent-1", message_type=MessageType.SUCCESS)

        assert msg.message_type == MessageType.SUCCESS
        assert msg.message_type.value == "success"


class TestMessagePriority:
    """Test MessagePriority enum."""

    def test_priority_levels_defined(self):
        """All priority levels are defined."""
        assert MessagePriority.LOW.value == "low"
        assert MessagePriority.NORMAL.value == "normal"
        assert MessagePriority.HIGH.value == "high"
        assert MessagePriority.URGENT.value == "urgent"

    def test_priority_is_string_enum(self):
        """MessagePriority inherits from str."""
        assert isinstance(MessagePriority.NORMAL, str)
        assert MessagePriority.HIGH == "high"


class TestMessageType:
    """Test MessageType enum."""

    def test_message_types_defined(self):
        """All message types are defined."""
        assert MessageType.STATUS.value == "status"
        assert MessageType.ERROR.value == "error"
        assert MessageType.SUCCESS.value == "success"
        assert MessageType.QUESTION.value == "question"
        assert MessageType.ANNOUNCEMENT.value == "announcement"

    def test_message_type_is_string_enum(self):
        """MessageType inherits from str."""
        assert isinstance(MessageType.STATUS, str)
        assert MessageType.ERROR == "error"


class TestTerminalChannel:
    """Test TerminalChannel (console output)."""

    def test_terminal_channel_creation(self):
        """TerminalChannel can be created."""
        channel = TerminalChannel()

        assert channel.name == "terminal"
        assert channel.enabled is True

    def test_terminal_channel_custom_name(self):
        """TerminalChannel can have custom name."""
        channel = TerminalChannel(name="custom-terminal")

        assert channel.name == "custom-terminal"

    def test_terminal_post_message(self, capsys):
        """TerminalChannel.post outputs message."""
        channel = TerminalChannel()
        msg = Message(content="Test post", from_agent="agent-1")

        result = channel.post(msg)

        assert result is True
        captured = capsys.readouterr()
        assert "Test post" in captured.out or "Test post" in captured.err

    def test_terminal_post_disabled(self, capsys):
        """TerminalChannel.post returns False when disabled."""
        channel = TerminalChannel()
        channel.disable()
        msg = Message(content="Should not appear", from_agent="agent-1")

        result = channel.post(msg)

        assert result is False
        captured = capsys.readouterr()
        assert "Should not appear" not in captured.out

    def test_terminal_dm_message(self, capsys):
        """TerminalChannel.dm outputs direct message."""
        channel = TerminalChannel()
        msg = Message(content="Direct message", from_agent="agent-1", to_agent="agent-2")

        result = channel.dm(msg)

        assert result is True
        captured = capsys.readouterr()
        assert "Direct message" in captured.out or "Direct message" in captured.err

    def test_terminal_dm_without_to_agent(self):
        """TerminalChannel.dm returns False if to_agent not specified."""
        channel = TerminalChannel()
        msg = Message(content="Missing recipient", from_agent="agent-1")

        result = channel.dm(msg)

        assert result is False

    def test_terminal_create_thread(self, capsys):
        """TerminalChannel.create_thread falls back to post, returns None."""
        channel = TerminalChannel()
        msg = Message(content="Thread message", from_agent="agent-1")

        result = channel.create_thread(msg)

        assert result is None
        captured = capsys.readouterr()
        assert "Thread message" in captured.out or "Thread message" in captured.err

    def test_terminal_reply_to_thread(self, capsys):
        """TerminalChannel.reply_to_thread outputs indented reply."""
        channel = TerminalChannel()
        msg = Message(
            content="Thread reply", from_agent="agent-1", thread_id="thread-123"
        )

        result = channel.reply_to_thread(msg)

        assert result is True
        captured = capsys.readouterr()
        output = captured.out
        assert "Thread reply" in output

    def test_terminal_supports_formatting_only(self):
        """TerminalChannel only supports formatting feature."""
        channel = TerminalChannel()

        assert channel.supports_feature("formatting") is True
        assert channel.supports_feature("threads") is False
        assert channel.supports_feature("dms") is False
        assert channel.supports_feature("reactions") is False
        assert channel.supports_feature("persistence") is False

    def test_terminal_enable_disable(self):
        """TerminalChannel can be enabled/disabled."""
        channel = TerminalChannel()

        assert channel.enabled is True
        channel.disable()
        assert channel.enabled is False
        channel.enable()
        assert channel.enabled is True


class TestFileChannel:
    """Test FileChannel (JSONL file writing)."""

    def test_file_channel_creation(self, tmp_path):
        """FileChannel can be created."""
        log_file = tmp_path / "test.jsonl"
        channel = FileChannel(name="file", log_path=log_file)

        assert channel.name == "file"
        assert channel.log_path == log_file
        assert channel.enabled is True

    def test_file_channel_default_path(self):
        """FileChannel uses default path if not specified."""
        channel = FileChannel()

        assert channel.log_path == Path("agentcoord_messages.jsonl")

    def test_file_channel_post_writes_jsonl(self, tmp_path):
        """FileChannel.post writes valid JSONL to file."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)

        msg = Message(
            content="Test message",
            from_agent="agent-1",
            channel="engineering",
            priority=MessagePriority.HIGH,
            message_type=MessageType.STATUS,
        )

        result = channel.post(msg)

        assert result is True
        assert log_file.exists()

        # Verify JSONL format
        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "post"
        assert entry["from_agent"] == "agent-1"
        assert entry["channel"] == "engineering"
        assert entry["priority"] == "high"
        assert entry["message_type"] == "status"
        assert entry["content"] == "Test message"
        assert "timestamp" in entry

    def test_file_channel_dm_writes_jsonl(self, tmp_path):
        """FileChannel.dm writes DM to JSONL."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)

        msg = Message(content="Direct message", from_agent="agent-1", to_agent="agent-2")

        result = channel.dm(msg)

        assert result is True

        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "dm"
        assert entry["to_agent"] == "agent-2"

    def test_file_channel_create_thread(self, tmp_path):
        """FileChannel.create_thread generates thread_id and writes to file."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)

        msg = Message(content="Thread start", from_agent="agent-1")

        thread_id = channel.create_thread(msg)

        assert thread_id is not None
        assert isinstance(thread_id, str)
        # Verify it's a valid UUID
        uuid.UUID(thread_id)

        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "thread_create"
        assert entry["thread_id"] == thread_id
        assert entry["metadata"]["thread_start"] is True

    def test_file_channel_reply_to_thread(self, tmp_path):
        """FileChannel.reply_to_thread writes thread reply."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)

        msg = Message(
            content="Thread reply", from_agent="agent-1", thread_id="thread-123"
        )

        result = channel.reply_to_thread(msg)

        assert result is True

        with open(log_file) as f:
            line = f.readline()
            entry = json.loads(line)

        assert entry["event_type"] == "thread_reply"
        assert entry["thread_id"] == "thread-123"

    def test_file_channel_multiple_messages(self, tmp_path):
        """FileChannel appends multiple messages to JSONL."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)

        msg1 = Message(content="First", from_agent="agent-1")
        msg2 = Message(content="Second", from_agent="agent-2")
        msg3 = Message(content="Third", from_agent="agent-3")

        channel.post(msg1)
        channel.post(msg2)
        channel.post(msg3)

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 3
        entries = [json.loads(line) for line in lines]
        assert entries[0]["content"] == "First"
        assert entries[1]["content"] == "Second"
        assert entries[2]["content"] == "Third"

    def test_file_channel_disabled(self, tmp_path):
        """FileChannel.post returns False when disabled."""
        log_file = tmp_path / "messages.jsonl"
        channel = FileChannel(log_path=log_file)
        channel.disable()

        msg = Message(content="Should not write", from_agent="agent-1")

        result = channel.post(msg)

        assert result is False
        assert not log_file.exists()

    def test_file_channel_supports_features(self):
        """FileChannel supports threads and persistence."""
        channel = FileChannel()

        assert channel.supports_feature("threads") is True
        assert channel.supports_feature("persistence") is True
        assert channel.supports_feature("formatting") is False
        assert channel.supports_feature("dms") is False
        assert channel.supports_feature("reactions") is False

    def test_file_channel_creates_parent_directory(self, tmp_path):
        """FileChannel creates parent directories if they don't exist."""
        nested_path = tmp_path / "logs" / "nested" / "messages.jsonl"
        channel = FileChannel(log_path=nested_path)

        msg = Message(content="Test", from_agent="agent-1")
        channel.post(msg)

        assert nested_path.exists()
        assert nested_path.parent.exists()


class TestDashboardChannel:
    """Test DashboardChannel (Rich TUI)."""

    def test_dashboard_channel_creation(self):
        """DashboardChannel can be created."""
        channel = DashboardChannel()

        assert channel.name == "dashboard"
        assert channel.enabled is True
        assert len(channel.messages) == 0
        assert len(channel.threads) == 0

    def test_dashboard_custom_max_messages(self):
        """DashboardChannel respects max_messages limit."""
        channel = DashboardChannel(max_messages=5)

        # Add more messages than max
        for i in range(10):
            msg = Message(content=f"Message {i}", from_agent="agent-1")
            channel.post(msg)

        # Only last 5 should be kept
        assert len(channel.messages) == 5
        assert channel.messages[-1].content == "Message 9"
        assert channel.messages[0].content == "Message 5"

    def test_dashboard_post_message(self):
        """DashboardChannel.post adds message to queue."""
        channel = DashboardChannel()
        msg = Message(content="Test message", from_agent="agent-1")

        result = channel.post(msg)

        assert result is True
        assert len(channel.messages) == 1
        assert channel.messages[0] == msg

    def test_dashboard_dm_message(self):
        """DashboardChannel.dm adds DM to queue."""
        channel = DashboardChannel()
        msg = Message(content="DM", from_agent="agent-1", to_agent="agent-2")

        result = channel.dm(msg)

        assert result is True
        assert len(channel.messages) == 1

    def test_dashboard_create_thread(self):
        """DashboardChannel.create_thread generates thread_id and stores thread."""
        channel = DashboardChannel()
        msg = Message(content="Thread start", from_agent="agent-1")

        thread_id = channel.create_thread(msg)

        assert thread_id is not None
        assert isinstance(thread_id, str)
        assert thread_id in channel.threads
        assert len(channel.threads[thread_id]) == 1
        assert channel.threads[thread_id][0] == msg

    def test_dashboard_reply_to_thread(self):
        """DashboardChannel.reply_to_thread adds reply to thread."""
        channel = DashboardChannel()

        # Create thread
        msg1 = Message(content="Thread start", from_agent="agent-1")
        thread_id = channel.create_thread(msg1)

        # Reply to thread
        msg2 = Message(
            content="Reply", from_agent="agent-2", thread_id=thread_id
        )
        result = channel.reply_to_thread(msg2)

        assert result is True
        assert len(channel.threads[thread_id]) == 2
        assert channel.threads[thread_id][1] == msg2
        # Reply should also appear in main message feed
        assert msg2 in channel.messages

    def test_dashboard_reply_to_nonexistent_thread(self):
        """DashboardChannel.reply_to_thread returns False for invalid thread."""
        channel = DashboardChannel()

        msg = Message(content="Reply", from_agent="agent-1", thread_id="invalid-thread")
        result = channel.reply_to_thread(msg)

        assert result is False

    def test_dashboard_disabled(self):
        """DashboardChannel.post returns False when disabled."""
        channel = DashboardChannel()
        channel.disable()

        msg = Message(content="Should not add", from_agent="agent-1")
        result = channel.post(msg)

        assert result is False
        assert len(channel.messages) == 0

    def test_dashboard_supports_features(self):
        """DashboardChannel supports threads, formatting, and realtime."""
        channel = DashboardChannel()

        assert channel.supports_feature("threads") is True
        assert channel.supports_feature("formatting") is True
        assert channel.supports_feature("realtime") is True
        assert channel.supports_feature("dms") is False
        assert channel.supports_feature("persistence") is False

    @pytest.mark.skipif(not RICH_AVAILABLE, reason="Rich not available")
    def test_dashboard_render_creates_table(self):
        """DashboardChannel._render creates Rich Table."""
        channel = DashboardChannel()
        msg = Message(content="Test", from_agent="agent-1")
        channel.post(msg)

        table = channel._render()

        assert table is not None
        from rich.table import Table
        assert isinstance(table, Table)

    def test_dashboard_render_without_rich(self):
        """DashboardChannel._render returns None if Rich unavailable."""
        with patch("agentcoord.channels.RICH_AVAILABLE", False):
            channel = DashboardChannel()
            result = channel._render()
            assert result is None


class TestChannelManager:
    """Test ChannelManager (multi-channel broadcasting)."""

    def test_channel_manager_creation(self):
        """ChannelManager can be created."""
        manager = ChannelManager()

        assert len(manager.channels) == 0

    def test_add_channel(self):
        """ChannelManager.add_channel adds channel."""
        manager = ChannelManager()
        channel = TerminalChannel(name="terminal")

        manager.add_channel(channel)

        assert len(manager.channels) == 1
        assert manager.get_channel("terminal") == channel

    def test_add_multiple_channels(self):
        """ChannelManager can manage multiple channels."""
        manager = ChannelManager()
        terminal = TerminalChannel(name="terminal")
        file_ch = FileChannel(name="file")

        manager.add_channel(terminal)
        manager.add_channel(file_ch)

        assert len(manager.channels) == 2
        assert manager.get_channel("terminal") == terminal
        assert manager.get_channel("file") == file_ch

    def test_add_channel_replaces_existing(self, caplog):
        """ChannelManager.add_channel replaces existing channel with same name."""
        manager = ChannelManager()
        channel1 = TerminalChannel(name="terminal")
        channel2 = TerminalChannel(name="terminal")

        manager.add_channel(channel1)
        manager.add_channel(channel2)

        # Should have 2 channels in list (not replaced in list)
        assert len(manager.channels) == 2
        # But map should have the new one
        assert manager.get_channel("terminal") == channel2

    def test_remove_channel(self):
        """ChannelManager.remove_channel removes channel."""
        manager = ChannelManager()
        channel = TerminalChannel(name="terminal")
        manager.add_channel(channel)

        manager.remove_channel("terminal")

        assert len(manager.channels) == 0
        assert manager.get_channel("terminal") is None

    def test_get_channel_nonexistent(self):
        """ChannelManager.get_channel returns None for nonexistent channel."""
        manager = ChannelManager()

        result = manager.get_channel("nonexistent")

        assert result is None

    def test_post_broadcasts_to_all_channels(self, tmp_path):
        """ChannelManager.post broadcasts to all enabled channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        results = manager.post(
            channel="engineering",
            content="Broadcast message",
            from_agent="agent-1",
        )

        assert results["file"] is True
        assert results["dashboard"] is True
        assert log_file.exists()
        assert len(dashboard.messages) == 1

    def test_post_skips_disabled_channels(self, tmp_path):
        """ChannelManager.post skips disabled channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        file_ch.disable()

        manager.add_channel(file_ch)

        results = manager.post(
            channel="engineering",
            content="Should not write",
            from_agent="agent-1",
        )

        assert "file" not in results
        assert not log_file.exists()

    def test_dm_broadcasts_to_all_channels(self, tmp_path):
        """ChannelManager.dm sends DM to all enabled channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        results = manager.dm(
            from_agent="agent-1",
            to_agent="agent-2",
            content="Direct message",
        )

        assert results["file"] is True
        assert results["dashboard"] is True

    def test_create_thread_broadcasts(self, tmp_path):
        """ChannelManager.create_thread creates threads on all channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        results = manager.create_thread(
            channel="engineering",
            title="Thread Title",
            content="Thread content",
            from_agent="agent-1",
        )

        # File channel returns thread_id
        assert results["file"] is not None
        assert isinstance(results["file"], str)

        # Dashboard returns thread_id
        assert results["dashboard"] is not None

    def test_reply_to_thread_broadcasts(self, tmp_path):
        """ChannelManager.reply_to_thread sends replies to all channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        # Create thread first
        thread_ids = manager.create_thread(
            channel="eng",
            title="Test",
            content="Start",
            from_agent="agent-1",
        )

        # Reply using dashboard's thread_id
        results = manager.reply_to_thread(
            thread_id=thread_ids["dashboard"],
            channel="eng",
            content="Reply",
            from_agent="agent-2",
        )

        assert results["file"] is True
        assert results["dashboard"] is True

    def test_broadcast(self, tmp_path):
        """ChannelManager.broadcast sends to all channels."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        results = manager.broadcast(
            content="System announcement",
            from_agent="system",
            priority=MessagePriority.URGENT,
            message_type=MessageType.ANNOUNCEMENT,
        )

        assert results["file"] is True
        assert results["dashboard"] is True

    def test_enable_channels(self):
        """ChannelManager.enable_channels enables specific channels."""
        manager = ChannelManager()
        terminal = TerminalChannel(name="terminal")
        file_ch = FileChannel(name="file")

        terminal.disable()
        file_ch.disable()

        manager.add_channel(terminal)
        manager.add_channel(file_ch)

        manager.enable_channels(["terminal"])

        assert terminal.enabled is True
        assert file_ch.enabled is False

    def test_disable_channels(self):
        """ChannelManager.disable_channels disables specific channels."""
        manager = ChannelManager()
        terminal = TerminalChannel(name="terminal")
        file_ch = FileChannel(name="file")

        manager.add_channel(terminal)
        manager.add_channel(file_ch)

        manager.disable_channels(["file"])

        assert terminal.enabled is True
        assert file_ch.enabled is False

    def test_list_channels(self):
        """ChannelManager.list_channels returns channel info."""
        manager = ChannelManager()
        terminal = TerminalChannel(name="terminal")
        file_ch = FileChannel(name="file")

        manager.add_channel(terminal)
        manager.add_channel(file_ch)

        channels = manager.list_channels()

        assert len(channels) == 2

        terminal_info = next(ch for ch in channels if ch["name"] == "terminal")
        assert terminal_info["enabled"] is True
        assert terminal_info["features"]["formatting"] is True
        assert terminal_info["features"]["threads"] is False

        file_info = next(ch for ch in channels if ch["name"] == "file")
        assert file_info["enabled"] is True
        assert file_info["features"]["threads"] is True
        assert file_info["features"]["persistence"] is True


class TestChannelIntegration:
    """Integration tests for channel system."""

    def test_full_workflow(self, tmp_path):
        """Test complete workflow: post, dm, thread create, reply."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)
        dashboard = DashboardChannel(name="dashboard")

        manager.add_channel(file_ch)
        manager.add_channel(dashboard)

        # Post to channel
        manager.post(
            channel="engineering",
            content="Feature completed",
            from_agent="agent-1",
            message_type=MessageType.SUCCESS,
        )

        # Send DM
        manager.dm(
            from_agent="agent-1",
            to_agent="agent-2",
            content="Can you review?",
        )

        # Create thread
        thread_ids = manager.create_thread(
            channel="code-review",
            title="PR #123",
            content="Please review changes",
            from_agent="agent-1",
        )

        # Reply to thread (each channel has its own thread_id)
        # Reply to file channel's thread
        manager.reply_to_thread(
            thread_id=thread_ids["file"],
            channel="code-review",
            content="Looks good from file!",
            from_agent="agent-2",
        )

        # Reply to dashboard's thread
        manager.reply_to_thread(
            thread_id=thread_ids["dashboard"],
            channel="code-review",
            content="Looks good from dashboard!",
            from_agent="agent-3",
        )

        # Verify file output
        with open(log_file) as f:
            lines = f.readlines()

        # File channel should have: post, dm, thread_create, 2 thread_replies
        assert len(lines) == 5
        entries = [json.loads(line) for line in lines]

        assert entries[0]["event_type"] == "post"
        assert entries[0]["content"] == "Feature completed"

        assert entries[1]["event_type"] == "dm"
        assert entries[1]["to_agent"] == "agent-2"

        assert entries[2]["event_type"] == "thread_create"
        assert "PR #123" in entries[2]["content"]

        assert entries[3]["event_type"] == "thread_reply"
        assert "Looks good from file!" in entries[3]["content"]

        assert entries[4]["event_type"] == "thread_reply"
        assert "Looks good from dashboard!" in entries[4]["content"]

        # Verify dashboard state
        # DashboardChannel adds to messages for: post, dm, and thread replies (not thread creation)
        # post + dm + dashboard thread reply (the file thread reply failed on dashboard since it's a different thread_id)
        assert len(dashboard.messages) == 3
        assert len(dashboard.threads) == 1
        assert len(dashboard.threads[thread_ids["dashboard"]]) == 2  # Initial + 1 reply

    def test_priority_and_type_handling(self, tmp_path):
        """Test message priority and type are preserved."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)

        manager.add_channel(file_ch)

        manager.post(
            channel="alerts",
            content="Critical error",
            from_agent="system",
            priority=MessagePriority.URGENT,
            message_type=MessageType.ERROR,
        )

        with open(log_file) as f:
            entry = json.loads(f.readline())

        assert entry["priority"] == "urgent"
        assert entry["message_type"] == "error"

    def test_metadata_preservation(self, tmp_path):
        """Test metadata is preserved through channel."""
        manager = ChannelManager()
        log_file = tmp_path / "messages.jsonl"
        file_ch = FileChannel(name="file", log_path=log_file)

        manager.add_channel(file_ch)

        manager.post(
            channel="metrics",
            content="Performance data",
            from_agent="monitor",
            metadata={"cpu": 75, "memory": 82, "disk": 45},
        )

        with open(log_file) as f:
            entry = json.loads(f.readline())

        assert entry["metadata"]["cpu"] == 75
        assert entry["metadata"]["memory"] == 82
        assert entry["metadata"]["disk"] == 45
