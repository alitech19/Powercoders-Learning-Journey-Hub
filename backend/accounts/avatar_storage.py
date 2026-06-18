import base64

MAX_AVATAR_BYTES = 2 * 1024 * 1024
AVATAR_CACHE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days; ?v= on URL busts cache on change

_CONTENT_TYPE_BY_FORMAT = {
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'webp': 'image/webp',
}


class AvatarUploadError(ValueError):
    pass


def _image_format_from_bytes(content):
    """Detect JPEG/PNG/GIF/WebP from file header (stdlib imghdr removed in Python 3.13)."""
    if content.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if content.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if len(content) >= 12 and content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        return 'webp'
    return None


def encode_upload(uploaded_file):
    """Validate image upload (max 2 MB) and return base64 text + content type."""
    content = uploaded_file.read()
    if not content:
        raise AvatarUploadError('The uploaded file is empty.')
    if len(content) > MAX_AVATAR_BYTES:
        raise AvatarUploadError('Profile photo must be 2 MB or smaller.')

    image_format = _image_format_from_bytes(content)
    if image_format is None:
        raise AvatarUploadError('Upload a JPG, PNG, GIF, or WebP image.')

    content_type = _CONTENT_TYPE_BY_FORMAT.get(image_format)
    if content_type is None:
        raise AvatarUploadError('Upload a JPG, PNG, GIF, or WebP image.')

    return base64.b64encode(content).decode('ascii'), content_type


def decode_avatar_data(avatar_data):
    return base64.b64decode(avatar_data)
