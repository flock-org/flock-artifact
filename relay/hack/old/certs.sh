#!/bin/bash
# call this script with an email address (valid or not).
# like:
# ./certs.sh joe@random.com
mkdir certs
rm certs/*
echo "make server cert"
openssl req -new -nodes -x509 -out certs/server1.pem -keyout certs/server1.key -days 3650 -subj "/C=DE/ST=NRW/L=Earth/O=Random Company2/OU=IT/CN=www.random2.com/emailAddress=$1"
echo "make client cert"
openssl req -new -nodes -x509 -out certs/client1.pem -keyout certs/client1.key -days 3650 -subj "/C=DE/ST=NRW/L=Earth/O=Random Company2/OU=IT/CN=www.random2.com/emailAddress=$1"