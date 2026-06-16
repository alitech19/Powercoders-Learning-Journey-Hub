import base64
import imghdr

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


def encode_upload(uploaded_file):
    """Validate image upload (max 2 MB) and return base64 text + content type."""
    content = uploaded_file.read()
    if not content:
        raise AvatarUploadError('The uploaded file is empty.')
    if len(content) > MAX_AVATAR_BYTES:
        raise AvatarUploadError('Profile photo must be 2 MB or smaller.')

    image_format = imghdr.what(None, h=content)
    if image_format is None:
        raise AvatarUploadError('Upload a JPG, PNG, GIF, or WebP image.')

    content_type = _CONTENT_TYPE_BY_FORMAT.get(image_format)
    if content_type is None:
        raise AvatarUploadError('Upload a JPG, PNG, GIF, or WebP image.')

    return base64.b64encode(content).decode('ascii'), content_type


def decode_avatar_data(avatar_data):
    return base64.b64decode(avatar_data)
