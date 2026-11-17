import os
import shutil
import tempfile
from datetime import date
from http import HTTPStatus
from io import BytesIO, StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image
from rest_framework.test import APITestCase

from interactions.models import Reaction

from .models import Hobby, Photo

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def make_user(email: str, **kwargs):
    data = {
        'first_name': 'Анна',
        'last_name': 'Петрова',
        'middle_name': 'Сергеевна',
        'gender': User.Gender.FEMALE,
        'birth_date': date(2000, 1, 1),
        'city': 'Москва',
    }
    data.update(kwargs)
    return User.objects.create_user(email, 'Pass12345!', **data)


def make_image(name: str = 'photo.png', color: str = 'pink'):
    image = BytesIO()
    Image.new('RGB', (10, 10), color).save(image, 'PNG')
    return SimpleUploadedFile(name, image.getvalue(), content_type='image/png')


class RegisterTest(APITestCase):
    def get_data(self, **kwargs) -> dict:
        data = {
            'email': 'Ivan@Mail.ru',
            'password': 'Pass12345!',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'gender': 'm',
            'birth_date': '1995-05-20',
            'city': 'Санкт-Петербург',
        }
        data.update(kwargs)
        return data

    def test_register_and_login_by_email(self):
        response = self.client.post(
            reverse('register'), self.get_data(), format='json'
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertNotIn('password', response.data)
        self.assertEqual(response.data['email'], 'ivan@mail.ru')
        response = self.client.post(
            reverse('token_obtain'),
            {'email': 'ivan@mail.ru', 'password': 'Pass12345!'},
            format='json',
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(reverse('user-me'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['full_name'], 'Иванов Иван')

    def test_wrong_data(self):
        wrong_data = [
            ({'password': '123'}, 'password'),
            ({'email': 'не почта'}, 'email'),
            ({'first_name': 'Иван2'}, 'first_name'),
            ({'city': ''}, 'city'),
            ({'gender': 'x'}, 'gender'),
            ({'birth_date': '2015-01-01'}, 'birth_date'),
            ({'birth_date': '1900-01-01'}, 'birth_date'),
        ]
        for data, field in wrong_data:
            with self.subTest(field=field, data=data):
                response = self.client.post(
                    reverse('register'), self.get_data(**data), format='json'
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                self.assertIn(field, response.data)
        self.assertFalse(User.objects.exists())

    def test_email_is_unique(self):
        make_user('ivan@mail.ru')
        response = self.client.post(
            reverse('register'), self.get_data(), format='json'
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('email', response.data)


class ProfileTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ivan = make_user('ivan@mail.ru', first_name='Иван')
        cls.anna = make_user(
            'anna@mail.ru',
            contacts='@anna',
            is_age_hidden=True,
            is_likes_hidden=True,
            is_full_name_hidden=True,
        )

    def setUp(self):
        self.client.force_authenticate(self.ivan)

    def test_anonymous_has_no_access(self):
        self.client.force_authenticate(None)
        for url in [reverse('user-me'), reverse('user-list')]:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code, HTTPStatus.UNAUTHORIZED
                )

    def test_update_my_profile(self):
        hobbies = Hobby.objects.all()[:2]
        response = self.client.patch(
            reverse('user-me'),
            {
                'city': 'Казань',
                'status': 'open',
                'about': 'Люблю горы',
                'hobby_ids': [hobby.pk for hobby in hobbies],
                'is_age_hidden': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['city'], 'Казань')
        self.assertEqual(
            response.data['status_display'], 'Открыт(а) к общению'
        )
        self.assertEqual(len(response.data['hobbies']), 2)
        self.assertEqual(response.data['age'], self.ivan.age)

    def test_wrong_profile_data(self):
        for data in [
            {'status': 'married'},
            {'city': 'Москва 2'},
            {'hobby_ids': [999999]},
            {'birth_date': '2020-01-01'},
        ]:
            with self.subTest(data=data):
                response = self.client.patch(
                    reverse('user-me'), data, format='json'
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_privacy(self):
        Reaction.objects.create(
            from_user=self.ivan, to_user=self.anna, is_like=True
        )
        response = self.client.get(reverse('user-detail', args=[self.anna.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['first_name'], 'Анна')
        self.assertIsNone(response.data['last_name'])
        self.assertIsNone(response.data['full_name'])
        self.assertIsNone(response.data['age'])
        self.assertIsNone(response.data['likes_count'])
        self.assertIsNone(response.data['contacts'])
        self.assertNotIn('email', response.data)

    def test_delete_profile(self):
        response = self.client.delete(reverse('user-me'))
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=self.ivan.pk).exists())


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PhotoTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user('anna@mail.ru')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.url = reverse('photo-list')
        self.client.force_authenticate(self.user)

    def upload(self, image=None):
        return self.client.post(
            self.url, {'image': image or make_image()}, format='multipart'
        )

    def test_first_photo_is_main(self):
        first_id = self.upload().data['id']
        response = self.upload()
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertFalse(response.data['is_main'])
        self.assertTrue(Photo.objects.get(pk=first_id).is_main)

    def test_set_main_photo(self):
        first_id = self.upload().data['id']
        second_id = self.upload().data['id']
        response = self.client.patch(
            reverse('photo-detail', args=[second_id]),
            {'is_main': True},
            format='json',
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(Photo.objects.get(pk=first_id).is_main)
        self.assertTrue(Photo.objects.get(pk=second_id).is_main)
        main_photo = self.client.get(reverse('user-me')).data['main_photo']
        self.assertTrue(
            main_photo.endswith(Photo.objects.get(pk=second_id).image.url)
        )

    def test_delete_photo_removes_file(self):
        first = Photo.objects.get(pk=self.upload().data['id'])
        second_id = self.upload().data['id']
        path = first.image.path
        self.assertTrue(os.path.exists(path))
        response = self.client.delete(reverse('photo-detail', args=[first.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertFalse(os.path.exists(path))
        self.assertTrue(Photo.objects.get(pk=second_id).is_main)

    def test_delete_user_removes_files(self):
        user = make_user('temp@mail.ru')
        self.client.force_authenticate(user)
        paths = [
            Photo.objects.get(pk=self.upload().data['id']).image.path
            for i in range(2)
        ]
        user.delete()
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def test_wrong_files(self):
        text_file = SimpleUploadedFile(
            'photo.png', b'not image', content_type='image/png'
        )
        self.assertEqual(
            self.upload(text_file).status_code, HTTPStatus.BAD_REQUEST
        )
        gif = BytesIO()
        Image.new('RGB', (10, 10)).save(gif, 'GIF')
        gif_file = SimpleUploadedFile(
            'photo.gif', gif.getvalue(), content_type='image/gif'
        )
        self.assertEqual(
            self.upload(gif_file).status_code, HTTPStatus.BAD_REQUEST
        )
        self.assertFalse(Photo.objects.exists())

    def test_cannot_change_other_photo(self):
        other = make_user('other@mail.ru')
        photo = Photo.objects.create(user=other, image=make_image())
        response = self.client.delete(reverse('photo-detail', args=[photo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class QueryCountTest(APITestCase):
    def create_users(self, count: int):
        hobbies = list(Hobby.objects.all()[:3])
        for i in range(count):
            user = make_user(f'user{User.objects.count()}@mail.ru')
            user.hobbies.set(hobbies)
            for j in range(2):
                Photo.objects.create(
                    user=user, image=make_image(), is_main=j == 0
                )

    def count_queries(self, url: str) -> int:
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return len(queries)

    def test_query_count_does_not_grow(self):
        viewer = make_user('viewer@mail.ru')
        self.client.force_authenticate(viewer)
        urls = [
            reverse('user-list'),
            reverse('user-random'),
            reverse('reaction-list'),
            reverse('view-list'),
            reverse('match-list'),
        ]
        self.create_users(2)
        for user in User.objects.exclude(pk=viewer.pk):
            Reaction.objects.create(
                from_user=viewer, to_user=user, is_like=True
            )
            Reaction.objects.create(
                from_user=user, to_user=viewer, is_like=True
            )
        make_user('free@mail.ru')
        small = [self.count_queries(url) for url in urls]
        self.create_users(10)
        for user in User.objects.exclude(pk=viewer.pk):
            Reaction.objects.get_or_create(
                from_user=viewer, to_user=user, defaults={'is_like': True}
            )
            Reaction.objects.get_or_create(
                from_user=user, to_user=viewer, defaults={'is_like': True}
            )
        make_user('free2@mail.ru')
        big = [self.count_queries(url) for url in urls]
        self.assertEqual(small, big)
        self.assertEqual(big[0], 3)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class DemoUsersCommandTest(APITestCase):
    def test_add_demo_users(self):
        for i in range(2):
            call_command('add_demo_users', stdout=StringIO())
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Photo.objects.count(), 4)
        anna = User.objects.get(email='anna@demo.ru')
        ivan = User.objects.get(email='ivan@demo.ru')
        self.assertEqual(anna.hobbies.count(), 4)
        self.assertEqual(ivan.likes_count, 1)
        self.assertTrue(ivan.photos.first().is_main)
        self.assertTrue(ivan.check_password('Demo12345!'))
