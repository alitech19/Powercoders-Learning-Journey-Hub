from django import forms

from .models import Workflow, WorkflowStep


class WorkflowStepForm(forms.ModelForm):
    class Meta:
        model = WorkflowStep
        fields = ['title', 'description', 'order', 'requires_previous']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }


class WorkflowMetadataForm(forms.ModelForm):
    class Meta:
        model = Workflow
        fields = ['title', 'description', 'visibility']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
