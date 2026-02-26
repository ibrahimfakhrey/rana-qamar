TRANSLATIONS = {
    'medication_reminder': {
        'ar': 'تذكير بالدواء',
        'en': 'Medication Reminder',
    },
    'medication_body': {
        'ar': 'حان وقت تناول {name} - {dosage}',
        'en': 'Time to take {name} - {dosage}',
    },
    'meal_reminder': {
        'ar': 'تذكير بالوجبة',
        'en': 'Meal Reminder',
    },
    'meal_body': {
        'ar': 'حان وقت {meal_type}: {description}',
        'en': 'Time for {meal_type}: {description}',
    },
    'water_reminder': {
        'ar': 'تذكير بشرب الماء',
        'en': 'Water Reminder',
    },
    'water_body': {
        'ar': 'لا تنسَ شرب كوب من الماء!',
        'en': "Don't forget to drink a glass of water!",
    },
    'activity_reminder': {
        'ar': 'تذكير بالنشاط',
        'en': 'Activity Reminder',
    },
    'activity_body': {
        'ar': 'حان وقت {name}',
        'en': 'Time for {name}',
    },
    'task_confirmed': {
        'ar': 'تم تأكيد المهمة',
        'en': 'Task Confirmed',
    },
    'meal_types': {
        'breakfast': {'ar': 'الإفطار', 'en': 'Breakfast'},
        'lunch': {'ar': 'الغداء', 'en': 'Lunch'},
        'dinner': {'ar': 'العشاء', 'en': 'Dinner'},
        'snack': {'ar': 'وجبة خفيفة', 'en': 'Snack'},
    },
}


def t(key, lang='ar', **kwargs):
    """Get translated string with optional format kwargs."""
    text = TRANSLATIONS.get(key, {}).get(lang, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_meal_type_name(meal_type, lang='ar'):
    """Get translated meal type name."""
    return TRANSLATIONS.get('meal_types', {}).get(meal_type, {}).get(lang, meal_type)
