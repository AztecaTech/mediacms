from django.core.management.base import BaseCommand

from learning.methods.lesson_metrics_sync import AnalyticsEventLessonBackfillManager, LessonMetricsSyncManager
from learning.methods.student_risk_sync import StudentRiskScoreSyncManager


class Command(BaseCommand):
    help = (
        "Backfill LMS analytics: optional AnalyticsEvent.lesson FK from metadata, "
        "recompute LessonMetrics from progress, optional StudentRiskScore sync."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--backfill-event-lessons",
            action="store_true",
            help="Set AnalyticsEvent.lesson_id from metadata.lesson_id where missing.",
        )
        parser.add_argument("--event-batch", type=int, default=5000, help="Max analytics rows to scan for backfill.")
        parser.add_argument("--course-id", type=int, default=None, help="Limit LessonMetrics sync to one course.")
        parser.add_argument("--limit-lessons", type=int, default=None, help="Max lessons to sync (testing).")
        parser.add_argument(
            "--risk",
            action="store_true",
            help="Run StudentRiskScoreSyncManager after lesson metrics (heavier).",
        )
        parser.add_argument("--risk-limit", type=int, default=None, help="Max enrollments for risk sync.")

    def handle(self, *args, **options):
        if options["backfill_event_lessons"]:
            n = AnalyticsEventLessonBackfillManager.backfill_lesson_fk(batch=options["event_batch"])
            self.stdout.write(self.style.SUCCESS(f"Backfilled lesson FK on {n} analytics events."))

        n_lessons = LessonMetricsSyncManager.sync_all(
            course_id=options["course_id"],
            limit=options["limit_lessons"],
        )
        self.stdout.write(self.style.SUCCESS(f"Synced LessonMetrics for {n_lessons} lessons."))

        if options["risk"]:
            n_risk = StudentRiskScoreSyncManager.sync_all(limit=options["risk_limit"])
            self.stdout.write(self.style.SUCCESS(f"Synced {n_risk} student risk scores."))
