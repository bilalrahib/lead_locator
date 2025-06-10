import re
from typing import Optional
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator


def validate_zip_code(value: str) -> str:
    """
    Validate US ZIP code format.
    
    Args:
        value: ZIP code string
        
    Returns:
        str: Validated ZIP code
        
    Raises:
        ValidationError: If ZIP code format is invalid
    """
    # Remove any spaces or hyphens
    cleaned = re.sub(r'[\s-]', '', value)
    
    # Check for 5-digit or 9-digit (ZIP+4) format
    if not re.match(r'^\d{5}(\d{4})?$', cleaned):
        raise ValidationError(
            'Invalid ZIP code format. Use 12345 or 123456789.',
            code='invalid_zip'
        )
    
    return cleaned


def validate_phone_number(value: str) -> str:
    """
    Validate US phone number format.
    
    Args:
        value: Phone number string
        
    Returns:
        str: Validated phone number
        
    Raises:
        ValidationError: If phone number format is invalid
    """
    # Remove all non-digits
    digits = re.sub(r'\D', '', value)
    
    # Check for valid US phone number (10 digits or 11 with country code)
    if len(digits) == 10:
        # Standard 10-digit number
        return digits
    elif len(digits) == 11 and digits[0] == '1':
        # 11-digit with US country code
        return digits[1:]  # Return just the 10-digit number
    else:
        raise ValidationError(
            'Invalid phone number format. Use (XXX) XXX-XXXX or XXX-XXX-XXXX.',
            code='invalid_phone'
        )


def validate_coordinates(latitude: float, longitude: float) -> tuple:
    """
    Validate latitude and longitude coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        
    Returns:
        tuple: Validated (latitude, longitude)
        
    Raises:
        ValidationError: If coordinates are invalid
    """
    if not (-90 <= latitude <= 90):
        raise ValidationError(
            'Latitude must be between -90 and 90 degrees.',
            code='invalid_latitude'
        )
    
    if not (-180 <= longitude <= 180):
        raise ValidationError(
            'Longitude must be between -180 and 180 degrees.',
            code='invalid_longitude'
        )
    
    return latitude, longitude


def validate_business_hours(hours_text: str) -> str:
    """
    Validate business hours format.
    
    Args:
        hours_text: Business hours text
        
    Returns:
        str: Validated hours text
        
    Raises:
        ValidationError: If format is invalid
    """
    if not hours_text or len(hours_text.strip()) < 5:
        raise ValidationError(
            'Business hours must be at least 5 characters.',
            code='invalid_hours'
        )
    
    # Basic validation - you could make this more sophisticated
    return hours_text.strip()


def validate_url(value: str) -> str:
    """
    Validate URL format.
    
    Args:
        value: URL string
        
    Returns:
        str: Validated URL
        
    Raises:
        ValidationError: If URL format is invalid
    """
    from django.core.validators import URLValidator
    
    url_validator = URLValidator()
    
    # Add protocol if missing
    if not value.startswith(('http://', 'https://')):
        value = 'https://' + value
    
    try:
        url_validator(value)
        return value
    except ValidationError:
        raise ValidationError(
            'Enter a valid URL.',
            code='invalid_url'
        )


def validate_file_size(file, max_size_mb: int = 5):
    """
    Validate uploaded file size.
    
    Args:
        file: Uploaded file object
        max_size_mb: Maximum size in MB
        
    Raises:
        ValidationError: If file is too large
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file.size > max_size_bytes:
        raise ValidationError(
            f'File size cannot exceed {max_size_mb}MB.',
            code='file_too_large'
        )


def validate_image_file(file):
    """
    Validate that uploaded file is an image.
    
    Args:
        file: Uploaded file object
        
    Raises:
        ValidationError: If file is not a valid image
    """
    from PIL import Image
    
    try:
        # Try to open as image
        image = Image.open(file)
        image.verify()
        
        # Reset file pointer
        file.seek(0)
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        file_ext = file.name.lower().split('.')[-1]
        
        if f'.{file_ext}' not in allowed_extensions:
            raise ValidationError(
                'Only image files are allowed (JPG, PNG, GIF, WebP).',
                code='invalid_image_type'
            )
            
    except Exception:
        raise ValidationError(
            'Invalid image file.',
            code='invalid_image'
        )