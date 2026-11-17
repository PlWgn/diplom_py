from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.serializers import ShortProfileSerializer

from .matches import is_match
from .models import Invite, ProfileView, Reaction

User = get_user_model()

ANSWER_CHOICES = [
    (Invite.Status.ACCEPTED, Invite.Status.ACCEPTED.label),
    (Invite.Status.DECLINED, Invite.Status.DECLINED.label),
]


class ReactionSerializer(serializers.ModelSerializer):
    to_user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), write_only=True
    )
    user = ShortProfileSerializer(source='to_user', read_only=True)

    class Meta:
        model = Reaction
        fields = (
            'id',
            'to_user',
            'user',
            'is_like',
            'created_at',
            'updated_at',
        )

    def validate_to_user(self, to_user):
        if to_user == self.context['request'].user:
            raise serializers.ValidationError('Нельзя оценить свою анкету')
        return to_user

    def create(self, validated_data: dict):
        reaction, is_created = Reaction.objects.update_or_create(
            from_user=validated_data['from_user'],
            to_user=validated_data['to_user'],
            defaults={'is_like': validated_data['is_like']},
        )
        reaction.is_created = is_created
        return reaction


class ReactionResultSerializer(ReactionSerializer):
    is_match = serializers.SerializerMethodField()

    class Meta(ReactionSerializer.Meta):
        fields = ReactionSerializer.Meta.fields + ('is_match',)

    def get_is_match(self, reaction: Reaction) -> bool:
        return reaction.is_like and is_match(
            reaction.from_user_id, reaction.to_user_id
        )


class ReceivedLikeSerializer(serializers.ModelSerializer):
    user = ShortProfileSerializer(source='from_user', read_only=True)

    class Meta:
        model = Reaction
        fields = ('id', 'user', 'created_at', 'updated_at')


class ProfileViewSerializer(serializers.ModelSerializer):
    user = ShortProfileSerializer(source='viewed', read_only=True)

    class Meta:
        model = ProfileView
        fields = ('id', 'user', 'viewed_at')


class MatchSerializer(ShortProfileSerializer):
    class Meta(ShortProfileSerializer.Meta):
        fields = ShortProfileSerializer.Meta.fields + ('contacts',)


class InviteSerializer(serializers.ModelSerializer):
    receiver = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), write_only=True
    )
    sender_profile = ShortProfileSerializer(source='sender', read_only=True)
    receiver_profile = ShortProfileSerializer(
        source='receiver', read_only=True
    )
    kind_display = serializers.CharField(
        source='get_kind_display', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    contacts = serializers.SerializerMethodField()

    class Meta:
        model = Invite
        fields = (
            'id',
            'receiver',
            'sender_profile',
            'receiver_profile',
            'kind',
            'kind_display',
            'message',
            'date_time',
            'place',
            'status',
            'status_display',
            'contacts',
            'created_at',
        )
        read_only_fields = ('status', 'created_at')

    def get_contacts(self, invite: Invite) -> str:
        if invite.status != Invite.Status.ACCEPTED:
            return None
        user = self.context['request'].user
        other = (
            invite.receiver if invite.sender_id == user.pk else invite.sender
        )
        return other.contacts

    def validate(self, data: dict):
        sender = self.context['request'].user
        receiver = data['receiver']
        if receiver == sender:
            raise serializers.ValidationError(
                {'receiver': 'Нельзя пригласить самого себя'}
            )
        if not is_match(sender.pk, receiver.pk):
            raise serializers.ValidationError(
                {
                    'receiver': 'Пригласить можно только пользователя '
                    'со взаимной симпатией'
                }
            )
        if data['kind'] == Invite.Kind.DATE and not data.get('date_time'):
            raise serializers.ValidationError(
                {'date_time': 'Укажите дату и время свидания'}
            )
        is_duplicate = Invite.objects.filter(
            sender=sender,
            receiver=receiver,
            kind=data['kind'],
            status=Invite.Status.PENDING,
        ).exists()
        if is_duplicate:
            raise serializers.ValidationError(
                'Такое приглашение уже отправлено и ждет ответа'
            )
        return data


class InviteAnswerSerializer(InviteSerializer):
    receiver = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.ChoiceField(choices=ANSWER_CHOICES)

    class Meta(InviteSerializer.Meta):
        read_only_fields = tuple(
            field
            for field in InviteSerializer.Meta.fields
            if field != 'status'
        )

    def validate(self, data: dict):
        if self.instance.status != Invite.Status.PENDING:
            raise serializers.ValidationError('На приглашение уже ответили')
        return data
