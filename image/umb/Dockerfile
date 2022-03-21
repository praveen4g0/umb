# Using official python runtime base image
FROM registry.access.redhat.com/ubi8/python-38

# Install our requirements.txt
ADD requirements.txt consumer.py producer.py /opt/app-root/src/
RUN pip install --upgrade pip && \
    pip install -Ur requirements.txt

USER 1001

# Make port 80 available for links and/or publish
EXPOSE 8080
