FROM craigwillis/cs598-hw5-base:v1

LABEL cs598_fdc=juhwans3@illinois.edu

RUN apt-get update \
    && apt-get install -y graphviz \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas \
    rdflib \
    lxml \
    prov \
    graphviz

WORKDIR /work
