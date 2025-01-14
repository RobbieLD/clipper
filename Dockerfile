FROM python:3

WORKDIR /app

RUN pip install numpy

RUN apt-get -y update

RUN apt-get update && apt-get install -y ffmpeg

COPY extractor.py ./

ENV SPAN=10, DRY=false, COMPRESS=true

CMD [ "python", "./extractor.py" ]