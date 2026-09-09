FROM thezake/test:v1
WORKDIR /usr/src/app
COPY . .
ENTRYPOINT ["bash", "start.sh"]
