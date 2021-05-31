# Using official python runtime base image
FROM registry.access.redhat.com/ubi8/python-38

# Install our requirements.txt
ADD requirements.txt /opt/app-root/src/requirements.txt
RUN pip install --upgrade pip && \
    pip install -Ur requirements.txt

# Copy our code from the current folder to /app inside the container
ADD . /opt/app-root/src

USER 1001

# Define our command to be run when launching the container
CMD ["python", "./consumer.py"]