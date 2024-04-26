#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include "json/json.h"
#include "utils/base64.h"
#include "utils/authshare_builder.h"
#include <chrono>
#include <iostream>
#include <fstream>
using namespace std;
using namespace emp;

// std::string circuit_file_location = "/app/files";
std::string circuit_file_location = "/home/ubuntu/flock/mpcauth/files";

const int nP = 2;
const int port = 6000;

int test_mpc(std::string filename) {

    std::ifstream f(filename);
    if (!f.is_open()) {
        std::cerr << "Failed to open the file." << std::endl;
        return 1;
    }

    Json::Value root;
    Json::Reader reader;
    bool parsingSuccessful = reader.parse(f, root);
    if (!parsingSuccessful) {
        std::cout << "Failed to parse JSON" << std::endl;
        return -1;
    }   

    int party = root["partyInt"].asInt() + 1;
    std::string passcode_share_b64 = root["passcodeShare"].asString();
    std::string passcode_gt_b64 = root["passcodeGroundTruth"].asString();
    std::string delta_b64 = root["delta"].asString();

    auto passcode_share_bytes = base64_decode(passcode_share_b64);
    auto passcode_gt_bytes = base64_decode(passcode_gt_b64);
    auto delta_bytes = base64_decode(delta_b64);

    auto passcode_share = AuthShareBuilder<nP>::deserialize(passcode_share_bytes);

    for (int i = 0; i < passcode_share.size(); ++i) {
        std::cout << passcode_share[i].bit_share;
    }
    std::cout << std::endl;

    auto passcode_gt = AuthShareBuilder<nP>::deserialize(passcode_gt_bytes);

    bool *delta = new bool[128];
    AuthShareBuilder<nP> ::copy_vec_to_bool_array(delta_bytes, delta);

    NetIOMP<nP> io(party, port);
	NetIOMP<nP> io2(party, port+2*(nP+1)*(nP+1)+1);
    NetIOMP<nP> *ios[2] = {&io, &io2};
    ThreadPool pool(4); 
    string file = circuit_file_location+"/comparison256.txt";

    BristolFormat cf(file.c_str());
    std::cout << "circuit loaded" << std::endl;

    CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf, delta);
    mpc->function_independent();
    mpc->function_dependent();

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
    mpc->online(&in, &out);

    std::cout << out.get_plaintext_bit(0) << std::endl;

    // Json::Value benchmark_json;

    // // Print the JSON object
    // Json::FastWriter writer;
    // std::string jsonString = writer.write(benchmark_json);
    // std::cout << jsonString;

}


int main(int argc, char** argv) {
    return test_mpc(argv[1]);
}