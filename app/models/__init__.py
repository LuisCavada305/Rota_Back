"""Aggregate imports to ensure string-based relationships see their targets."""

# Base metadata
from .base import Base  # noqa: F401

# Lookup tables
from .lookups import LkSex, LkRole, LkColor  # noqa: F401
from .lk_item_type import LkItemType  # noqa: F401
from .lk_enrollment_status import LkEnrollmentStatus  # noqa: F401
from .lk_progress_status import LkProgressStatus  # noqa: F401
from .lk_question_type import LkQuestionType  # noqa: F401

# Core domain models
from .users import User  # noqa: F401
from .trails import Trails  # noqa: F401
from .trail_sections import TrailSections  # noqa: F401
from .trail_items import TrailItems  # noqa: F401
from .trail_included_items import TrailIncludedItems  # noqa: F401
from .trail_requirements import TrailRequirements  # noqa: F401
from .trail_target_audience import TrailTargetAudience  # noqa: F401
from .trail_certificates import TrailCertificates  # noqa: F401
from .forums import Forum, ForumTopic, ForumPost  # noqa: F401

# Progress / enrollment models
from .user_trails import UserTrails  # noqa: F401
from .user_item_progress import UserItemProgress  # noqa: F401

# Forms & assessments
from .forms import Form  # noqa: F401
from .form_questions import FormQuestion  # noqa: F401
from .form_question_options import FormQuestionOption  # noqa: F401
from .form_submissions import FormSubmission  # noqa: F401
from .form_answers import FormAnswer  # noqa: F401
