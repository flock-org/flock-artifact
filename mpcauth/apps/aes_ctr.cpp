#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include <chrono>
#include "json/json.h"
using namespace std;
using namespace emp;

// std::string circuit_file_location = "/app/files";
std::string circuit_file_location = "/home/ubuntu/flock/mpcauth/files";
const int nP = 3;

PRG prg;
bool delta[128];

int run_agmpc(int party, NetIOMP<nP> *ios[2], FlexIn<nP> *in, FlexOut<nP> *out, std::string circuit_name, Json::Value &benchmark_json) {
    string file = circuit_file_location+"/"+circuit_name+".txt";
    BristolFormat cf(file.c_str());
    ThreadPool pool(4); 

    // Benchmarking setup phase
    auto start_setup = std::chrono::high_resolution_clock::now();
    CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf, delta);
    ios[0]->flush();
	ios[1]->flush();
    auto end_setup = std::chrono::high_resolution_clock::now();
    auto setup_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_setup - start_setup);

    if (benchmark_json.isMember(circuit_name+"_setup_time")) {
        benchmark_json[circuit_name+"_setup_time"] = benchmark_json[circuit_name+"_setup_time"].asDouble() + setup_duration.count();
    } else {
         benchmark_json[circuit_name+"_setup_time"] = setup_duration.count();
    }

    // Benchmarking function independent phase
    auto start_func_ind = std::chrono::high_resolution_clock::now();
    mpc->function_independent();
    ios[0]->flush();
	ios[1]->flush();
    auto end_func_ind = std::chrono::high_resolution_clock::now();
    auto func_ind_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_func_ind - start_func_ind);

    if (benchmark_json.isMember(circuit_name+"_func_ind_time")) {
        benchmark_json[circuit_name+"_func_ind_time"] = benchmark_json[circuit_name+"_func_ind_time"].asDouble() + func_ind_duration.count();
    } else {
        benchmark_json[circuit_name+"_func_ind_time"] = func_ind_duration.count();
    }

    // Benchmarking function dependent phase
    auto start_func_dep = std::chrono::high_resolution_clock::now();
    mpc->function_dependent();
    ios[0]->flush();
	ios[1]->flush();
    auto end_func_dep = std::chrono::high_resolution_clock::now();
    auto func_dep_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_func_dep - start_func_dep);
    if (benchmark_json.isMember(circuit_name+"_func_dep_time")) {
        benchmark_json[circuit_name+"_func_dep_time"] = benchmark_json[circuit_name+"_func_dep_time"].asDouble() + func_dep_duration.count();
    } else {
        benchmark_json[circuit_name+"_func_dep_time"] = func_dep_duration.count();
    }

    // cout <<"========= PARTY "<<party<<" BENCHMARKS =========\n";
    // cout <<"Time to run setup for party "<< party << ": " << setup_duration.count() << " ms\n";

    // cout <<"Time to run function independent phase for party "<< party << ": " << func_ind_duration.count() << " ms\n";

    // cout <<"Time to run function dependent phase for party "<< party << ": " << func_dep_duration.count() << " ms\n";

    auto start_online = std::chrono::high_resolution_clock::now();
    mpc->online(in, out);
    auto end_online = std::chrono::high_resolution_clock::now();
    auto online_duration = std::chrono::duration_cast<std::chrono::duration<double>>(end_online - start_online);
    // cout <<"Time to run online phase for party "<< party << ": " << func_dep_duration.count() << " ms\n";
    if (benchmark_json.isMember(circuit_name+"_online_time")) {
        benchmark_json[circuit_name+"_online_time"] = benchmark_json[circuit_name+"_online_time"].asDouble() + online_duration.count();
    } else {
        benchmark_json[circuit_name+"_online_time"] = online_duration.count();
    }
    ios[0]->flush();
	ios[1]->flush();
    delete mpc;
}

int handler(std::string payload) {
    Json::Value root;
    Json::Reader reader;
    bool parsingSuccessful = reader.parse(payload, root);
    // std::cout << payload << std::endl;
    if (!parsingSuccessful) {
        std::cout << "Failed to parse JSON" << std::endl;
        return -1;
    }
    int party = root["partyInt"].asInt() + 1;
	std::string key_share = root["keyShare"].asString();
    std::string input_share = root["inputShare"].asString();
    std::string file_location = root["circuitFileLocation"].asString();
    std::string cert_path = root["certPath"].asString();
    std::vector<std::string> ip_addrs;
    const Json::Value ipAddressesJson = root["ipAddrs"];
    for (const auto& ip : ipAddressesJson) {
        ip_addrs.push_back(ip.asString());
    }

    int port = root["port"].asInt();
    if (file_location != "") {
        circuit_file_location = file_location;
    }

    bool use_router = root["useRouter"].asBool();
    NetIOMP<nP> *ios[2];
    if (use_router) {
        std::string username = root["username"].asString();
        std::string router_ip = root["routerAddr"].asString();
        int router_port = root["routerPort"].asInt();
        std::string server_ip = ip_addrs.at(3);
        std::string tag1 = "io_";
        std::string tag2 = "io2_";
        ios[0] = new NetIOMP<nP>(party, port, router_port, cert_path, router_ip, server_ip, username, tag1);
        ios[1] = new NetIOMP<nP>(party, port+2*(nP+1), router_port, cert_path, router_ip, server_ip, username, tag2);
    } else {
        ios[0] = new NetIOMP<nP>(party, port, cert_path, ip_addrs);
        ios[1] = new NetIOMP<nP>(party, port+2*(nP+1), cert_path, ip_addrs);
    }
 
    int n_blocks = input_share.size() / 128;
    // add padding
    if (n_blocks * 128 != input_share.size()) {
        n_blocks += 1;
        int n_pad = n_blocks * 128 - input_share.size();
        for (int i = 0; i < n_pad; ++i)
            input_share += "0";
    }

    std::string out_share = "";
    Json::Value bench_json;

    for (int j = 0; j < n_blocks; ++j) {
        int offset = j * 128;    

        FlexIn<nP> in(256, party);
        FlexOut<nP> out(128, party);
 
        // first 128 bit is the AES key (key_share)
        for (int i = 0; i < 128; ++i){
            in.assign_party(i, -2);
            in.assign_plaintext_bit(i, key_share[i] == '1');

            out.assign_party(i, -1);
        }
        for (int i = 128; i < 256; ++i) {
            in.assign_party(i, 0);
            in.assign_plaintext_bit(i, i % 2); // iv
        }
        run_agmpc(party, ios, &in, &out, "AES-non-expanded", bench_json);

        // FlexIn<nP> in2(256, party);
        // FlexOut<nP> out2(128, party);
        // for (int i = 0; i < 128; ++i) {
        //     in2.assign_party(i, -2);
        //     in2.assign_plaintext_bit(i, input_share[i+offset] == '1'); // set plaintext bit
        // }
        // for (int i = 128; i < 256; ++i) {
        //     in2.assign_party(i, -1);
        //     AuthBitShare<nP> mabit = out.get_authenticated_bitshare(i-128);
        //     in2.assign_authenticated_bitshare(i, &mabit);
        // }
        // for (int i = 0; i < 128; ++i) {
        //     out2.assign_party(i, -1);
        // }
        // run_agmpc(party, ios, &in2, &out2, "xor128", bench_json);
        // for (int i = 0; i < 128; ++i) {
        //     out_share += out2.get_authenticated_bitshare(i).bit_share ? '1':'0';
        // }
    }
    bench_json["aes_ctr_out_share"] = out_share;
    bench_json["aes_ctr_bandwidth"] = ios[0]->count() + ios[1]->count();

    // Print json string to stdout
    Json::FastWriter writer;
    std::string jsonString = writer.write(bench_json);
    std::cout << jsonString;

	return 0;
}

int main(int argc, char** argv) { 
    prg.random_bool(delta, 128);
    return handler(argv[1]);   
}