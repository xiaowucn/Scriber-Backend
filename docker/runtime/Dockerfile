FROM harbor.wujiaxing.top/library/nginx:latest AS nginx 

FROM harbor.wujiaxing.top/library/ubuntu:24.04 

ARG NGINX_VERSION=""

ENV LANG=en_US.UTF-8 \
    TZ=Asia/Shanghai \
    PYTHONPATH=/opt/scriber \
    DOTNET_ROOT=/usr/share/dotnet \
    PATH=${PATH}:/usr/share/dotnet:/usr/local/instantclient \
    LD_PRELOAD=/usr/local/lib/python3.12/dist-packages/palladium/libpdfium.so \
    PIP_ROOT_USER_ACTION=ignore \
    PIP_INDEX_URL=http://100.64.0.1:3141/cheftin/pypi \
    PIP_TRUSTED_HOST=100.64.0.1 \
    PIP_BREAK_SYSTEM_PACKAGES=true \
    PIP_NO_CACHE_DIR=true \
    PIP_DISABLE_PIP_VERSION_CHECK=true \
    UV_NO_CACHE=true \
    UV_PROJECT_ENVIRONMENT=/usr/ \
    UV_BREAK_SYSTEM_PACKAGES=true \
    UV_SYSTEM_PYTHON=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PSYCOPG2_GAUSS=False \
    LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/lib:/usr/local/instantclient \
    SUPERVISOR_LOGFILE_BACKUPS=180 \
    SUPERVISOR_LOGFILE_BY_DATE="D"

WORKDIR /opt/scriber

SHELL ["/bin/bash", "-c"]

RUN --mount=type=bind,source=./,target=/builder \
    --mount=type=bind,from=nginx,source=/usr/lib/nginx/modules/,target=/nginx-modules \
    cp -a /builder/. /opt/scriber && \
    set -o pipefail -e && \
    ( userdel -r -f ubuntu || true ) && \
    useradd -s /bin/bash scriber && \
    sed -Ei 's/(ports|archive).ubuntu.com/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/ubuntu.sources && \
    apt update -y && \
    DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
        python3.12-dev \
        python3.12-full \
        libpq-dev \
        vim-tiny \
        jq \
        ca-certificates \
        tzdata \
        locales \
        build-essential \
        fontconfig \
        libsm6 \
        libgtk2.0-dev \
        gosu \
        gnupg \
        # qpdf
        qpdf \
        mono-devel \
        # pdftoppm
        poppler-utils \
        # java11
        openjdk-11-jdk \
        # oracle
        libaio1t64 \
        libgdiplus \
        # common
        patchelf \
        redis-tools \
        postgresql-client \
        curl \
        zstd \
        wget \
        htop \
        libatk-bridge2.0-0 \
        libatspi2.0-0 \
        libgbm1 \
        libxkbcommon0 \
        software-properties-common \
        netcat-traditional && \
    # install nginx
    source /etc/os-release && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/chrome.list && \
    ( wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - ) && \
    ( curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor | tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null ) && \
    ( echo -e "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/mainline/ubuntu ${VERSION_CODENAME} nginx" \
        | tee /etc/apt/sources.list.d/nginx.list ) && \
    ( echo -e "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] http://nginx.org/packages/ubuntu ${VERSION_CODENAME} nginx" \
        | tee /etc/apt/sources.list.d/nginx-stable.list ) && \
    # install gosu and configuration chrome preinstall and libaio.so.1 set soft link
    ARCH=$(uname -m) && \
    CHROME_NAME="google-chrome-stable" && \
    if [ "$ARCH" = "aarch64" ]; then \
      add-apt-repository ppa:xtradeb/apps -y && \
      CHROME_NAME="chromium" && \
      ln -sf /usr/lib/aarch64-linux-gnu/libaio.so.1t64.0.2 /usr/lib/aarch64-linux-gnu/libaio.so.1 && \
      wget -qO /tmp/dotnet-runtime-6.0.36-linux.tar.gz https://fm.paodingai.com/api/public/dl/-1VBtejs/dotnet_runtime/dotnet-runtime-6.0.36-linux-arm64.tar.gz && \
      wget -qO /tmp/instantclient.tgz https://fm.paodingai.com/api/public/dl/lxVd6kK1/oracle_client/instantclient_arm64_23.9.tgz; \
    elif [ "$ARCH" = "x86_64" ]; then \
      echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/chrome.list && \
      ( wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - ) && \
      ln -sf /usr/lib/x86_64-linux-gnu/libaio.so.1t64.0.2 /usr/lib/x86_64-linux-gnu/libaio.so.1 && \
      wget -qO /tmp/dotnet-runtime-6.0.36-linux.tar.gz https://fm.paodingai.com/api/public/dl/XAz7kZQY/dotnet_runtime/dotnet-runtime-6.0.36-linux-x64.tar.gz && \
      wget -qO /tmp/instantclient.tgz https://fm.paodingai.com/api/public/dl/BjTO3aHc/oracle_client/instantclient_amd64_21.3.tgz; \
    else \
      echo "Unsupported architecture: $ARCH" >&2 && exit 1; \
    fi && \
    mkdir -p /usr/share/dotnet && tar xzof /tmp/dotnet-runtime-6.0.36-linux.tar.gz -C /usr/share/dotnet && \
    tar xzof /tmp/instantclient.tgz -C /usr/local/ && \
    apt update -y && \
    APT_NGINX_VERSION=$(apt list -a nginx 2>/dev/null | grep "${NGINX_VERSION}" | awk '{print $2}' | head -n 1 ) && \
    DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y \
        nginx=${APT_NGINX_VERSION} \
        ${CHROME_NAME} && \
    apt-mark hold nginx && \
    cp -a /nginx-modules/. /usr/lib/nginx/modules/ && \
    ln -sf /usr/bin/vim.tiny /usr/bin/vim && \
    ln -sf /usr/bin/python3.12 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.12-config /usr/bin/python3-config && \
    locale-gen en_US.UTF-8 && \
    ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    wget -qO - http://fm.paodingai.com/share/5525fcf729f1003a9ab7661f5668e60d776fcd1e8c94f36660475f1fded609f8?dl=1 | python3 - && \
    # install google fonts
    wget -qO /tmp/fonts.tar.gz http://fm.paodingai.com/api/public/dl/DVb-UEdW && \
    tar xzf /tmp/fonts.tar.gz -C /opt/ && \
    mkdir -p /usr/share/fonts/truetype/ && \
    wget --quiet -O /tmp/msttcorefonts.tar.gz http://fm.paodingai.com/share/nhFR7Ag_?dl=1 && \
    tar xzvf /tmp/msttcorefonts.tar.gz -C /usr/share/fonts/truetype/ && \
    fc-cache -f -v && \
    pip3 install pip uv --upgrade --no-cache-dir && \
    uv sync --no-group dev && \
    cd /tmp && \
    wget -qO /tmp/mupdf-1.17.0-source.tar.gz http://fm.paodingai.com/api/public/dl/1DmMMNE9/mupdf-1.17.0-source.tar.gz && \
    tar xzvf mupdf-1.17.0-source.tar.gz && \
    cd mupdf-1.17.0-source && \
    export CFLAGS="-fPIC" && \
    make HAVE_X11=no HAVE_GLFW=no HAVE_GLUT=no prefix=/usr/local install && \
    uv pip uninstall pdfparser palladium calliper-diff wordinsight aipod speedy && \
    mkdir -pv /etc/supervisor/conf.d && \
    chmod +x /opt/scriber/docker/fix_permission.sh && \
    ( /opt/scriber/docker/fix_permission.sh || true ) && \
    rm -rf /opt/scriber/.dockerignore /opt/scriber/* /var/lib/apt/lists/* /tmp/* /root/.cache /etc/nginx/sites-enabled/default
