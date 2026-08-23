"""Domain errors. Handlers translate these into friendly user messages."""


class StudyAIError(Exception):
    """Base application error."""


class LimitExceededError(StudyAIError):
    """A plan/counter limit was hit (AI requests, quizzes, exams...)."""

    def __init__(self, kind: str = "generic"):
        self.kind = kind
        super().__init__(f"limit_exceeded:{kind}")


class UsageLimitError(LimitExceededError):
    pass


class NotConfiguredError(StudyAIError):
    """Required external configuration (API key, etc.) is missing."""


class InvalidFileError(StudyAIError):
    """Uploaded file is the wrong type, too large, or unreadable."""
