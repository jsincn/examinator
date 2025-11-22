import unicodedata

def strip_non_ascii(text):
    """Remove or replace non-ASCII characters with ASCII equivalents."""
    if not text:
        return text
    
    # First try to normalize to ASCII equivalents
    normalized = unicodedata.normalize('NFKD', text)
    # Encode to ASCII, replacing non-ASCII with closest equivalent or removing
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return ascii_text
