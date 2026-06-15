from django import forms

from .models import BugReport


class BugReportCreateForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = ('description',)
        widgets = {
            'description': forms.Textarea(
                attrs={
                    'rows': 5,
                    'class': (
                        'w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 '
                        'text-sm resize-y focus:outline-none focus:ring-2 focus:ring-[#B23149] '
                        'focus:border-[#B23149]'
                    ),
                    'placeholder': 'What went wrong? Steps to reproduce help us fix it faster.',
                }
            ),
        }


class BugReportReplyForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 3,
                'class': (
                    'w-full px-3 py-2 rounded-xl border border-gray-300 dark:border-gray-600 '
                    'text-sm resize-y focus:outline-none focus:ring-2 focus:ring-[#B23149] '
                    'focus:border-[#B23149]'
                ),
                'placeholder': 'Reply to the reporter…',
            }
        )
    )
