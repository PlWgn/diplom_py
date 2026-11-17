from django.db.models import Q

from .models import Invite, Reaction


def is_match(user_id: int, other_id: int) -> bool:
    likes_count = (
        Reaction.objects.filter(is_like=True)
        .filter(
            Q(from_user_id=user_id, to_user_id=other_id)
            | Q(from_user_id=other_id, to_user_id=user_id)
        )
        .count()
    )
    return likes_count == 2


def get_match_ids(user_id: int) -> set:
    return set(
        Reaction.objects.filter(
            from_user_id=user_id,
            is_like=True,
            to_user__reactions_sent__to_user_id=user_id,
            to_user__reactions_sent__is_like=True,
        ).values_list('to_user_id', flat=True)
    )


def get_exchanged_ids(user_id: int) -> set:
    pairs = Invite.objects.filter(
        Q(sender_id=user_id) | Q(receiver_id=user_id),
        status=Invite.Status.ACCEPTED,
    ).values_list('sender_id', 'receiver_id')
    return {
        receiver_id if sender_id == user_id else sender_id
        for sender_id, receiver_id in pairs
    }
