#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include "json/json.h"
#include "utils/base64.h"
#include "utils/authshare_builder.h"
#include <chrono>
#include <iostream>
using namespace std;
using namespace emp;

// std::string circuit_file_location = "/app/files";
std::string circuit_file_location = "/home/ubuntu/flock/mpcauth/files";

const int nP = 2;

int compare_passcode(std::string payload) {
    auto start_e2e = std::chrono::high_resolution_clock::now();

    Json::Value root;
    Json::Reader reader;
    bool parsingSuccessful = reader.parse(payload, root);
    if (!parsingSuccessful) {
        std::cout << "Failed to parse JSON" << std::endl;
        return -1;
    }

    int party = root["partyInt"].asInt() + 1;
	std::string passcode_share_b64 = root["passcodeShare"].asString();
    std::string passcode_gt_b64 = root["passcodeGroundTruth"].asString();
    std::string file_location = root["circuitFileLocation"].asString();
    std::string delta_b64 = root["delta"].asString();
    std::vector<std::string> ip_addrs;
    const Json::Value ipAddressesJson = root["ipAddrs"];
    for (const auto& ip : ipAddressesJson) {
        ip_addrs.push_back(ip.asString());
    }

    auto passcode_share_bytes = base64_decode(passcode_share_b64);
    auto passcode_gt_bytes = base64_decode(passcode_gt_b64);
    auto delta_bytes = base64_decode(delta_b64);

    auto passcode_share = AuthShareBuilder<nP>::deserialize(passcode_share_bytes);
    auto passcode_gt = AuthShareBuilder<nP>::deserialize(passcode_gt_bytes);
    bool *delta = new bool[128];
    AuthShareBuilder<nP> ::copy_vec_to_bool_array(delta_bytes, delta);
    std::string cert_path = root["certPath"].asString();

    int port = root["port"].asInt();
    if (file_location != "") {
        circuit_file_location = file_location;
    }

    NetIOMP<nP> io(party, port, cert_path, ip_addrs);
	NetIOMP<nP> io2(party, port+2*(nP+1), cert_path, ip_addrs);
    NetIOMP<nP> *ios[2] = {&io, &io2};
    ThreadPool pool(4); 
    string file = circuit_file_location+"/comparison256.txt";

    BristolFormat cf(file.c_str());
    std::cout << "circuit loaded" << std::endl;

    // Declare a JSON object
    Json::Value benchmark_json;

    // Benchmarking setup phase
    auto start_setup = std::chrono::high_resolution_clock::now();
    CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf, delta);
    auto end_setup = std::chrono::high_resolution_clock::now();
    auto setup_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_setup - start_setup);
    benchmark_json["auth_passcode_setup_time"] = setup_duration.count();

    // Benchmarking function independent phase
    auto start_func_ind = std::chrono::high_resolution_clock::now();
    mpc->function_independent();
    auto end_func_ind = std::chrono::high_resolution_clock::now();
    auto func_ind_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_func_ind - start_func_ind);
    benchmark_json["auth_passcode_func_ind_time"] = func_ind_duration.count();

    // Benchmarking function dependent phase
    auto start_func_dep = std::chrono::high_resolution_clock::now();
    mpc->function_dependent();
    auto end_func_dep = std::chrono::high_resolution_clock::now();
    auto func_dep_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_func_dep - start_func_dep);
    benchmark_json["auth_passcode_func_dep_time"] = func_dep_duration.count();

    FlexIn<nP> in(cf.n1+cf.n2, party);
    FlexOut<nP> out(cf.n3, party); 

    for (int i = 0; i < cf.n1+cf.n2; ++i) {
        in.assign_party(i, -1);
    }
    std::copy(passcode_share.begin(), passcode_share.end(), in.authenticated_share_assignment.begin());
    std::copy(passcode_gt.begin(), passcode_gt.end(), in.authenticated_share_assignment.begin()+cf.n1);

    // Output is plaintext
    for (int i = 0; i < cf.n3; ++i) {
        out.assign_party(i, 0);
    }

    auto start_online = std::chrono::high_resolution_clock::now();
    mpc->online(&in, &out);
    auto end_online = std::chrono::high_resolution_clock::now();
    auto online_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_online - start_online);
    benchmark_json["auth_passcode_online_time"] = online_duration.count();
    benchmark_json["auth_passcode_result"] = out.get_plaintext_bit(0);
    benchmark_json["auth_passcode_bandwidth"] = io.count() + io2.count();

    auto end_e2e = std::chrono::high_resolution_clock::now();
    auto e2e_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_e2e - start_e2e);
    benchmark_json["auth_passcode_e2e_time"] = e2e_duration.count();

    // Print the JSON object
    Json::FastWriter writer;
    std::string jsonString = writer.write(benchmark_json);
    std::cout << jsonString;

    delete mpc;
    return 0;
}

int main(int argc, char** argv) {    
    return compare_passcode(argv[1]);
}