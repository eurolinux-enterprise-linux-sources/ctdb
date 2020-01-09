#!/bin/sh

. "${TEST_SCRIPTS_DIR}/unit.sh"

define_test "3 nodes, 1 healthy"

required_result <<EOF
192.168.21.254 2
192.168.21.253 2
192.168.21.252 2
192.168.20.254 2
192.168.20.253 2
192.168.20.252 2
192.168.20.251 2
192.168.20.250 2
192.168.20.249 2
EOF

simple_test 2,2,0 <<EOF
192.168.20.249 0
192.168.20.250 1
192.168.20.251 2
192.168.20.252 0
192.168.20.253 1
192.168.20.254 2
192.168.21.252 0
192.168.21.253 1
192.168.21.254 2
EOF
