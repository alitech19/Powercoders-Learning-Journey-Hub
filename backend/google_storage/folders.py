"""Ensure PowerHUB folder hierarchy in Shared drive or student My Drive."""

from __future__ import annotations

from django.db import transaction

from .config import get_workspace_storage_config
from .constants import GROUPS_FOLDER_NAME, ROOT_FOLDER_NAME
from .drive.service_account import (
    build_service_account_drive_service,
    create_folder,
    find_child_folder,
)
from .folder_paths import group_drive_path, root_drive_path
from .models import GoogleDriveFolder, GoogleWorkspaceStorageConfig


class SharedDriveFolderService:
    """Org Shared drive folders — provisioned via service account."""

    def __init__(self, config: GoogleWorkspaceStorageConfig | None = None):
        self.config = config or get_workspace_storage_config()

    def _service(self):
        return build_service_account_drive_service(self.config.get_service_account_json())

    def ensure_root_folder(self) -> GoogleDriveFolder:
        if not self.config.staff_uploads_enabled():
            raise ValueError('Staff Shared drive uploads are not enabled or configured.')

        existing = GoogleDriveFolder.objects.filter(
            storage_backend=GoogleDriveFolder.StorageBackend.SHARED_ORG,
            folder_kind=GoogleDriveFolder.FolderKind.ROOT,
            group__isnull=True,
        ).first()
        if existing:
            return existing

        service = self._service()
        drive_id = self.config.shared_drive_id
        root_name = self.config.root_folder_name or ROOT_FOLDER_NAME

        if self.config.shared_root_folder_id:
            folder_id = self.config.shared_root_folder_id
        else:
            folder_id = find_child_folder(
                service,
                parent_id=drive_id,
                name=root_name,
                drive_id=drive_id,
            )
            if not folder_id:
                folder_id = create_folder(
                    service,
                    name=root_name,
                    parent_id=drive_id,
                    drive_id=drive_id,
                )
            self.config.shared_root_folder_id = folder_id
            self.config.save(update_fields=['shared_root_folder_id', 'updated_at'])

        with transaction.atomic():
            mapping, _created = GoogleDriveFolder.objects.get_or_create(
                storage_backend=GoogleDriveFolder.StorageBackend.SHARED_ORG,
                folder_kind=GoogleDriveFolder.FolderKind.ROOT,
                group=None,
                defaults={
                    'drive_folder_id': folder_id,
                    'drive_path': root_drive_path(),
                },
            )
        return mapping

    def ensure_group_folder(self, group) -> GoogleDriveFolder:
        root = self.ensure_root_folder()
        existing = GoogleDriveFolder.objects.filter(
            storage_backend=GoogleDriveFolder.StorageBackend.SHARED_ORG,
            folder_kind=GoogleDriveFolder.FolderKind.GROUP,
            group=group,
        ).first()
        if existing:
            return existing

        service = self._service()
        drive_id = self.config.shared_drive_id

        groups_parent = find_child_folder(
            service,
            parent_id=root.drive_folder_id,
            name=GROUPS_FOLDER_NAME,
            drive_id=drive_id,
        )
        if not groups_parent:
            groups_parent = create_folder(
                service,
                name=GROUPS_FOLDER_NAME,
                parent_id=root.drive_folder_id,
                drive_id=drive_id,
            )

        segment = group_drive_path(group).split('/')[-1]
        group_folder_id = find_child_folder(
            service,
            parent_id=groups_parent,
            name=segment,
            drive_id=drive_id,
        )
        if not group_folder_id:
            group_folder_id = create_folder(
                service,
                name=segment,
                parent_id=groups_parent,
                drive_id=drive_id,
            )

        path = group_drive_path(group)
        mapping, _created = GoogleDriveFolder.objects.get_or_create(
            storage_backend=GoogleDriveFolder.StorageBackend.SHARED_ORG,
            folder_kind=GoogleDriveFolder.FolderKind.GROUP,
            group=group,
            defaults={
                'drive_folder_id': group_folder_id,
                'drive_path': path,
            },
        )
        return mapping


class PersonalDriveFolderService:
    """Student My Drive folders — requires OAuth connection."""

    def __init__(self, connection):
        self.connection = connection
        self.config = get_workspace_storage_config()

    def _service(self):
        from .drive.oauth_client import build_user_drive_service

        return build_user_drive_service(self.connection, self.config)

    def ensure_root_folder(self) -> GoogleDriveFolder:
        existing = GoogleDriveFolder.objects.filter(
            storage_backend=GoogleDriveFolder.StorageBackend.PERSONAL,
            folder_kind=GoogleDriveFolder.FolderKind.ROOT,
            user=self.connection.user,
            group__isnull=True,
        ).first()
        if existing:
            return existing

        service = self._service()
        root_name = self.config.root_folder_name or ROOT_FOLDER_NAME
        folder_id = self.connection.root_folder_id
        if folder_id:
            pass
        else:
            folder_id = find_child_folder(service, parent_id='root', name=root_name)
            if not folder_id:
                folder_id = create_folder(service, name=root_name, parent_id='root')
            self.connection.root_folder_id = folder_id
            self.connection.save(update_fields=['root_folder_id'])

        mapping, _created = GoogleDriveFolder.objects.get_or_create(
            storage_backend=GoogleDriveFolder.StorageBackend.PERSONAL,
            folder_kind=GoogleDriveFolder.FolderKind.ROOT,
            user=self.connection.user,
            group=None,
            defaults={
                'drive_folder_id': folder_id,
                'drive_path': root_drive_path(),
            },
        )
        return mapping

    def ensure_group_folder(self, group) -> GoogleDriveFolder:
        root = self.ensure_root_folder()
        existing = GoogleDriveFolder.objects.filter(
            storage_backend=GoogleDriveFolder.StorageBackend.PERSONAL,
            folder_kind=GoogleDriveFolder.FolderKind.GROUP,
            user=self.connection.user,
            group=group,
        ).first()
        if existing:
            return existing

        service = self._service()
        groups_parent = find_child_folder(
            service,
            parent_id=root.drive_folder_id,
            name=GROUPS_FOLDER_NAME,
        )
        if not groups_parent:
            groups_parent = create_folder(
                service,
                name=GROUPS_FOLDER_NAME,
                parent_id=root.drive_folder_id,
            )

        segment = group_drive_path(group).split('/')[-1]
        group_folder_id = find_child_folder(
            service,
            parent_id=groups_parent,
            name=segment,
        )
        if not group_folder_id:
            group_folder_id = create_folder(
                service,
                name=segment,
                parent_id=groups_parent,
            )

        mapping, _created = GoogleDriveFolder.objects.get_or_create(
            storage_backend=GoogleDriveFolder.StorageBackend.PERSONAL,
            folder_kind=GoogleDriveFolder.FolderKind.GROUP,
            user=self.connection.user,
            group=group,
            defaults={
                'drive_folder_id': group_folder_id,
                'drive_path': group_drive_path(group),
            },
        )
        return mapping
