from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def pusherable_script():
    return ('<script src="//js.pusher.com/3.0/pusher.min.js" '
            'type="text/javascript"></script>')


@register.simple_tag
def pusherable_subscribe(instance):
    """
    Channel: <model_name>_<model_primary_key>
    """
    channel = '{model_name}_{model_pk}'.format(
        model_name=instance._meta.model_name, model_pk=instance.pk)

    return """
    <script>
        var pusher = new Pusher('{api_key}'),
            channel = pusher.subscribe('{channel}');
        channel.bind_all(function(event, data) {{
            if (event.indexOf('pusher:') === 0) {{
                return false;
            }}
            pusherable_notify(event, data);
        }});
    </script>
    """.format(api_key=settings.PUSHER_KEY, channel=channel)
