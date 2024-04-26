#!/bin/bash

# Function to run GoBen and capture output
run_goben_client() {
    server_ip=$1
    output=$(~/go/bin/goben --hosts $server_ip 2>&1)
    echo "$output"
}

run_goben_server() {
    output=$(~/go/bin/goben 2>&1)
    echo "$output"
}

run_goben_relay() {
    output=$(~/go/bin/goben --relay 2>&1)
    echo "$output"
}

# Function to parse throughput from output
parse_read_throughput() {
    output=$1
    regex='aggregate reading: ([0-9.]+) Mbps'
    if [[ $output =~ $regex ]]; then
        throughput="${BASH_REMATCH[1]}"
        echo "$throughput"
    else
        echo ""
    fi
}

parse_write_throughput() {
    output=$1
    regex='aggregate writing: ([0-9.]+) Mbps'
    if [[ $output =~ $regex ]]; then
        throughput="${BASH_REMATCH[1]}"
        echo "$throughput"
    else
        echo ""
    fi
}

# Main script
mode=$1
server_ip=$2  # Replace with server IP
repeats=10  # Duration of the test in seconds
total_throughput=0
client=0
for ((i=1; i<=10; i++)); do
    # Run GoBen and capture output
    if [[ "$mode" == "client" ]]; then
        output=$(run_goben_client $server_ip)
    elif [[ "$mode" == "server" ]]; then
        output=$(run_goben_server)
    elif [[ "$mode" == "relay" ]]; then
        output=$(run_goben_relay)
    fi
    # Parse throughput from output
    read_throughput=$(parse_read_throughput "$output")
    if [ -z "$read_throughput" ]; then
        echo "Unable to read throughput: probably using relay and is serverside"
        continue
    fi
    write_throughput=$(parse_write_throughput "$output")
    if [ -z "$read_throughput" ]; then
        echo "Unable to read throughput: probably using relay and is serverside"
        continue
    fi
    let "client++" 
    avg_throughput=$(echo "scale=2; ($read_throughput + $write_throughput) / 2" | bc)
    echo $avg_throughput Mbps
    total_throughput=$(echo "$total_throughput + $avg_throughput" | bc)
    sleep 1
done
average=$(echo "scale=4; $total_throughput / $client" | bc)
average_gbps=$(echo "scale=4; $average / 1000" | bc)

echo "Average of $repeats iterations: $average_gbps Gbps"
