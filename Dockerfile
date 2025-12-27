FROM alpine:latest

RUN apk add --no-cache tinyproxy curl

RUN echo "Port 3007" > /etc/tinyproxy/tinyproxy.conf && \
    echo "Listen 0.0.0.0" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "Timeout 600" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "MaxClients 100" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "Allow 0.0.0.0/0" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "LogLevel Connect" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "LogFile \"/dev/stdout\"" >> /etc/tinyproxy/tinyproxy.conf && \
    echo "XTinyproxy On" >> /etc/tinyproxy/tinyproxy.conf

RUN mkdir -p /var/run/tinyproxy && chown -R tinyproxy:tinyproxy /var/run/tinyproxy

USER tinyproxy
EXPOSE 3007

CMD ["tinyproxy", "-d"]
