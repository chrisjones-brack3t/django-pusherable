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

    def send_pusher_notification(self, data):
        """ Sends the notification to pusher """
        self.pusher.trigger(
            [self.channel],
            self.get_pusher_event_name(),
            self.get_pusher_payload(data))


class PusherUpdateMixin(PusherMixin):
    pusher_event_name = 'update'

    def form_valid(self, form):
        """
        Call super first to make sure the object saves.
        Call pusher methods and send notification.
        """
        response = super(PusherUpdateMixin, self).form_valid(form)

        self._set_pusher()
        self._set_pusher_channel()
        data = self._object_to_json_serializable(self.object)
        self.send_pusher_notification(data)

        return response


class PusherDetailMixin(PusherMixin):
    pusher_event_name = 'view'

    def render_to_response(self, context, **kwargs):
        """
        Generate Response first.
        Send pusher notification.
        """
        response = super(PusherDetailMixin, self).render_to_response(
            context, **kwargs)

        self._set_pusher()
        self._set_pusher_channel()
        data = self._object_to_json_serializable(self.object)
        self.send_pusher_notification(data)

        return response


class PusherDeleteMixin(PusherMixin):
    pusher_event_name = 'delete'

    def delete(self, *args, **kwargs):
        response = super(PusherDeleteMixin, self).delete(*args, **kwargs)

        self._set_pusher()
        self._set_pusher_channel()
        data = self._object_to_json_serializable(self.object)
        self.send_pusher_notification(data)

        return response
