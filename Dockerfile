# Docker file to create a webserver rendering string of latex document/piece and return a png file

FROM texlive/texlive

RUN apt-get update && \ 
    apt-get install -y --no-install-recommends \
        poppler-utils \
        vim \
        python3-pip && \
    python -m pip install --upgrade pip && \
    pip install --upgrade tornado

RUN mkdir -p /root/latex
WORKDIR /root/latex/
COPY . .

EXPOSE 8888

CMD ["python", "xe-latex-server.py"]