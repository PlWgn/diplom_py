from datetime import date, timedelta
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Invite, ProfileView, Reaction

User = get_user_model()


def make_user(email: str, **kwargs):
    data = {
        'first_name': 'Анна',
        'last_name': 'Петрова',
        'gender': User.Gender.FEMALE,
        'birth_date': date(2000, 1, 1),
        'city': 'Москва',
    }
    data.update(kwargs)
    return User.objects.create_user(email, 'Pass12345!', **data)


class ReactionTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ivan = make_user(
            'ivan@mail.ru', first_name='Иван', gender=User.Gender.MALE
        )
        cls.anna = make_user('anna@mail.ru')
        cls.olga = make_user('olga@mail.ru', first_name='Ольга')

    def setUp(self):
        self.url = reverse('reaction-list')
        self.client.force_authenticate(self.ivan)

    def react(self, user, is_like: bool = True):
        return self.client.post(
            self.url, {'to_user': user.pk, 'is_like': is_like}, format='json'
        )

    def get_likes_count(self, user) -> int:
        user.refresh_from_db()
        return user.likes_count

    def test_anonymous_cannot_react(self):
        self.client.force_authenticate(None)
        response = self.react(self.anna)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertFalse(Reaction.objects.exists())

    def test_like(self):
        response = self.react(self.anna)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertTrue(response.data['is_like'])
        self.assertFalse(response.data['is_match'])
        self.assertEqual(response.data['user']['id'], self.anna.pk)
        self.assertEqual(self.get_likes_count(self.anna), 1)

    def test_dislike_does_not_change_likes_count(self):
        response = self.react(self.anna, is_like=False)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertFalse(response.data['is_like'])
        self.assertEqual(self.get_likes_count(self.anna), 0)

    def test_repeat_like_does_not_duplicate(self):
        self.react(self.anna)
        response = self.react(self.anna)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Reaction.objects.count(), 1)
        self.assertEqual(self.get_likes_count(self.anna), 1)

    def test_change_like_to_dislike_and_back(self):
        self.react(self.anna)
        response = self.react(self.anna, is_like=False)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Reaction.objects.count(), 1)
        self.assertEqual(self.get_likes_count(self.anna), 0)
        self.react(self.anna)
        self.assertEqual(self.get_likes_count(self.anna), 1)

    def test_delete_like(self):
        reaction_id = self.react(self.anna).data['id']
        response = self.client.delete(
            reverse('reaction-detail', args=[reaction_id])
        )
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        self.assertEqual(self.get_likes_count(self.anna), 0)

    def test_cannot_delete_other_reaction(self):
        reaction = Reaction.objects.create(
            from_user=self.anna, to_user=self.olga, is_like=True
        )
        response = self.client.delete(
            reverse('reaction-detail', args=[reaction.pk])
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTrue(Reaction.objects.filter(pk=reaction.pk).exists())

    def test_cannot_react_to_self(self):
        response = self.react(self.ivan)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('to_user', response.data)

    def test_wrong_data(self):
        for data in [
            {'to_user': 999999, 'is_like': True},
            {'to_user': self.anna.pk},
            {'to_user': self.anna.pk, 'is_like': 'может быть'},
        ]:
            with self.subTest(data=data):
                response = self.client.post(self.url, data, format='json')
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(Reaction.objects.exists())

    def test_match(self):
        Reaction.objects.create(
            from_user=self.anna, to_user=self.ivan, is_like=True
        )
        response = self.react(self.anna)
        self.assertTrue(response.data['is_match'])
        response = self.client.get(reverse('match-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.anna.pk)

    def test_dislike_is_not_match(self):
        Reaction.objects.create(
            from_user=self.anna, to_user=self.ivan, is_like=True
        )
        self.assertFalse(self.react(self.anna, is_like=False).data['is_match'])
        self.assertEqual(
            self.client.get(reverse('match-list')).data['count'], 0
        )

    def test_liked_and_disliked_lists(self):
        self.react(self.anna)
        self.react(self.olga, is_like=False)
        liked = self.client.get(self.url, {'is_like': 'true'}).data
        disliked = self.client.get(self.url, {'is_like': 'false'}).data
        self.assertEqual(liked['count'], 1)
        self.assertEqual(liked['results'][0]['user']['id'], self.anna.pk)
        self.assertEqual(disliked['count'], 1)
        self.assertEqual(disliked['results'][0]['user']['id'], self.olga.pk)

    def test_received_likes_history(self):
        Reaction.objects.create(
            from_user=self.anna, to_user=self.ivan, is_like=True
        )
        Reaction.objects.create(
            from_user=self.olga, to_user=self.ivan, is_like=False
        )
        response = self.client.get(reverse('reaction-received'))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['user']['id'], self.anna.pk
        )

    def test_user_delete_decreases_likes_count(self):
        user = make_user('temp@mail.ru')
        Reaction.objects.create(
            from_user=user, to_user=self.anna, is_like=True
        )
        self.assertEqual(self.get_likes_count(self.anna), 1)
        user.delete()
        self.assertEqual(self.get_likes_count(self.anna), 0)


class RandomProfileTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ivan = make_user(
            'ivan@mail.ru', first_name='Иван', gender=User.Gender.MALE
        )
        cls.anna = make_user('anna@mail.ru', city='Казань')
        cls.olga = make_user(
            'olga@mail.ru',
            first_name='Ольга',
            birth_date=date(1985, 6, 15),
            status=User.Status.BUSY,
        )
        cls.hidden = make_user('hidden@mail.ru', is_visible=False)

    def setUp(self):
        self.url = reverse('user-random')
        self.client.force_authenticate(self.ivan)

    def get_random_ids(self, params: dict = None, times: int = 20) -> set:
        ids = set()
        for i in range(times):
            response = self.client.get(self.url, params or {})
            if response.status_code == HTTPStatus.OK:
                ids.add(response.data['id'])
        return ids

    def test_shows_only_other_visible_profiles(self):
        self.assertEqual(self.get_random_ids(), {self.anna.pk, self.olga.pk})

    def test_filters(self):
        filters = [
            ({'city': 'Казань'}, {self.anna.pk}),
            ({'status': 'busy'}, {self.olga.pk}),
            ({'age_min': 30}, {self.olga.pk}),
            ({'age_max': 30}, {self.anna.pk}),
            ({'gender': 'm'}, set()),
        ]
        for params, expected_ids in filters:
            with self.subTest(params=params):
                self.assertEqual(self.get_random_ids(params, 5), expected_ids)

    def test_wrong_filter(self):
        response = self.client.get(self.url, {'age_min': 5})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = self.client.get(self.url, {'gender': 'x'})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_reacted_profiles_are_not_shown(self):
        Reaction.objects.create(
            from_user=self.ivan, to_user=self.anna, is_like=True
        )
        Reaction.objects.create(
            from_user=self.ivan, to_user=self.olga, is_like=False
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_view_history(self):
        self.client.get(self.url, {'city': 'Казань'})
        self.client.get(self.url, {'city': 'Казань'})
        self.assertEqual(ProfileView.objects.count(), 1)
        response = self.client.get(reverse('view-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(
            response.data['results'][0]['user']['id'], self.anna.pk
        )

    def test_random_like_flow(self):
        shown_ids = []
        for i in range(2):
            profile = self.client.get(self.url).data
            shown_ids.append(profile['id'])
            self.client.post(
                reverse('reaction-list'),
                {'to_user': profile['id'], 'is_like': i == 0},
                format='json',
            )
        self.assertEqual(set(shown_ids), {self.anna.pk, self.olga.pk})
        self.assertEqual(
            self.client.get(self.url).status_code, HTTPStatus.NOT_FOUND
        )


class InviteTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ivan = make_user(
            'ivan@mail.ru',
            first_name='Иван',
            gender=User.Gender.MALE,
            contacts='@ivan',
        )
        cls.anna = make_user('anna@mail.ru', contacts='+79990001122')
        cls.olga = make_user('olga@mail.ru')
        Reaction.objects.create(
            from_user=cls.ivan, to_user=cls.anna, is_like=True
        )
        Reaction.objects.create(
            from_user=cls.anna, to_user=cls.ivan, is_like=True
        )
        Reaction.objects.create(
            from_user=cls.ivan, to_user=cls.olga, is_like=True
        )

    def setUp(self):
        self.url = reverse('invite-list')
        self.client.force_authenticate(self.ivan)

    def invite(self, user, **kwargs):
        data = {
            'receiver': user.pk,
            'kind': 'date',
            'message': 'Пойдем в кино?',
            'date_time': (timezone.now() + timedelta(days=2)).isoformat(),
            'place': 'Кинотеатр',
        }
        data.update(kwargs)
        return self.client.post(self.url, data, format='json')

    def test_invite_only_match(self):
        self.assertEqual(
            self.invite(self.anna).status_code, HTTPStatus.CREATED
        )
        response = self.invite(self.olga)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('receiver', response.data)

    def test_date_validation(self):
        past = (timezone.now() - timedelta(hours=1)).isoformat()
        response = self.invite(self.anna, date_time=past)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn('date_time', response.data)
        response = self.invite(self.anna, date_time=None)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = self.invite(self.anna, kind='contacts', date_time=None)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_no_duplicate_pending_invite(self):
        self.invite(self.anna)
        response = self.invite(self.anna)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_accept_shows_contacts(self):
        invite_id = self.invite(self.anna, kind='contacts').data['id']
        matches = self.client.get(reverse('match-list')).data['results']
        self.assertIsNone(matches[0]['contacts'])
        detail_url = reverse('invite-detail', args=[invite_id])
        response = self.client.patch(
            detail_url, {'status': 'accepted'}, format='json'
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.client.force_authenticate(self.anna)
        incoming = self.client.get(self.url, {'direction': 'incoming'}).data
        self.assertEqual(incoming['count'], 1)
        response = self.client.patch(
            detail_url, {'status': 'accepted'}, format='json'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.data['contacts'], '@ivan')
        self.client.force_authenticate(self.ivan)
        matches = self.client.get(reverse('match-list')).data['results']
        self.assertEqual(matches[0]['contacts'], '+79990001122')
        profile = self.client.get(reverse('user-detail', args=[self.anna.pk]))
        self.assertEqual(profile.data['contacts'], '+79990001122')

    def test_answer_only_once(self):
        invite = Invite.objects.create(
            sender=self.ivan,
            receiver=self.anna,
            kind=Invite.Kind.CONTACTS,
            status=Invite.Status.DECLINED,
        )
        self.client.force_authenticate(self.anna)
        response = self.client.patch(
            reverse('invite-detail', args=[invite.pk]),
            {'status': 'accepted'},
            format='json',
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_cancel_invite(self):
        invite_id = self.invite(self.anna).data['id']
        detail_url = reverse('invite-detail', args=[invite_id])
        self.client.force_authenticate(self.anna)
        self.assertEqual(
            self.client.delete(detail_url).status_code, HTTPStatus.FORBIDDEN
        )
        self.client.force_authenticate(self.ivan)
        self.assertEqual(
            self.client.delete(detail_url).status_code, HTTPStatus.NO_CONTENT
        )
