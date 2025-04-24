FROM postgres:latest

ENV POSTGRES_DB=cafe_db
ENV POSTGRES_USER=cafe_user
ENV POSTGRES_PASSWORD=secure_password

COPY init.sql /docker-entrypoint-initdb.d/
