from django.urls import path

from learning.views.assessment_views import (
    AssignmentDetailView,
    AssignmentSubmitView,
    GradeSubmissionView,
    GradingQueueView,
    QuizAttemptDetailView,
    QuizAttemptSubmitView,
    QuizStartView,
)
from learning.views.lms_gradebook_analytics_views import (
    CertificateRevokeView,
    CourseCertificatesListView,
    CourseCertificateIssueView,
    CourseCertificateHealthView,
    CertificateVerifyView,
    CourseAnalyticsSummaryView,
    CourseGradebookExportView,
    CourseGradebookRecalculateView,
    CourseGradebookView,
    CourseMyGradesView,
    OrgAnalyticsSummaryView,
)
from learning.views.org_at_risk_views import OrgAtRiskEnrollmentsView, OrgInterventionNoteView
from learning.views.directory_views import LdapDirectorySourceListView, LdapDirectorySourceSyncView
from learning.views.letter_grade_views import CourseLetterGradeSchemeView
from learning.views.lti_launch_views import (
    LtiLaunchFormPostView,
    LtiOidcLoginInitiationView,
    LtiOidcLoginResumeView,
)
from learning.views.phase_stubs import LtiJwksView
from learning.views.paths_views import (
    CourseAuthoringView,
    LearningPathDetailView,
    LearningPathListCreateView,
    LessonDraftListCreateView,
)
from learning.views.question_bank_views import (
    QuestionBankDetailView,
    QuestionBankListCreateView,
    QuestionBankQuestionCreateView,
)
from learning.views.roster_export_views import CourseRosterCsvExportView
from learning.views.roster_import_views import CourseRosterCsvImportView
from learning.views import (
    CohortDetailView,
    CohortListCreateView,
    CourseDetailView,
    CourseListCreateView,
    CourseModulesListCreateView,
    CourseRosterView,
    EnrollView,
    LessonDetailView,
    LessonProgressPostView,
    ModuleDetailView,
    ModuleLessonsListCreateView,
    MyEnrollmentsListView,
    WithdrawView,
)
from learning.views.communication_views import (
    CourseAnnouncementsListView,
    CourseDiscussionsListView,
    DiscussionNotificationPreferencesView,
    DiscussionDetailView,
    DiscussionPostsListCreateView,
    NotificationDetailView,
    NotificationsListView,
)
from learning.views.gradebook_rubrics_views import (
    CourseGradeItemRubricView,
    SubmissionRubricScoresView,
)
from learning.views.credentials_views import MyBadgesView, MyCertificatesView, MyTranscriptView
from learning.views.gradebook_matrix_views import (
    CourseGradebookCellsBulkUpsertView,
    CourseGradebookCellUpsertView,
)
from learning.views.course_member_search_views import CourseMemberSearchView
from learning.views.calendar_views import CourseCalendarView, MyCalendarView
from learning.views.lms_analytics_product_views import (
    CourseAnalyticsAtRiskStudentsView,
    CourseAnalyticsDropOffView,
    CourseAnalyticsEngagementHeatmapView,
    CourseAnalyticsFunnelView,
    CourseAnalyticsTimeInContentView,
    OrgAnalyticsExportCsvView,
    OrgCompletionTrendView,
    OrgEnrollmentTrendView,
)

urlpatterns = [
    path("courses/", CourseListCreateView.as_view()),
    path("courses/<slug:slug>/", CourseDetailView.as_view()),
    path("courses/<slug:slug>/enroll/", EnrollView.as_view()),
    path("courses/<slug:slug>/withdraw/", WithdrawView.as_view()),
    path("courses/<slug:slug>/roster/", CourseRosterView.as_view()),
    path("courses/<slug:slug>/roster/export.csv", CourseRosterCsvExportView.as_view()),
    path("courses/<slug:slug>/roster/import/", CourseRosterCsvImportView.as_view()),
    path("courses/<slug:slug>/modules/", CourseModulesListCreateView.as_view()),
    path("modules/<int:pk>/", ModuleDetailView.as_view()),
    path("modules/<int:pk>/lessons/", ModuleLessonsListCreateView.as_view()),
    path("lessons/<int:pk>/", LessonDetailView.as_view()),
    path("lessons/<int:pk>/progress/", LessonProgressPostView.as_view()),
    path("enrollments/", MyEnrollmentsListView.as_view()),
    path("cohorts/", CohortListCreateView.as_view()),
    path("cohorts/<int:pk>/", CohortDetailView.as_view()),
    path("learning-paths/", LearningPathListCreateView.as_view()),
    path("learning-paths/<slug:slug>/", LearningPathDetailView.as_view()),
    path("question-banks/", QuestionBankListCreateView.as_view()),
    path("question-banks/<int:pk>/", QuestionBankDetailView.as_view()),
    path("question-banks/<int:pk>/questions/", QuestionBankQuestionCreateView.as_view()),
    path("courses/<slug:slug>/authoring/", CourseAuthoringView.as_view()),
    path("courses/<slug:slug>/discussions/", CourseDiscussionsListView.as_view()),
    path("courses/<slug:slug>/announcements/", CourseAnnouncementsListView.as_view()),
    path("courses/<slug:slug>/members/search/", CourseMemberSearchView.as_view()),
    path("courses/<slug:slug>/calendar/", CourseCalendarView.as_view()),
    path("my/calendar/", MyCalendarView.as_view()),
    path("discussions/<int:pk>/", DiscussionDetailView.as_view()),
    path("discussions/<int:pk>/posts/", DiscussionPostsListCreateView.as_view()),
    path("notifications/", NotificationsListView.as_view()),
    path("notifications/<int:pk>/", NotificationDetailView.as_view()),
    path("notifications/discussion-preferences/", DiscussionNotificationPreferencesView.as_view()),
    path("lessons/<int:pk>/drafts/", LessonDraftListCreateView.as_view()),
    path("courses/<slug:slug>/gradebook/export.csv", CourseGradebookExportView.as_view()),
    path("courses/<slug:slug>/gradebook/recalculate/", CourseGradebookRecalculateView.as_view()),
    path("courses/<slug:slug>/gradebook/cells/bulk/", CourseGradebookCellsBulkUpsertView.as_view()),
    path("courses/<slug:slug>/gradebook/cells/", CourseGradebookCellUpsertView.as_view()),
    path("courses/<slug:slug>/gradebook/letter-scheme/", CourseLetterGradeSchemeView.as_view()),
    path("courses/<slug:slug>/gradebook/items/<int:item_id>/rubric/", CourseGradeItemRubricView.as_view()),
    path("courses/<slug:slug>/gradebook/", CourseGradebookView.as_view()),
    path("courses/<slug:slug>/my-grades/", CourseMyGradesView.as_view()),
    path("submissions/", GradingQueueView.as_view()),
    path("submissions/<int:pk>/grade/", GradeSubmissionView.as_view()),
    path("submissions/<int:pk>/rubric-scores/", SubmissionRubricScoresView.as_view()),
    path("quizzes/<int:pk>/start/", QuizStartView.as_view()),
    path("quiz-attempts/<int:pk>/", QuizAttemptDetailView.as_view()),
    path("quiz-attempts/<int:pk>/submit/", QuizAttemptSubmitView.as_view()),
    path("assignments/<int:pk>/submit/", AssignmentSubmitView.as_view()),
    path("assignments/<int:pk>/", AssignmentDetailView.as_view()),
    path("courses/<slug:slug>/analytics/summary/", CourseAnalyticsSummaryView.as_view()),
    path("courses/<slug:slug>/analytics/funnel/", CourseAnalyticsFunnelView.as_view()),
    path("courses/<slug:slug>/analytics/engagement-heatmap/", CourseAnalyticsEngagementHeatmapView.as_view()),
    path("courses/<slug:slug>/analytics/drop-off/", CourseAnalyticsDropOffView.as_view()),
    path("courses/<slug:slug>/analytics/time-in-content/", CourseAnalyticsTimeInContentView.as_view()),
    path("courses/<slug:slug>/analytics/at-risk-students/", CourseAnalyticsAtRiskStudentsView.as_view()),
    path("courses/<slug:slug>/certificates/", CourseCertificatesListView.as_view()),
    path("courses/<slug:slug>/certificates/issue/", CourseCertificateIssueView.as_view()),
    path("courses/<slug:slug>/certificates/health/", CourseCertificateHealthView.as_view()),
    path("certificates/<int:pk>/revoke/", CertificateRevokeView.as_view()),
    path("admin/analytics/org-summary/", OrgAnalyticsSummaryView.as_view()),
    path("admin/analytics/enrollment-trend/", OrgEnrollmentTrendView.as_view()),
    path("admin/analytics/completion-trend/", OrgCompletionTrendView.as_view()),
    path("admin/analytics/export.csv", OrgAnalyticsExportCsvView.as_view()),
    path("admin/analytics/at-risk-enrollments/", OrgAtRiskEnrollmentsView.as_view()),
    path("admin/analytics/intervention-notes/", OrgInterventionNoteView.as_view()),
    path("admin/directory/ldap-sources/", LdapDirectorySourceListView.as_view()),
    path("admin/directory/ldap-sources/<int:pk>/sync/", LdapDirectorySourceSyncView.as_view()),
    path("lti/jwks/", LtiJwksView.as_view()),
    path("lti/login/", LtiOidcLoginInitiationView.as_view()),
    path("lti/login-resume/", LtiOidcLoginResumeView.as_view()),
    path("lti/launch/", LtiLaunchFormPostView.as_view()),
    path("verify/<str:code>/", CertificateVerifyView.as_view()),
    path("my/certificates/", MyCertificatesView.as_view()),
    path("my/badges/", MyBadgesView.as_view()),
    path("my/transcript/", MyTranscriptView.as_view()),
]
