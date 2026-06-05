from django import forms

from config.input_limits import (
    DESCRIPTION_MAX_LENGTH,
    STEP_DESCRIPTION_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)

from .models import Workflow, WorkflowStep


class WorkflowStepForm(forms.ModelForm):
    class Meta:
        model = WorkflowStep
        fields = ['title', 'description', 'requires_previous']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs['maxlength'] = TITLE_MAX_LENGTH
        self.fields['description'].widget.attrs['maxlength'] = STEP_DESCRIPTION_MAX_LENGTH


class WorkflowMetadataForm(forms.ModelForm):
    class Meta:
        model = Workflow
        fields = ['title', 'description', 'visibility']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].max_length = TITLE_MAX_LENGTH
        self.fields['title'].widget.attrs['maxlength'] = TITLE_MAX_LENGTH
        self.fields['description'].widget.attrs['maxlength'] = DESCRIPTION_MAX_LENGTH
