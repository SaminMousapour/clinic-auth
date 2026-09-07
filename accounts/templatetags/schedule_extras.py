from django import template
from datetime import date

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key (supports variable keys)"""
    if dictionary is None:
        return []
    return dictionary.get(key, [])

@register.filter
def get_category_color(category):
    """Return color for category"""
    colors = {
        'class': '#8b5cf6',
        'work': '#10b981',
        'appointment': '#ef4444',
        'personal': '#f59e0b',
        'exercise': '#06b6d4',
        'other': '#6b7280',
    }
    return colors.get(category, '#6b7280')

@register.filter
def get_today_items(schedule_items):
    """Filter schedule items for today's day of week"""
    if not schedule_items:
        return []
    today = date.today()
    weekday_map = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday', 5: 'saturday', 6: 'sunday'}
    today_name = weekday_map[today.weekday()]
    return [item for item in schedule_items if item.day_of_week == today_name and item.is_active]