# -*- coding: utf-8 -*-

import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

from pusher import Pusher


class PusherMixin(object):
    pusher_include_model_fields = None
    pusher_event_name = None
    pusher_exclude_model_fields = None

    def _object_to_json_serializable(self, object):
        model_dict = model_to_dict(
            object, fields=self.pusher_include_model_fields,
            exclude=self.pusher_exclude_model_fields)
        json_data = json.dumps(model_dict, cls=DjangoJSONEncoder)
        data = json.loads(json_data)

        return data

    def set_pusher(self):
        """
        Check that pusher settings exist or raise ValidationError.
        Create Pusher on object.
        """
        if hasattr(self, 'pusher') and isinstance(self.pusher, Pusher):
            return

        app_id = getattr(settings, 'PUSHER_APP_ID', None)
        key = getattr(settings, 'PUSHER_KEY', None)
        secret = getattr(settings, 'PUSHER_SECRET', None)

        if not all([app_id, key, secret]):
            raise ImproperlyConfigured(
                'Pusher settings are not defined. Make sure PUSHER_APP_ID, '
                'PUSHER_KEY and PUSHER_SECRET are set in your settings file.')

        self.pusher = Pusher(
            app_id=getattr(settings, 'PUSHER_APP_ID'),
            key=getattr(settings, 'PUSHER_KEY'),
            secret=getattr(settings, 'PUSHER_SECRET'))

    def set_pusher_channel(self):
        """
        Set the pusher channel
        <model_name>_<primary_key>
        """
        self.channel = '{model}_{pk}'.format(
            model=self.object._meta.model_name,
            pk=self.object.pk)

    def get_pusher_payload(self, data):
        """
        Method responsible for building payload data for pusher.
        Override this method to customize the data sent to pusher.
        Method should return a dict.
        """
        user = self.request.user
        username = user.username

        if user.is_anonymous():
            username = 'Anonymous User'

        return {
            'object': data,
            'user': username
        }

    def send_pusher_notification(self, event):
        self.set_pusher()
        self.set_pusher_channel()
        data = self._object_to_json_serializable(self.object)
        self.pusher.trigger(
            [self.channel], event, self.get_pusher_payload(data))


class PusherViewedMixin(PusherMixin):
    event_name_viewed = 'viewed'

    def get(self, request, *args, **kwargs):
        response = super(PusherViewedMixin, self).get(
            request, *args, **kwargs)
        self.send_pusher_notification(self.event_name_viewed)
        return response


class PusherUpdatePendingMixin(PusherMixin):
    event_name_update_pending = 'update_pending'

    def get(self, request, *args, **kwargs):
        response = super(PusherUpdatePendingMixin, self).get(
            request, *args, **kwargs)
        self.send_pusher_notification(self.event_name_update_pending)
        return response


class PusherUpdateSucceededMixin(PusherMixin):
    event_name_update_success = 'update_succeeded'

    def form_valid(self, form):
        response = super(PusherUpdateSucceededMixin, self).form_valid(form)
        self.send_pusher_notification(self.event_name_update_success)
        return response


class PusherUpdateFailedMixin(PusherMixin):
    event_name_update_fail = 'update_failed'

    def form_invalid(self, form):
        self.send_pusher_notification(self.event_name_update_fail)
        response = super(PusherUpdateFailedMixin, self).form_valid(form)
        return response


class PusherDeletePendingMixin(PusherMixin):
    event_name_delete_pending = 'delete_pending'

    def get(self, request, *args, **kwargs):
        response = super(PusherDeletePendingMixin, self).get(
            request, *args, **kwargs)
        self.send_pusher_notification(self.event_name_delete_pending)
        return response


class PusherDeleteSucceededMixin(PusherMixin):
    event_name_delete_succeeded = 'delete_succeeded'

    def delete(self, *args, **kwargs):
        """
        TODO: Verify this approach won't cause problems or find another
        way.


        Not sure if I like this implementation. It feels sketchy.
        We hold onto a copy of the obj before it is deleted. After
        the super call (object should be deleted at that point)
        we set the copied object back on self so that it can be used
        by the mixin to connect to the pusher channel. Could just
        call the pusher notification before the super call but it
        is possible that the delete is not successful and thus
        we've given the user false information.
        """
        obj = self.get_object()
        response = super(PusherDeleteSucceededMixin, self).delete(
            *args, **kwargs)
        self.object = obj
        self.send_pusher_notification(self.event_name_delete_succeeded)
        return response
