FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    postfix \
    mailutils \
    libsasl2-2 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Configure postfix
RUN postconf -e "myhostname=smtp.local" \
    && postconf -e "myorigin=/etc/mailname" \
    && postconf -e "inet_interfaces=all" \
    && postconf -e "inet_protocols=ipv4" \
    && postconf -e "mydestination=" \
    && postconf -e "relayhost=" \
    && postconf -e "mynetworks=0.0.0.0/0" \
    && postconf -e "home_mailbox=Maildir/"

RUN echo "smtp.local" > /etc/mailname

EXPOSE 25

CMD ["postfix", "start-fg"]
