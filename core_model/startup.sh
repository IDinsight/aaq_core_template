#!/bin/bash
# Script called from parent directory

# Note on root:
# The Dockerfile is configured to launch this script as root, since we need to be root to run cron.
# We switch to container_user when we run the process (gunicorn), in line with standards.
# See https://github.com/praekeltfoundation/docker-py-base.

# Setup cron job to refresh FAQs, every hour on 0th minute
# (The crontab must be added here, not in the Dockerfile, since it relies on a secret passed into the container)
if [[ $ENABLE_FAQ_REFRESH_CRON == "true" ]]; then
    echo "Enabling cron job for FAQ refresh"
    service cron start
    echo '*/5 * * * * curl http://127.0.0.1:'$PORT'/internal/refresh-faqs -H "Authorization: Bearer '$INBOUND_CHECK_TOKEN'"' > cronfaqs
    crontab cronfaqs
else
    echo "Cron job not enabled within container. Set ENABLE_FAQ_REFRESH_CRON to 'true' to run"
fi

# Note: timeout is high here to allow for loading the large pre-trained model
# Note: we run with 2n+1 workers, preloading application (to share the large model in RAM)
# Note: application is not thread-safe, so must be single-threaded
exec su-exec container_user \
    gunicorn --timeout 300 --workers=$((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --preload flask_app:app -b 0.0.0.0:$PORT
