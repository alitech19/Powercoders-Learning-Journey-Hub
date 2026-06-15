"""Google Drive file permissions helpers."""


def set_anyone_reader(service, file_id: str, *, supports_all_drives: bool = False) -> None:
    kwargs = {
        'fileId': file_id,
        'body': {
            'type': 'anyone',
            'role': 'reader',
            'allowFileDiscovery': False,
        },
    }
    if supports_all_drives:
        kwargs['supportsAllDrives'] = True
    service.permissions().create(**kwargs).execute()


def delete_drive_file(service, file_id: str, *, supports_all_drives: bool = False) -> None:
    kwargs = {'fileId': file_id}
    if supports_all_drives:
        kwargs['supportsAllDrives'] = True
    service.files().delete(**kwargs).execute()
