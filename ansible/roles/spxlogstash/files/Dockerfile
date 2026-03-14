FROM docker.elastic.co/logstash/logstash:8.7.1

# Create a custom temporary directory with appropriate permissions
RUN mkdir /usr/share/logstash/tmp && \
    chmod 755 /usr/share/logstash/tmp

# Set the TMPDIR environment variable to use the custom temporary directory
ENV TMPDIR=/usr/share/logstash/tmp

# Install gzip_lines codec plugin
# Install gzip_lines and csv codec plugins
RUN /usr/share/logstash/bin/logstash-plugin install logstash-codec-gzip_lines && \
    /usr/share/logstash/bin/logstash-plugin install logstash-codec-csv

