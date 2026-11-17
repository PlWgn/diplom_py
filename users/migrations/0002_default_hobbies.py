from django.db import migrations

HOBBIES = [
    'Музыка',
    'Кино',
    'Путешествия',
    'Спорт',
    'Книги',
    'Кулинария',
    'Фотография',
    'Игры',
    'Танцы',
    'Искусство',
    'Природа',
    'Животные',
    'Технологии',
    'Йога',
    'Театр',
    'Автомобили',
]


def add_hobbies(apps, schema_editor):
    Hobby = apps.get_model('users', 'Hobby')
    Hobby.objects.bulk_create(
        [Hobby(name=name) for name in HOBBIES], ignore_conflicts=True
    )


def remove_hobbies(apps, schema_editor):
    Hobby = apps.get_model('users', 'Hobby')
    Hobby.objects.filter(name__in=HOBBIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_hobbies, remove_hobbies),
    ]
