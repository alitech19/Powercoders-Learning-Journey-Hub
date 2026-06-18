from django import forms

from accounts.models import User
from config.input_limits import TITLE_MAX_LENGTH

from .models import ProjectSpace, ProjectSpaceMembership

_INPUT_CLASS = (
    'w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-[#B23149] focus:border-[#B23149]'
)


class ProjectSpaceForm(forms.ModelForm):
    class Meta:
        model = ProjectSpace
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': _INPUT_CLASS,
                'placeholder': 'Project title',
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': _INPUT_CLASS,
                'placeholder': 'Optional description',
            }),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise forms.ValidationError('Title is required.')
        if len(title) > TITLE_MAX_LENGTH:
            raise forms.ValidationError('Title is too long.')
        return title


class ProjectMemberAddForm(forms.Form):
    user_id = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label='User',
        widget=forms.Select(attrs={'class': _INPUT_CLASS}),
    )

    def __init__(self, *args, project_space=None, **kwargs):
        self.project_space = project_space
        super().__init__(*args, **kwargs)
        member_ids = set()
        if project_space is not None:
            member_ids = set(project_space.memberships.values_list('user_id', flat=True))
        self.fields['user_id'].queryset = (
            User.objects.filter(is_active=True, role__in=[User.Role.STUDENT, User.Role.TEACHER])
            .exclude(pk__in=member_ids)
            .order_by('display_name', 'email')
        )

    def clean_user_id(self):
        user = self.cleaned_data['user_id']
        if self.project_space and self.project_space.memberships.filter(user=user).exists():
            raise forms.ValidationError('This user is already a member.')
        return user

    @property
    def membership_role(self):
        user = self.cleaned_data.get('user_id')
        if user is None:
            return ProjectSpaceMembership.Role.MEMBER
        if user.role == User.Role.TEACHER:
            return ProjectSpaceMembership.Role.MODERATOR
        return ProjectSpaceMembership.Role.MEMBER
