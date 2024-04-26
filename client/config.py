import sys

N = 3
GCP_ADDR     = "34.94.106.191" #2vCPU
AWS_ADDR = "54.177.190.187" # 2vCPU
AZURE_ADDR   = "104.42.77.164" #2vCPU
PARTY_ADDRS = [GCP_ADDR, AWS_ADDR, AZURE_ADDR]
AWS_PORT     = 5004
AZURE_PORT_1 = 5005
AZURE_PORT_2 = 5006
CPP_PORT = 5010
CERT_PATH = "/app/certs/"
URLS = []
USE_ROUTER = None

AWS_TP_ADDR = "54.177.245.145"
GCP_TP_ADDR = "35.236.13.119"

ROUTER_ADDR = "40.78.94.35"
ROUTER_PORT = 9000

USERNAME = "user1"

offset = 0

exec_path = {
    "gen_requests": "../pir/bazel-bin/client_gen_pir_requests_bin",
    "handle_responses": "../pir/bazel-bin/client_handle_pir_responses_bin",
}


setup = sys.argv[1]
assert setup in ["flock", "baseline"]
if setup == "baseline":
    URLS = ["https://{0}:{1}".format(PARTY_ADDRS[party_int], 443) for party_int in range(N)]
    USE_ROUTER = False
elif setup == "flock":
    URLS = [
        "https://flock-wf6p6sulza-wl.a.run.app",
        "https://pvivrsctz64i2fvtyadqp6fioa0euhix.lambda-url.us-west-1.on.aws/",
        f"https://{PARTY_ADDRS[2]}:443",
    ]
    USE_ROUTER = True