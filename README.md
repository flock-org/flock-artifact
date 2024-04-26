# Artifact Evaluation for Flock

Flock is a framework for developing and deploying on-demand distributed-trust. 

## Overview & Setups
We have a total of five servers. One server simulates the client and is placed in AWS, one server is used as the secure relay that routes traffic between Flock's serverless containers. The other three servers are the distributed-trust nodes, located in AWS, GCP, and Azure. 

We provide a ssh key `creds/flock.pem` that gives you access to all servers. To avoid unprotected key file error, first change the permission of the key with the following command: 
```chmod 600 creds/flock.pem```

First, Prepare 5 separate terminals and ssh into all these servers.

The client server: `ssh -i creds/flock.pem ubuntu@ec2-13-57-39-94.us-west-1.compute.amazonaws.com`

The AWS server: `ssh -i creds/flock.pem ubuntu@ec2-54-177-190-187.us-west-1.compute.amazonaws.com`

The GCP server: `ssh -i creds/flock.pem sijun@34.94.106.191`

The Azure server: `ssh -i creds/flock.pem sijuntan@104.42.77.164`

The relay: `ssh -i creds/flock.pem azureuser@40.78.94.35`


### Setting up baseline

First, ssh into all the three servers (AWS, Azure, GCP). Flock's code is package into a Docker container, and we already uploaded to Docker's container registry. Use the following command to pull the Docker image from the registry. 
```
sudo docker pull sijuntan/flock:ubuntu
```

On each server, first create a tmux session with `tmux new -s flock`. If the tmux session is already created, enter the tmux session with `tmux a -t flock`. Then execute the following command. This will start running Flock's Docker container. 

Use `sudo docker ps` to check if the container if already running. If the container is running, the terminal will output something like:
```
CONTAINER ID   IMAGE                   COMMAND                  CREATED       STATUS       PORTS                                                                                                                 NAMES
9ba698d5c895   sijuntan/flock:ubuntu   "gunicorn --certfile…"   2 hours ago   Up 2 hours   0.0.0.0:443->443/tcp, :::443->443/tcp, 0.0.0.0:5000-5200->5000-5200/tcp, :::5000-5200->5000-5200/tcp, 5201-7000/tcp   adoring_bassi
```
If so, you can stop the Docker container via `sudo docker stop <container_id>`. On each VM, start the Docker container via the following commands:

<a id="setup"></a>
AWS:
```
sudo docker run -p 443:443 -p  5000-5200:5000-5200 -e RELAY_CA="$(cat certs/frelay-ca.pem)" -e RELAY_CERT="$(cat certs/0/cert.pem)" -e RELAY_KEY="$(cat certs/0/key.pem)" -e USER_CA="$(cat certs/user1/user-ca.pem)" -e PARTY_CERT="$(cat certs/user1/1/cert.pem)" -e PARTY_KEY="$(cat certs/user1/1/key.pem)" -e STORAGE="aws" sijuntan/flock:ubuntu gunicorn --certfile="/app/certs/client.pem" --keyfile="/app/certs/client.key" --bind="0.0.0.0:443" --timeout 120 -w 8 handler:app
```

GCP:
```
sudo docker run -p 443:443 -p  5000-5200:5000-5200 -e RELAY_CA="$(cat certs/frelay-ca.pem)" -e RELAY_CERT="$(cat certs/0/cert.pem)" -e RELAY_KEY="$(cat certs/0/key.pem)" -e USER_CA="$(cat certs/user1/user-ca.pem)" -e PARTY_CERT="$(cat certs/user1/0/cert.pem)" -e PARTY_KEY="$(cat certs/user1/0/key.pem)" -e STORAGE="gcp" sijuntan/flock:ubuntu gunicorn --certfile="/app/certs/client.pem" --keyfile="/app/certs/client.key" --bind="0.0.0.0:443" --timeout 120 -w 8 handler:app
```

Azure:
```
sudo docker run -p 443:443 -p  5000-5200:5000-5200 -e RELAY_CA="$(cat certs/frelay-ca.pem)" -e RELAY_CERT="$(cat certs/2/cert.pem)" -e RELAY_KEY="$(cat certs/2/key.pem)" -e USER_CA="$(cat certs/user1/user-ca.pem)" -e PARTY_CERT="$(cat certs/user1/2/cert.pem)" -e PARTY_KEY="$(cat certs/user1/2/key.pem)" -e STORAGE="azure" sijuntan/flock:ubuntu gunicorn --certfile="/app/certs/client.pem" --keyfile="/app/certs/client.key" --bind="0.0.0.0:443" --timeout 120 -w 8 handler:app
```


### Setting up Flock & Relay
Flock has two endpoint from AWS and GCP, and share the Azure server with the baseline:

Flock's AWS Lambda endpoint: `https://pvivrsctz64i2fvtyadqp6fioa0euhix.lambda-url.us-west-1.on.aws/`

Flock's GCP cloud run endpoint: `https://flock-wf6p6sulza-wl.a.run.app`

Flock's AWS Lambda and GCP cloud run end point is already up and running. You need to additionally start the Flock relay.

Log into the relay server. The script to start the relay is in the `/relay` folder of `flock-dev`. `cd` into it and execute the following command:
```
bash start_relay.sh
```

This will start 4 relay processes running in the background. You can use `ps` to check if they are there. Also, you can use `pkill -f relay` to kill all the relay processes running in the background. 


## Reproduce Latency Results in Table 3 and Figure 4. (~30 minutes)

Log into the client server (`ubuntu@ec2-13-57-39-94.us-west-1.compute.amazonaws.com`) via ssh, and create a tmux session with `tmux new -s flock`. The latency server will sends requests to Flock's baseline server as well as serverless endpoints. 

First, go to the `client` repo where all the bash scripts are located:
```
cd flock-dev/client
```

All the following operations will be executed 10 times, and the average will be computed.
First, go to the client server and execute the following script

```
bash latency_baseline.sh
bash latency_flock.sh
python3 figure_latency.py
```

The first two lines will run all the latency experiments and save the results in the `/results` folder as json files. Then, `figure_latency.py` will read these results and generate the corresponding figure. The figure will be generated in the `./figures` folder.


## Reproduce Throughput Results in Figure 6 (~60 min)
We have an additional AWS and GCP large server that is used to benchmark throughput for baseline. This is because the both servers gets saturated before the Azure server so baseline's throughput is bottlenecked by them. Since both baseline and Flock uses the Azure server, we choose larger servers for AWS and GCP to saturate Azure in the baseline. 

AWS large server: `ec2-54-177-245-145.us-west-1.compute.amazonaws.com`

GCP large server: `sijun@35.236.13.119`

Log into these server via `creds/flock.pem`, and use the same command from [the Setup section](#setup) to start the AWS and GCP server.

The script to measure throughput is located in `client/throughput.py`. The throughput script will launch https requests in multiple threads simutaneously. It goes over a for loop of increasing number of threads, each trial lasts ~90 second, and we record the number of requests completed between 15-75 seconds. We store the throughput results in a json file in the `results` folder for each threads we tested. When drawing the figure, we will take the maximum throughput from these trials for both Flock and baseline.

```
bash throughput_baseline.sh
bash throughput_flock.sh
python3 figure_throughput.py
```

Similarly, the first two lines will run all the throughput experiments and save the results in the `/results` folder as json files. Then, `figure_throughput.py` will read these results and generate the corresponding figure. The figure will be generated in the `./figures` folder.


## Download all figures
You can download all generated figures via the following command.
```
scp -i creds/flock.pem ubuntu@ec2-13-57-39-94.us-west-1.compute.amazonaws.com:~/flock-dev/figures .
```

If everything works well, the figures should look like the following:
### Latency Figures (Figure 4)
<table>
  <tr>
    <td><img src="./figures_archive/latency_sharding_recover.png" alt="Secret Recover" width="300"></td>
    <td><img src="./figures_archive/latency_signing_sign.png" alt="Signing" width="300"></td>
    <td><img src="./figures_archive/latency_pir.png" alt="PIR" width="300"></td>
  </tr>
<tr>
    <td><img src="./figures_archive/latency_freshness_retrieve_file.png" alt="Freshness" width="300"></td>
    <td><img src="./figures_archive/latency_aes_encrypt.png" alt="Decryption" width="300"></td>
  </tr>
</table>

### Throughput Figures (Figure 6)



## Reproduce Cost Results in Table 5 and Figure 7
```
python3 cost.py
```

## Reproduce Relay Microbenchmarks in Table 4 (~30 min)

### Baseline Results (Row 1 of Table 4)

#### Throughput

Start test server on GCP, which runs goben

<<<<<<< HEAD
=======
## Reproduce Relay Microbenchmarks in Table 4

### Baseline Results 

#### Throughput

Start Goben server on GCP

```
./scripts/throughput.sh server
>>>>>>> b849bd4 (Throughput microbenchmark results)
```
~/scripts/throughput.sh server
```

Start test client on Azure, which runs goben 10 times and prints out average

```
~/scripts/throughput.sh client 34.94.106.191
```

Compare this value to "Per-Conn. Gbps" of Row 1.

#### Latency

Start server on GCP

```
cd flock-dev
export USER=user1
export NAME=1
export DEST=0
export MODE=server
./relay/bin/client_func
```

Start Client on Azure

```
cd flock-dev
export USER=user1
export NAME=0
export DEST=1
export MODE=client
export TARGET=34.94.106.191:9000
./relay/bin/client_func
```

This will print out the baseline latency over 10 iterations
Compare this value to Setup Latency (ms) Total in row 1.
Note: Expect this baseline latency to be close to 40, which is higher than the number we observed during our runs for the paper.
This is because of cloud provisioning and other factors, which could contribute to increase in baseline latency.

### Relay Results

Start Flock Relay on AWS

```
cd ~/flock-dev
./relay/bin/relay start --port 9000
```

#### Throughput

Start Goben on GCP

Set Env Variables required to contact relay

```
cd ~/flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/1/cert.pem)
export RELAY_KEY=$(cat certs/1/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/1/cert.pem)
export PARTY_KEY=$(cat certs/user1/1/key.pem)
export DEST=0
```

Start throughput test using goben

```
~/scripts/throughput.sh relay
```

Start Goben on Azure

Set Env Variables required to contact relay

```
cd ~/flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/0/cert.pem)
export RELAY_KEY=$(cat certs/0/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/0/cert.pem)
export PARTY_KEY=$(cat certs/user1/0/key.pem)
export DEST=1
```

Start throughput test using Goben

```
~/scripts/throughput.sh relay
```

Compare this value to "Per-Conn. Gbps" of Row 2.

#### Latency

Make sure the relay is running in the AWS VM

Start Client Function in GCP

```
cd ~/flock-dev
export MODE=""
export TEST=latency

./relay/bin/client_func
```

Start Client Function in Azure

```
cd ~/flock-dev

export MODE=""
export TEST=latency

./relay/bin/client_func
```
Now, S2R latency and E2E latency will be printed on the azure VM.
Note: Expect this e2e latency to be close to 70, which is higher than the number we observed during our runs for the paper.
This is because baseline latency between azure and gcp vm increased in the current setup.

Now stop the relay running in AWS VM by pressing Ctrl+c or the following command

```
killall relay
```

### Wireguard

Start Wireguard Relay on the AWS VM

```
cd ~/serverless-relay
wgrelay start --port 9000
```

Start Wireguard setup on GCP VM

```
~/scripts/wireguard.sh gcp
```

Start Wireguard setup on Azure VM

```
~/scripts/wireguard.sh azure
```

#### Throughput


Run Goben server on the GCP VM

```
~/scripts/throughput.sh server

Start client on Azure, which runs goben 10 times and prints out average

```
./scripts/throughput.sh client 34.94.106.191
```

#### Latency

Start server on GCP

```
cd flock-dev
export USER=user1
export NAME=1
export DEST=0
export MODE=server
./relay/bin/client_func
```

Start Client on azure

```
cd flock-dev
export USER=user1
export NAME=0
export DEST=1
export MODE=client
export TARGET=34.94.106.191:9000
./relay/bin/client_func
```

### Relay Results

Start Relay on AWS

```
cd ~/flock-dev
./relay/bin/relay start --port 9000
```

#### Throughput

Start Goben on GCP

Set Env Variables required to contact relay 

```
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/1/cert.pem)
export RELAY_KEY=$(cat certs/1/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/1/cert.pem)
export PARTY_KEY=$(cat certs/user1/1/key.pem)
export DEST=0
```

Start throughput test using goben

```
./scripts/throughput.sh relay
```

Start Goben on Azure

Set Env Variables required to contact relay 

```
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/0/cert.pem)
export RELAY_KEY=$(cat certs/0/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/0/cert.pem)
export PARTY_KEY=$(cat certs/user1/0/key.pem)
export DEST=1
```

Start throughput test using Goben

```
./scripts/throughput.sh relay
```

#### Latency

Start Client Function in GCP

```
cd flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/1/cert.pem)
export RELAY_KEY=$(cat certs/1/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/1/cert.pem)
export PARTY_KEY=$(cat certs/user1/1/key.pem)
export DEST=0
export TEST=latency
./relay/bin/client_func
```

Start Client Function in Azure

```
cd flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/0/cert.pem)
export RELAY_KEY=$(cat certs/0/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/0/cert.pem)
export PARTY_KEY=$(cat certs/user1/0/key.pem)
export DEST=1
export CONN=0
./relay/bin/client_func
```

### Wireguard

Start Wireguard Relay on the AWS VM

```
cd serverless-relay
wgrelay start --port 9000
```

Start Wireguard Proxy on both VMs

```
wgproxy 8000 54.177.190.187:9000 & 

```


Setup Wireguard on Azure

```
sudo ip link del wireguard1
sudo tunnel-benchmarking --tunnel-type=wireguard \
--datapath=linux --host-name=host1 \
--remote-hosts=host2:127.0.0.1 \
--wireguard-public-key=ARq3ziAZVWj5IQ202TskQEsl3GQQrQ7NnJAKOv2F5kE= \
--wireguard-private-key=uCmjq4myg7GGCZP6Shu7xXuyVzyeyedg/VhZrVJtck4= 

```

Setup Wireguard on GCP

```
sudo ip link del wireguard2
sudo tunnel-benchmarking --tunnel-type=wireguard \
--datapath=linux --host-name=host2 \
--remote-hosts=host1:127.0.0.1 \
--wireguard-public-key=/tcWr8BES3jzSbE2vGxH+PAWqEawE2/2tWe7+LUVHGU= \
--wireguard-private-key=MOp5jPFweMpLPNSgkp4CLMWzJO2Yh7ASlIQpPAQxwXA= 

```


#### Throughput


Run Goben server on the GCP VM

```
~/go/bin/goben
```

Run Goben client the Azure VM

```
~/go/bin/goben --hosts 10.201.2.1
```

### Latency

```
cd flock-dev
export USER=user1
export NAME=1
export DEST=0
export MODE=server
./relay/bin/client_func
```

Start Client on azure

```
cd flock-dev
export USER=user1
export NAME=0
export DEST=1
export MODE=client
export TARGET=34.94.106.191:9000
./relay/bin/client_func
```

Run Goben client the Azure VM

```
~/scripts/throughput.sh client 10.201.2.1
```

Compare this value to "Per-Conn. Gbps" of Row 1.

### Latency

Rerun Wireguard setup on Azure VM, and setup latency would be printed

```
~/scripts/wireguard.sh azure
```

Note: The latency we observed for all benchmarks would be increasing by a factor due to the current setup. However, the pattern would remain the same, e.g. baseline latency would be lower than the total latency observed with relay which would be lesser than that of wireguard
Baseline < Relay < Wireguard is what our results convey.

## Scale (Concurrent Users) tests of relay

Make sure relay is running in AWS VM using the following command

```
cd ~/flock-dev/
./relay/bin/relay start --port 9000
```

Make sure the following env variables are set in GCP VM

```
cd ~/flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/1/cert.pem)
export RELAY_KEY=$(cat certs/1/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/1/cert.pem)
export PARTY_KEY=$(cat certs/user1/1/key.pem)
export DEST=0

```

Make sure the following env variables are set in Azure VM

```
cd ~/flock-dev
export RELAY=54.177.190.187:9000
export RELAY_CA=$(cat certs/frelay-ca.pem)
export RELAY_CERT=$(cat certs/0/cert.pem)
export RELAY_KEY=$(cat certs/0/key.pem)
export USER_CA=$(cat certs/user1/user-ca.pem)
export PARTY_CERT=$(cat certs/user1/0/cert.pem)
export PARTY_KEY=$(cat certs/user1/0/key.pem)
export DEST=1

```

Run the throughput scale test on Azure and GCP VM with signing operation

```
cd ~/flock-dev
~/scripts/scale_ops.sh signing
```

The Total throughput will be printed on the screen after few minutes.

Once this is finished, run the throughput scale test with decrypt option on Azure and GCP VM

```
cd ~/flock-dev
~/scripts/scale_ops.sh decrypt
```

The Total throughput will be printed on the screen after few minutes.

## Contact us
If you run into any questions,  leave a comment or ask questions in HotCRP or email us through `sijuntan@berkeley.edu` and `daryakaviani@berkeley.edu`

