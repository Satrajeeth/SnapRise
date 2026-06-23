FROM postgres:16

RUN apt-get update && \
    apt-get install -y pgbackrest cron && \
    rm -rf /var/lib/apt/lists/*

COPY pgbackrest.conf /etc/pgbackrest.conf
RUN chown postgres:postgres /etc/pgbackrest.conf && chmod 640 /etc/pgbackrest.conf

COPY setup_stanza.sh /docker-entrypoint-initdb.d/
RUN chmod +x /docker-entrypoint-initdb.d/setup_stanza.sh

COPY crontab /etc/cron.d/pgbackrest-cron
RUN chmod 0644 /etc/cron.d/pgbackrest-cron && \
    crontab -u postgres /etc/cron.d/pgbackrest-cron

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

ENTRYPOINT ["start.sh"]
CMD ["postgres"]
