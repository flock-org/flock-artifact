./bin/relay start --port 9000 2>&1 | tee >(cat > relay.log) & 
./bin/relay start --port 9001 2>&1 | tee -a >(cat >> relay.log) & 
./bin/relay start --port 9002 2>&1 | tee -a >(cat >> relay.log) & 
./bin/relay start --port 9003 2>&1 | tee -a >(cat >> relay.log) &