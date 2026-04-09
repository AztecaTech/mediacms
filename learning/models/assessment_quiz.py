from django.conf import settings
from django.db import models


class ShowCorrectAfter(models.TextChoices):
    NEVER = "never", "Never"
    AFTER_ATTEMPT = "after_attempt", "After attempt"
    AFTER_PASSING = "after_passing", "After passing"
    AFTER_DUE_DATE = "after_due_date", "After due date"


class QuestionType(models.TextChoices):
    MC_SINGLE = "mc_single", "Multiple choice (single)"
    MC_MULTI = "mc_multi", "Multiple choice (multi)"
    TRUE_FALSE = "true_false", "True / false"
    SHORT_ANSWER = "short_answer", "Short answer"
    MATCHING = "matching", "Matching"
    FILL_BLANK = "fill_blank", "Fill in the blank"


class QuizAttemptStatus(models.TextChoices):
    IN_PROGRESS = "in_progress", "In progress"
    SUBMITTED = "submitted", "Submitted"
    GRADED = "graded", "Graded"
    EXPIRED = "expired", "Expired"


class QuestionBank(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="question_banks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Quiz(models.Model):
    lesson = models.OneToOneField(
        "learning.Lesson",
        on_delete=models.CASCADE,
        related_name="quiz_spec",
    )
    instructions = models.TextField(blank=True)
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)
    passing_score_pct = models.PositiveIntegerField(default=70)
    randomize_questions = models.BooleanField(default=False)
    randomize_choices = models.BooleanField(default=False)
    show_correct_after = models.CharField(
        max_length=20,
        choices=ShowCorrectAfter.choices,
        default=ShowCorrectAfter.NEVER,
    )
    due_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Quiz:{self.lesson_id}"


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questions",
    )
    bank = models.ForeignKey(
        QuestionBank,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questions",
    )
    order = models.PositiveIntegerField(default=0)
    prompt = models.TextField()
    type = models.CharField(max_length=20, choices=QuestionType.choices)
    points = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    explanation = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(quiz__isnull=False) | models.Q(bank__isnull=False),
                name="learning_question_quiz_or_bank",
            ),
            models.UniqueConstraint(
                fields=["quiz", "order"],
                condition=models.Q(quiz__isnull=False),
                name="learning_question_unique_quiz_order",
            ),
            models.UniqueConstraint(
                fields=["bank", "order"],
                condition=models.Q(bank__isnull=False),
                name="learning_question_unique_bank_order",
            ),
        ]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=2000)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class QuizAttempt(models.Model):
    enrollment = models.ForeignKey(
        "learning.Enrollment",
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    score_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=QuizAttemptStatus.choices,
        default=QuizAttemptStatus.IN_PROGRESS,
    )
    attempt_number = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "quiz", "attempt_number"],
                name="learning_quizattempt_unique_enrollment_quiz_attemptnum",
            ),
        ]


class Answer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="student_answers")
    selected_choices = models.ManyToManyField(Choice, blank=True, related_name="answer_selections")
    text_answer = models.TextField(blank=True)
    matching_answer = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    auto_graded = models.BooleanField(default=False)
    grader_feedback = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="learning_answer_unique_attempt_question",
            ),
        ]
