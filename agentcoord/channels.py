"""
Communication channel system for AgentCoord.

Provides platform-agnostic abstraction for agent-to-agent communication
supporting multiple delivery channels (terminal, file, dashboard, Slack, Discord)
through a unified interface.
"""

import sys
import json
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import deque
from threading import Lock

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class MessagePriority(str, Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MessageType(str, Enum):
    """Message type for routing and formatting."""
    STATUS = "status"           # General status update
    ERROR = "error"             # Error/failure notification
    SUCCESS = "success"         # Success notification
    QUESTION = "question"       # Request for input/approval
    ANNOUNCEMENT = "announcement"  # Broadcast announcement


@dataclass
class Message:
    """Structured message for channel delivery."""
    content: str
    from_agent: str
    to_agent: Optional[str] = None  # None = broadcast
    channel: Optional[str] = None   # Channel/thread name
    priority: MessagePriority = MessagePriority.NORMAL
    message_type: MessageType = MessageType.STATUS
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None  # For threaded replies

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


class CommunicationChannel(ABC):
    """Abstract base class for communication channels."""

    def __init__(self, name: str):
        """
        Initialize channel adapter.

        Args:
            name: Unique identifier for this channel instance
        """
        self.name = name
        self.enabled = True

    @abstractmethod
    def post(self, message: Message) -> bool:
        """
        Post a message to a channel.

        Args:
            message: Message to post

        Returns:
            True if posted successfully, False otherwise
        """
        pass

    @abstractmethod
    def dm(self, message: Message) -> bool:
        """
        Send a direct message.

        Args:
            message: Message with to_agent specified

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def create_thread(self, message: Message) -> Optional[str]:
        """
        Create a new threaded conversation.

        Args:
            message: Initial message for thread

        Returns:
            Thread ID if supported, None otherwise
        """
        pass

    @abstractmethod
    def reply_to_thread(self, message: Message) -> bool:
        """
        Reply to an existing thread.

        Args:
            message: Message with thread_id specified

        Returns:
            True if posted successfully, False otherwise
        """
        pass

    @abstractmethod
    def supports_feature(self, feature: str) -> bool:
        """
        Check if channel supports a specific feature.

        Args:
            feature: Feature name ("threads", "dms", "formatting", "reactions")

        Returns:
            True if feature is supported
        """
        pass

    def enable(self):
        """Enable this channel."""
        self.enabled = True

    def disable(self):
        """Disable this channel."""
        self.enabled = False


class TerminalChannel(CommunicationChannel):
    """Terminal output channel using Rich for formatting."""

    def __init__(self, name: str = "terminal"):
        super().__init__(name)
        if RICH_AVAILABLE:
            self.console = Console()
            self._color_map = {
                MessagePriority.LOW: "dim white",
                MessagePriority.NORMAL: "white",
                MessagePriority.HIGH: "yellow",
                MessagePriority.URGENT: "red bold"
            }
            self._type_emoji = {
                MessageType.STATUS: "ℹ️",
                MessageType.ERROR: "❌",
                MessageType.SUCCESS: "✅",
                MessageType.QUESTION: "❓",
                MessageType.ANNOUNCEMENT: "📢"
            }
        else:
            self.console = None

    def post(self, message: Message) -> bool:
        """Print message to terminal."""
        if not self.enabled:
            return False

        if self.console:
            color = self._color_map.get(message.priority, "white")
            emoji = self._type_emoji.get(message.message_type, "")

            header = f"{emoji} [{message.from_agent}]"
            if message.channel:
                header += f" → #{message.channel}"

            panel = Panel(
                message.content,
                title=header,
                border_style=color
            )

            self.console.print(panel)
        else:
            # Fallback to basic print if Rich unavailable
            header = f"[{message.from_agent}]"
            if message.channel:
                header += f" → #{message.channel}"
            print(f"{header}: {message.content}")

        return True

    def dm(self, message: Message) -> bool:
        """Print DM to terminal."""
        if not self.enabled or not message.to_agent:
            return False

        if self.console:
            self.console.print(
                f"[bold cyan]DM[/bold cyan] "
                f"[dim]{message.from_agent} → {message.to_agent}:[/dim] "
                f"{message.content}"
            )
        else:
            print(f"DM {message.from_agent} → {message.to_agent}: {message.content}")

        return True

    def create_thread(self, message: Message) -> Optional[str]:
        """Threads not supported in terminal, falls back to post."""
        self.post(message)
        return None

    def reply_to_thread(self, message: Message) -> bool:
        """Thread replies become indented posts."""
        if not self.enabled:
            return False

        if self.console:
            self.console.print(f"  ↳ [{message.from_agent}]: {message.content}")
        else:
            print(f"  ↳ [{message.from_agent}]: {message.content}")

        return True

    def supports_feature(self, feature: str) -> bool:
        """Terminal supports formatting only."""
        return feature in ["formatting"]


class FileChannel(CommunicationChannel):
    """File-based channel for persistent logging."""

    def __init__(self, name: str = "file", log_path: Optional[Path] = None):
        super().__init__(name)
        self.log_path = log_path or Path("agentcoord_messages.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _write_message(self, message: Message, event_type: str) -> bool:
        """Write message to log file."""
        if not self.enabled:
            return False

        log_entry = {
            "timestamp": message.timestamp.isoformat(),
            "event_type": event_type,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "channel": message.channel,
            "priority": message.priority.value,
            "message_type": message.message_type.value,
            "content": message.content,
            "thread_id": message.thread_id,
            "metadata": message.metadata
        }

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            return True
        except Exception as e:
            print(f"FileChannel error: {e}", file=sys.stderr)
            return False

    def post(self, message: Message) -> bool:
        """Log channel post."""
        return self._write_message(message, "post")

    def dm(self, message: Message) -> bool:
        """Log direct message."""
        return self._write_message(message, "dm")

    def create_thread(self, message: Message) -> Optional[str]:
        """Log thread creation."""
        thread_id = str(uuid.uuid4())
        message.thread_id = thread_id
        message.metadata = message.metadata or {}
        message.metadata["thread_start"] = True
        self._write_message(message, "thread_create")
        return thread_id

    def reply_to_thread(self, message: Message) -> bool:
        """Log thread reply."""
        return self._write_message(message, "thread_reply")

    def supports_feature(self, feature: str) -> bool:
        """File channel supports threads and persistence."""
        return feature in ["threads", "persistence"]


class DashboardChannel(CommunicationChannel):
    """Rich TUI dashboard channel."""

    def __init__(self, name: str = "dashboard", max_messages: int = 100):
        super().__init__(name)
        if not RICH_AVAILABLE:
            logger.warning("Rich not available, DashboardChannel will be non-functional")
        self.messages = deque(maxlen=max_messages)
        self.threads = {}  # thread_id -> [messages]
        self.lock = Lock()
        self.live = None  # Rich Live instance

    def start_live_display(self):
        """Start live dashboard rendering."""
        if not RICH_AVAILABLE:
            logger.warning("Rich not available, cannot start live display")
            return

        if self.live is None:
            self.live = Live(self._render(), refresh_per_second=4)
            self.live.start()

    def stop_live_display(self):
        """Stop live dashboard."""
        if self.live:
            self.live.stop()
            self.live = None

    def _render(self) -> Table:
        """Render current state as table."""
        if not RICH_AVAILABLE:
            return None

        table = Table(title="AgentCoord Messages")
        table.add_column("Time", style="dim")
        table.add_column("From", style="cyan")
        table.add_column("To/Channel", style="green")
        table.add_column("Message")

        with self.lock:
            for msg in list(self.messages)[-20:]:  # Last 20 messages
                time_str = msg.timestamp.strftime("%H:%M:%S")
                to_str = msg.to_agent or f"#{msg.channel}" or "broadcast"
                table.add_row(time_str, msg.from_agent, to_str, msg.content)

        return table

    def post(self, message: Message) -> bool:
        """Add message to dashboard."""
        if not self.enabled:
            return False

        with self.lock:
            self.messages.append(message)

        if self.live and RICH_AVAILABLE:
            self.live.update(self._render())

        return True

    def dm(self, message: Message) -> bool:
        """Add DM to dashboard."""
        return self.post(message)

    def create_thread(self, message: Message) -> Optional[str]:
        """Create thread in dashboard."""
        thread_id = str(uuid.uuid4())

        with self.lock:
            self.threads[thread_id] = [message]

        message.thread_id = thread_id
        return thread_id

    def reply_to_thread(self, message: Message) -> bool:
        """Add reply to thread."""
        if not message.thread_id or message.thread_id not in self.threads:
            return False

        with self.lock:
            self.threads[message.thread_id].append(message)
            self.messages.append(message)  # Also show in main feed

        return True

    def supports_feature(self, feature: str) -> bool:
        """Dashboard supports threads, formatting, real-time."""
        return feature in ["threads", "formatting", "realtime"]


class ChannelManager:
    """Manages multiple communication channels and broadcasts."""

    def __init__(self):
        self.channels: List[CommunicationChannel] = []
        self._channel_map = {}  # name -> channel

    def add_channel(self, channel: CommunicationChannel):
        """
        Add a channel adapter.

        Args:
            channel: Channel instance to add
        """
        if channel.name in self._channel_map:
            logger.warning(f"Channel {channel.name} already exists, replacing")

        self.channels.append(channel)
        self._channel_map[channel.name] = channel
        logger.info(f"Added channel: {channel.name}")

    def remove_channel(self, name: str):
        """Remove channel by name."""
        if name in self._channel_map:
            channel = self._channel_map[name]
            self.channels.remove(channel)
            del self._channel_map[name]
            logger.info(f"Removed channel: {name}")

    def get_channel(self, name: str) -> Optional[CommunicationChannel]:
        """Get channel by name."""
        return self._channel_map.get(name)

    def post(
        self,
        channel: str,
        content: str,
        from_agent: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        message_type: MessageType = MessageType.STATUS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Post message to all enabled channels.

        Args:
            channel: Channel name (e.g., "engineering", "status")
            content: Message content
            from_agent: Agent sending message
            priority: Message priority
            message_type: Type of message
            metadata: Additional metadata

        Returns:
            Dict mapping channel name to success status
        """
        message = Message(
            content=content,
            from_agent=from_agent,
            channel=channel,
            priority=priority,
            message_type=message_type,
            metadata=metadata
        )

        results = {}
        for ch in self.channels:
            if ch.enabled:
                results[ch.name] = ch.post(message)

        return results

    def dm(
        self,
        from_agent: str,
        to_agent: str,
        content: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """
        Send direct message via all enabled channels.

        Args:
            from_agent: Sending agent
            to_agent: Receiving agent
            content: Message content
            priority: Message priority
            metadata: Additional metadata

        Returns:
            Dict mapping channel name to success status
        """
        message = Message(
            content=content,
            from_agent=from_agent,
            to_agent=to_agent,
            priority=priority,
            metadata=metadata
        )

        results = {}
        for ch in self.channels:
            if ch.enabled:
                results[ch.name] = ch.dm(message)

        return results

    def create_thread(
        self,
        channel: str,
        title: str,
        content: str,
        from_agent: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> Dict[str, Optional[str]]:
        """
        Create threaded conversation.

        Args:
            channel: Channel name
            title: Thread title
            content: Initial message
            from_agent: Agent creating thread
            priority: Message priority

        Returns:
            Dict mapping channel name to thread ID (None if not supported)
        """
        message = Message(
            content=f"**{title}**\n\n{content}",
            from_agent=from_agent,
            channel=channel,
            priority=priority
        )

        results = {}
        for ch in self.channels:
            if ch.enabled:
                results[ch.name] = ch.create_thread(message)

        return results

    def reply_to_thread(
        self,
        thread_id: str,
        channel: str,
        content: str,
        from_agent: str
    ) -> Dict[str, bool]:
        """
        Reply to existing thread.

        Args:
            thread_id: Thread identifier
            channel: Channel name
            content: Reply content
            from_agent: Agent replying

        Returns:
            Dict mapping channel name to success status
        """
        message = Message(
            content=content,
            from_agent=from_agent,
            channel=channel,
            thread_id=thread_id
        )

        results = {}
        for ch in self.channels:
            if ch.enabled:
                results[ch.name] = ch.reply_to_thread(message)

        return results

    def broadcast(
        self,
        content: str,
        from_agent: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        message_type: MessageType = MessageType.ANNOUNCEMENT
    ) -> Dict[str, bool]:
        """
        Broadcast to all channels (no specific channel).

        Args:
            content: Message content
            from_agent: Agent broadcasting
            priority: Message priority
            message_type: Message type

        Returns:
            Dict mapping channel name to success status
        """
        message = Message(
            content=content,
            from_agent=from_agent,
            priority=priority,
            message_type=message_type
        )

        results = {}
        for ch in self.channels:
            if ch.enabled:
                results[ch.name] = ch.post(message)

        return results

    def enable_channels(self, names: List[str]):
        """Enable specific channels."""
        for name in names:
            if name in self._channel_map:
                self._channel_map[name].enable()

    def disable_channels(self, names: List[str]):
        """Disable specific channels."""
        for name in names:
            if name in self._channel_map:
                self._channel_map[name].disable()

    def list_channels(self) -> List[Dict[str, Any]]:
        """List all channels with their status."""
        return [
            {
                "name": ch.name,
                "enabled": ch.enabled,
                "features": {
                    "threads": ch.supports_feature("threads"),
                    "dms": ch.supports_feature("dms"),
                    "formatting": ch.supports_feature("formatting"),
                    "reactions": ch.supports_feature("reactions"),
                    "persistence": ch.supports_feature("persistence")
                }
            }
            for ch in self.channels
        ]
