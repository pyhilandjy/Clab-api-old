# requirements-stage
FROM python:3.9.19-bullseye as requirements-stage

WORKDIR /tmp

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    openssl \
    wget \
    libmecab-dev \
    mecab-ipadic-utf8 \
    build-essential \
    automake \
    autoconf \
    libtool \
    pkg-config \
    gettext \
    libc-dev

# MeCab Korean 설치
RUN wget -qO- https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz | tar xz && \
    cd mecab-0.996-ko-0.9.2 && ./configure && make && make install

RUN wget -qO- https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz | tar xz && \
    cd mecab-ko-dic-2.1.1-20180720 && ./autogen.sh && ./configure && make && make install

RUN ldconfig

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python && \
    cd /usr/local/bin && ln -s /opt/poetry/bin/poetry && poetry config virtualenvs.create false && poetry self add poetry-plugin-export

COPY ./pyproject.toml ./poetry.lock* /tmp/

# 환경이 올바른지 확인하기 위해 종속성 설치
RUN poetry install --no-root

# poetry-plugin-export 명시적으로 설치
RUN poetry self add poetry-plugin-export

ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then poetry export -f requirements.txt --output requirements.txt --dev --without-hashes; else poetry export -f requirements.txt --output requirements.txt --without-hashes; fi

# final-stage
FROM python:3.9.19-bullseye

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    openssl \
    wget \
    libmecab-dev \
    mecab-ipadic-utf8 \
    build-essential \
    automake \
    autoconf \
    libtool \
    pkg-config \
    gettext \
    libc-dev

# MeCab Korean 설치
RUN wget -qO- https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz | tar xz && \
    cd mecab-0.996-ko-0.9.2 && ./configure && make && make install

RUN wget -qO- https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz | tar xz && \
    cd mecab-ko-dic-2.1.1-20180720 && ./autogen.sh && ./configure && make && make install

RUN ldconfig

LABEL name="jychoi" version="0.1.0" description="connectslab_api"

RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime && echo "Asia/Tokyo" > /etc/timezone
ENV TZ=Asia/Tokyo

WORKDIR /src/

COPY --from=requirements-stage /tmp/requirements.txt /src/requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r /src/requirements.txt

# mecab-python3와 pandas 설치
RUN pip install mecab-python3 pandas

COPY ./NanumFontSetup_TTF_GOTHIC /src/NanumFontSetup_TTF_GOTHIC
COPY ./app /src/app/
COPY ./.env.example /src/.env

EXPOSE 2456
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "2456"]
