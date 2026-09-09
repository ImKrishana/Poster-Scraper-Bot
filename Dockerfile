FROM thezake/test:v1
WORKDIR /usr/src/app
COPY requirements.txt .
RUN uv pip install --python /zakevenv/bin/python --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["bash", "start.sh"]
