import re
import uuid
import string
import random
from typing import Optional
from django.http import HttpRequest


def get_client_ip(request: HttpRequest) -> str:
    """
    Get the client's IP address from the request.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def format_phone_number(phone: str) -> str:
    """
    Format phone number to a consistent format.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        str: Formatted phone number
    """
    # Remove all non-digits
    digits = re.sub(r'\D', '', phone)
    
    # Format as (XXX) XXX-XXXX for 10-digit US numbers
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone  # Return original if can't format


def generate_unique_code(length: int = 8, include_numbers: bool = True, 
                        include_uppercase: bool = True, include_lowercase: bool = True) -> str:
    """
    Generate a unique code with specified characteristics.
    
    Args:
        length: Length of the code
        include_numbers: Include numbers in the code
        include_uppercase: Include uppercase letters
        include_lowercase: Include lowercase letters
        
    Returns:
        str: Generated unique code
    """
    characters = ''
    
    if include_lowercase:
        characters += string.ascii_lowercase
    if include_uppercase:
        characters += string.ascii_uppercase
    if include_numbers:
        characters += string.digits
    
    if not characters:
        characters = string.ascii_letters + string.digits
    
    return ''.join(random.choice(characters) for _ in range(length))


def slugify_filename(filename: str) -> str:
    """
    Create a URL-safe filename.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Slugified filename
    """
    # Keep the file extension
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    
    # Remove special characters and replace spaces with underscores
    name = re.sub(r'[^\w\s-]', '', name.strip().lower())
    name = re.sub(r'[-\s]+', '_', name)
    
    # Add timestamp to ensure uniqueness
    import time
    timestamp = int(time.time())
    
    if ext:
        return f"{name}_{timestamp}.{ext}"
    else:
        return f"{name}_{timestamp}"


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    
    Args:
        email: Email address to mask
        
    Returns:
        str: Masked email address
    """
    if '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"


def parse_user_agent(user_agent: str) -> dict:
    """
    Parse user agent string to extract browser and OS information.
    
    Args:
        user_agent: User agent string
        
    Returns:
        dict: Parsed user agent information
    """
    # Basic user agent parsing (for production, consider using a library like user-agents)
    info = {
        'browser': 'Unknown',
        'os': 'Unknown',
        'device': 'Desktop'
    }
    
    user_agent = user_agent.lower()
    
    # Browser detection
    if 'chrome' in user_agent:
        info['browser'] = 'Chrome'
    elif 'firefox' in user_agent:
        info['browser'] = 'Firefox'
    elif 'safari' in user_agent and 'chrome' not in user_agent:
        info['browser'] = 'Safari'
    elif 'edge' in user_agent:
        info['browser'] = 'Edge'
    
    # OS detection
    if 'windows' in user_agent:
        info['os'] = 'Windows'
    elif 'mac' in user_agent:
        info['os'] = 'macOS'
    elif 'linux' in user_agent:
        info['os'] = 'Linux'
    elif 'android' in user_agent:
        info['os'] = 'Android'
        info['device'] = 'Mobile'
    elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
        info['os'] = 'iOS'
        info['device'] = 'Mobile' if 'iphone' in user_agent else 'Tablet'
    
    return info