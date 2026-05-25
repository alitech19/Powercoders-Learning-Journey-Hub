from django.urls import path
from django.views.generic import RedirectView

from .views import feedback, goals, habits, journal, reflections, teacher

app_name = 'growth'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='growth:journal_list', permanent=False), name='index'),

    # Daily Journal
    path('journal/', journal.journal_list, name='journal_list'),
    path('journal/new/', journal.journal_create, name='journal_create'),
    path('journal/<int:pk>/', journal.journal_detail, name='journal_detail'),
    path('journal/<int:pk>/edit/', journal.journal_edit, name='journal_edit'),

    # Habits
    path('habits/', habits.habit_list, name='habit_list'),
    path('habits/new/', habits.habit_create, name='habit_create'),
    path('habits/<int:pk>/edit/', habits.habit_edit, name='habit_edit'),
    path('habits/<int:pk>/delete/', habits.habit_delete, name='habit_delete'),
    path('habits/<int:pk>/mark-completed/', habits.habit_mark_completed, name='habit_mark_completed'),
    path('habits/<int:pk>/reactivate/', habits.habit_reactivate, name='habit_reactivate'),
    path('habits/<int:pk>/log-today/done/', habits.habit_log_done, name='habit_log_done'),
    path('habits/<int:pk>/log-today/not-done/', habits.habit_log_not_done, name='habit_log_not_done'),

    # Goals
    path('goals/', goals.goal_list, name='goal_list'),
    path('goals/new/', goals.goal_create, name='goal_create'),
    path('goals/<int:pk>/', goals.goal_detail, name='goal_detail'),
    path('goals/<int:pk>/edit/', goals.goal_edit, name='goal_edit'),
    path('goals/<int:pk>/delete/', goals.goal_delete, name='goal_delete'),
    path('goals/<int:pk>/mark-achieved/', goals.goal_mark_achieved, name='goal_mark_achieved'),

    # Reflections
    path('reflections/', reflections.reflection_list, name='reflection_list'),
    path('reflections/new/', reflections.reflection_create, name='reflection_create'),
    path('reflections/<int:pk>/', reflections.reflection_detail, name='reflection_detail'),
    path('reflections/<int:pk>/edit/', reflections.reflection_edit, name='reflection_edit'),

    # Feedback
    path('feedback/<str:content_type>/<int:object_id>/new/', feedback.feedback_create, name='feedback_create'),

    # Teacher / Admin growth dashboard
    path('teaching/', teacher.teacher_dashboard, name='teacher_dashboard'),
    path('teaching/students/<int:student_id>/', teacher.student_growth_detail, name='student_growth_detail'),
]
