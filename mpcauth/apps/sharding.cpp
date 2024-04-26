#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include <chrono>
#include "json/json.h"
using namespace std;
using namespace emp;

const std::string circuit_file_location = "../files";
std::string data_dir = "../data/";

std::pair<std::string, std::string> read_shards(std::string file_path) {
    std::ifstream file(file_path);

    Json::Value root;
    file >> root;
    std::string key_share = root["key_share"].asString();
    std::string passcode_share = root["passcode_share"].asString();

    return std::make_pair(passcode_share, key_share);
}

int compare_passcode(int argc, char** argv) {
	int port, party;
	parse_party_and_port(argv, &party, &port);

	const static int nP = 3;

    NetIOMP<nP> io(party, port);
	NetIOMP<nP> io2(party, port+2*(nP+1)*(nP+1)+1);
    
    NetIOMP<nP> *ios[2] = {&io, &io2};
    ThreadPool pool(4); 
    string file = circuit_file_location+"/comparison256.txt";

    BristolFormat cf(file.c_str());

    // Benchmarking setup phase
    auto start_setup = std::chrono::high_resolution_clock::now();
    CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
    auto end_setup = std::chrono::high_resolution_clock::now();
    auto setup_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_setup - start_setup);

    // Benchmarking function independent phase
    auto start_func_ind = std::chrono::high_resolution_clock::now();
    mpc->function_independent();
    auto end_func_ind = std::chrono::high_resolution_clock::now();
    auto func_ind_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_func_ind - start_func_ind);

    // Benchmarking function dependent phase
    auto start_func_dep = std::chrono::high_resolution_clock::now();
    mpc->function_dependent();
    auto end_func_dep = std::chrono::high_resolution_clock::now();
    auto func_dep_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_func_dep - start_func_dep);

    std::cout <<"========= PARTY "<<party<<" BENCHMARKS =========\n";
    std::cout <<"Time to run setup for party "<< party << ": " << setup_duration.count() << " ms\n";

    std::cout <<"Time to run function independent phase for party "<< party << ": " << func_ind_duration.count() << " ms\n";

    std::cout <<"Time to run function dependent phase for party "<< party << ": " << func_dep_duration.count() << " ms\n";

    FlexIn<nP> in(cf.n1+cf.n2, party);
    FlexOut<nP> out(cf.n3, party);

    std::string shard_gt_file = data_dir+"shard"+to_string(party)+"_gt.json";
    std::string shard_file = data_dir+"shard"+to_string(party)+".json";
    auto shard_gt = read_shards(shard_gt_file).first;
    auto shard = read_shards(shard_file).first;

    // Both party 1 and party 2 has unauthenticated shares
    for (int i = 0; i < cf.n1+cf.n2; ++i) {
        in.assign_party(i, -2);
    }
    for (int i = 0; i < cf.n1; ++i){
        in.assign_plaintext_bit(i, shard[i]=='1');
	}
    for(int i = 0; i < cf.n2; ++i){
        in.assign_plaintext_bit(i+cf.n1, shard_gt[i]=='1');
	}
    // Output is plaintext
    for (int i = 0; i < cf.n3; ++i) {
        out.assign_party(i, 0);
    }
	auto start_online = std::chrono::high_resolution_clock::now();
    mpc->online(&in, &out);
    auto end_online = std::chrono::high_resolution_clock::now();
    auto online_duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_online - start_online);
	uint64_t band2 = io.count();
    std::cout <<"Bandwidth of party "<<party<<": "<<band2<< std::endl;
    std::cout << "Output:" << out.get_plaintext_bit(0) << std::endl;

	delete mpc;
	return 0;
}

int main(int argc, char** argv) {    
    compare_passcode(argc, argv);
}