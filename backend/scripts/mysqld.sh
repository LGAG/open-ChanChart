#!/bin/sh

# Example Startup Script for MySQL

set -eux

backend_root=$(realpath $(dirname $(dirname $0)))

cd $backend_root

if [ -f mysql/data/localhost.pid ]; then
    kill $(cat mysql/data/localhost.pid)
    sleep 3s
fi

if [ -d mysql ]; then
    rm -r mysql
fi

mkdir -p mysql/logs mysql/data

which mysqld

mysqld \
    --defaults-file=$backend_root/conf/my.cnf \
    --datadir=$backend_root/mysql/data \
    --init-file=$backend_root/conf/mysql-init.txt \
    --log-error=$backend_root/mysql/mysql.err \
    --initialize_insecure

mysqld \
    --defaults-file=$backend_root/conf/my.cnf \
    --datadir=$backend_root/mysql/data \
    --init-file=$backend_root/conf/mysql-init.txt \
    --log-error=$backend_root/mysql/mysql.err
