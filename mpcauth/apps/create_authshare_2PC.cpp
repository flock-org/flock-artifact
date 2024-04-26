#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include "utils/authshare_builder.h"
#include <chrono>
#include <iostream>
#include <iterator>
using namespace std;
using namespace emp;

const int nP = 2;

void gen_deltas() {
    AuthShareBuilder<nP> builder(0);
    for (int i = 1; i <= nP; ++i) {
        auto bytes = AuthShareBuilder<nP>::serializeBlock(builder.Deltas[i]);
        std::ostream_iterator<uint8_t> out_it(std::cout);
        std::copy(bytes.begin(), bytes.end(), out_it);
    }
}

void gen_authshares(std::string input_string, block deltas[nP+1]) {
    int len = input_string.size();
    bool input_bits[len];

    for (int i = 0; i < len; ++i)
        input_bits[i] = (input_string[i] == '1');

    AuthShareBuilder<nP> builder(len, deltas);
    builder.gen_auth_share(input_bits);
    for (int i = 1; i <= nP; ++i) {
        auto bytes = AuthShareBuilder<nP>::serialize(builder.auth_shares[i]);
        // Write the bytes to standard output
        std::ostream_iterator<uint8_t> out_it(std::cout);
        std::copy(bytes.begin(), bytes.end(), out_it);
    }
}

int main(int argc, char** argv) {
    std::string func = argv[1];
    if (func == "gen_deltas") {
        gen_deltas();
    } else if (func == "gen_authshares") {
        std::string delta_path = argv[2];

        std::ifstream file(delta_path, std::ios::binary | std::ios::in);
        if (!file.is_open()) {
            std::cerr << "Could not open the file!" << std::endl;
            return 1;
        }
        const int delta_size = 16; // or any other size
        std::vector<std::uint8_t> buffer(delta_size);

        block deltas[nP+1];
        int i = 1;
        while (file.read(reinterpret_cast<char*>(buffer.data()), buffer.size())) {
            auto block = AuthShareBuilder<nP>::deserializeBlock(buffer);
            deltas[i] = block;
            i++;
        }
        std::string bin_string = argv[3];

        gen_authshares(bin_string, deltas);
    }
}