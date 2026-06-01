from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from group_space.constants import GROUP_FILE_MAX_BYTES
from group_space.services import (
    detect_urls,
    post_is_achievement_share,
    post_qualifies_for_resources,
    validate_uploaded_file,
)
from test_utils.cohorts import make_cohort, make_group
from test_utils.group_space import get_space_for_group, make_post
from test_utils.users import make_student


class GroupSpaceServicesTests(TestCase):
    def setUp(self):
        self.group = make_group(make_cohort())
        self.space = get_space_for_group(self.group)
        self.student = make_student('s@example.com', group=self.group)

    def test_detect_urls(self):
        urls = detect_urls('See https://example.com/a and http://test.org')
        self.assertEqual(len(urls), 2)

    def test_post_qualifies_for_resources(self):
        post = make_post(
            self.space,
            self.student,
            body='Link https://example.com',
            resource_label='Docs',
        )
        self.assertTrue(post_qualifies_for_resources(post))

    def test_snapshot_does_not_qualify(self):
        post = make_post(
            self.space,
            self.student,
            snapshot_html='<p>Done!</p>',
            resource_label='ignored',
        )
        self.assertTrue(post_is_achievement_share(post))
        self.assertFalse(post_qualifies_for_resources(post))

    def test_missing_label_does_not_qualify(self):
        post = make_post(
            self.space,
            self.student,
            body='https://example.com',
            resource_label='',
        )
        self.assertFalse(post_qualifies_for_resources(post))

    def test_validate_uploaded_file_rejects_bad_extension(self):
        bad = SimpleUploadedFile('virus.exe', b'x', content_type='application/octet-stream')
        with self.assertRaises(ValidationError):
            validate_uploaded_file(bad)

    def test_validate_uploaded_file_rejects_oversize(self):
        huge = SimpleUploadedFile(
            'big.pdf',
            b'x' * (GROUP_FILE_MAX_BYTES + 1),
            content_type='application/pdf',
        )
        with self.assertRaises(ValidationError):
            validate_uploaded_file(huge)
