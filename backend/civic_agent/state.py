"""Conversation state management for the civic algorithm agent."""

from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """A single message in the conversation history."""
    role: str
    text: str


@dataclass
class ConversationState:
    """Tracks conversation context across multiple turns."""
    
    history: list[ChatMessage] = field(default_factory=list)
    last_options: list[str] = field(default_factory=list)
    current_topic: str | None = None
    current_subtopic: str | None = None
    clarification_depth: int = 0
    
    def add_message(self, role: str, text: str) -> None:
        """Add a message to the conversation history."""
        self.history.append(ChatMessage(role=role, text=text))
    
    def set_options(self, options: list[str]) -> None:
        """Update the last offered options."""
        self.last_options = options
    
    def clear_options(self) -> None:
        """Clear the last offered options."""
        self.last_options = []
    
    def increment_depth(self) -> None:
        """Increment clarification depth."""
        self.clarification_depth += 1
    
    def reset_depth(self) -> None:
        """Reset clarification depth when user gets specific."""
        self.clarification_depth = 0
    
    def to_dict(self) -> dict:
        """Convert state to dictionary for JSON serialization."""
        return {
            "history": [{"role": msg.role, "text": msg.text} for msg in self.history],
            "last_options": self.last_options,
            "current_topic": self.current_topic,
            "current_subtopic": self.current_subtopic,
            "clarification_depth": self.clarification_depth,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """Create state from dictionary."""
        history = [ChatMessage(role=msg["role"], text=msg["text"]) for msg in data.get("history", [])]
        return cls(
            history=history,
            last_options=data.get("last_options", []),
            current_topic=data.get("current_topic"),
            current_subtopic=data.get("current_subtopic"),
            clarification_depth=data.get("clarification_depth", 0),
        )
