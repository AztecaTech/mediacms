#!/bin/bash

RANDOM_ADMIN_PASS=`python -c "import secrets;chars = 'abcdefghijklmnopqrstuvwxyz0123456789';print(''.join(secrets.choice(chars) for i in range(10)))"`
ADMIN_PASSWORD=${ADMIN_PASSWORD:-$RANDOM_ADMIN_PASS}

if [ X"$ENABLE_MIGRATIONS" = X"yes" ]; then
    echo "Running migrations service"
    python manage.py migrate

    # Encode profiles are the reliable "DB has been provisioned" marker. Only seed default
    # categories on the first run where encoding fixtures were absent — not whenever User
    # check fails or the DB was wiped in odd ways while profiles already exist.
    HAS_ENCODE_PROFILES=$(python -c "import django; django.setup(); from files.models import EncodeProfile; print('True' if EncodeProfile.objects.exists() else 'False')" 2>/dev/null || echo "False")
    if [ "$HAS_ENCODE_PROFILES" != "True" ]; then
        echo "Loading encoding profiles fixture (first-time DB seed)"
        python manage.py loaddata fixtures/encoding_profiles.json
        FRESH_ENCODING_SEED=1
    else
        FRESH_ENCODING_SEED=0
    fi

    HAS_USER=$(python -c "import django; django.setup(); from users.models import User; print('True' if User.objects.exists() else 'False')" 2>/dev/null || echo "False")
    if [ "$HAS_USER" = "True" ]; then
        echo "Admin user(s) already exist; skipping category fixture and createsuperuser"
    else
        # Default categories only on first install (encoding fixtures were just loaded).
        # Set SEED_DEFAULT_CATEGORIES=no to skip even then.
        SEED_CATS="${SEED_DEFAULT_CATEGORIES:-yes}"
        if [ "$FRESH_ENCODING_SEED" = "1" ] && [ "$SEED_CATS" != "no" ] && [ "$SEED_CATS" != "false" ] && [ "$SEED_CATS" != "0" ]; then
            echo "Loading default categories fixture (first install only)"
            python manage.py loaddata fixtures/categories.json
        elif [ "$FRESH_ENCODING_SEED" != "1" ]; then
            echo "Skipping categories fixture (encoding profiles already present — not a fresh DB)"
        else
            echo "Skipping categories fixture (SEED_DEFAULT_CATEGORIES=$SEED_CATS)"
        fi

        # post_save, needs redis to succeed (ie. migrate depends on redis)
        echo "Creating admin user"
        DJANGO_SUPERUSER_PASSWORD=$ADMIN_PASSWORD python manage.py createsuperuser \
            --no-input \
            --username=$ADMIN_USER \
            --email=$ADMIN_EMAIL \
            --database=default || true
        echo "Created admin user with password: $ADMIN_PASSWORD"
    fi

    echo "Ensuring Site record exists for FRONTEND_HOST ..."
    echo "from django.contrib.sites.models import Site; site, _ = Site.objects.get_or_create(id=1, defaults={'domain': 'localhost', 'name': 'MediaCMS'}); site.domain = '${FRONTEND_HOST}'.replace('https://', '').replace('http://', '').rstrip('/'); site.name = 'MediaCMS'; site.save(); print(f'Site domain set to: {site.domain}')" | python manage.py shell
fi

# Seed default media assets (volume mount hides files baked into the image)
mkdir -p /home/mediacms.io/mediacms/media_files/userlogos
cp -n /home/mediacms.io/mediacms/media_files_defaults/userlogos/* /home/mediacms.io/mediacms/media_files/userlogos/ 2>/dev/null || true

echo "RUNNING COLLECTSTATIC"
python manage.py collectstatic --noinput

# Setting up internal nginx server
# HTTPS setup is delegated to a reverse proxy running infront of the application

cp deploy/docker/nginx_http_only.conf /etc/nginx/sites-available/default
cp deploy/docker/nginx_http_only.conf /etc/nginx/sites-enabled/default
cp deploy/docker/uwsgi_params /etc/nginx/sites-enabled/uwsgi_params
cp deploy/docker/nginx.conf /etc/nginx/

#### Supervisord Configurations #####

cp deploy/docker/supervisord/supervisord-debian.conf /etc/supervisor/conf.d/supervisord-debian.conf

if [ X"$ENABLE_UWSGI" = X"yes" ] ; then
    echo "Enabling uwsgi app server"
    cp deploy/docker/supervisord/supervisord-uwsgi.conf /etc/supervisor/conf.d/supervisord-uwsgi.conf
fi

if [ X"$ENABLE_NGINX" = X"yes" ] ; then
    echo "Enabling nginx as uwsgi app proxy and media server"
    cp deploy/docker/supervisord/supervisord-nginx.conf /etc/supervisor/conf.d/supervisord-nginx.conf
fi

if [ X"$ENABLE_CELERY_BEAT" = X"yes" ] ; then
    echo "Enabling celery-beat scheduling server"
    cp deploy/docker/supervisord/supervisord-celery_beat.conf /etc/supervisor/conf.d/supervisord-celery_beat.conf
fi

if [ X"$ENABLE_CELERY_SHORT" = X"yes" ] ; then
    echo "Enabling celery-short task worker"
    cp deploy/docker/supervisord/supervisord-celery_short.conf /etc/supervisor/conf.d/supervisord-celery_short.conf
fi

if [ X"$ENABLE_CELERY_LONG" = X"yes" ] ; then
    echo "Enabling celery-long task worker"
    cp deploy/docker/supervisord/supervisord-celery_long.conf /etc/supervisor/conf.d/supervisord-celery_long.conf
    rm /var/run/mediacms/* -f # remove any stale id, so that on forced restarts of celery workers there are no stale processes that prevent new ones
fi
