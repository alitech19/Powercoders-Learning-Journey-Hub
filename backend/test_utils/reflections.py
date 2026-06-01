from reflections.constants import TAG_WEEKLY
from reflections.models import Reflection


def make_reflection(
    author,
    *,
    title='Weekly reflection',
    visibility=Reflection.Visibility.PRIVATE,
    tags=None,
    expectations='',
    final_reflection='',
    **kwargs,
):
    return Reflection.objects.create(
        author=author,
        title=title,
        visibility=visibility,
        tags=tags if tags is not None else [TAG_WEEKLY],
        expectations=expectations,
        final_reflection=final_reflection,
        **kwargs,
    )
