from django.test import TestCase

from google_storage.folder_paths import group_drive_path
from test_utils.cohorts import make_cohort, make_group


class FolderPathTests(TestCase):
    def test_group_drive_path(self):
        cohort = make_cohort('Bern 2026')
        group = make_group(cohort, 'Team Alpha')
        path = group_drive_path(group)
        self.assertTrue(path.startswith('PowerHUB/Groups/'))
        self.assertIn('bern-2026', path)
        self.assertIn('team-alpha', path)
