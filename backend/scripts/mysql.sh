#!/bin/sh

# Example Login Script for MySQL

set -eux

backend_root=$(realpath $(dirname $(dirname $0)))

cd $backend_root

mysql --defaults-file=$backend_root/conf/my.cnf
