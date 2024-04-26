#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include "network/comm.h"
#include "json/json.h"
using namespace std;
using namespace emp;

const std::string circuit_file_location = "../files";
static char out3[] = "92b404e556588ced6c1acd4ebf053f6809f73a93";//bafbc2c87c33322603f38e06c3e0f79c1f1b1475";

std::string share11 = "1011000100001010001010111010110100001000001110010001010000010010101011110101001011101111111011010100011001111001111100010011011000001011010000101011110111010010000101000011111101101111110100111101101011110001010001111100101000010101111111100111111111010110";
std::string share12 = "1110010001011111011111101111100001011101011011000100000101000111111110100000011110111010101110000001001100101100101001000110001101011110000101111110100010000111010000010110101000111010100001101000111110100100000100101001111101000000101010110010101010000011";
std::string share21 = "0101000010101011100010101000000100101010011111111100111011000111000000100001100000001100101101001101100001111010101110100111101110001010111101110011010100100111011010100000011010011100010101100110000011010000010100110101101100101100101101100010111100001101";
std::string share22 = "0000010111111110110111111101010001111111001010101001101110010010010101110100110101011001111000011000110100101111111011110010111011011111101000100110000001110010001111110101001111001001000000110011010110000101000001100000111001111001111000110111101001011000";

bool **to_xor_shares_plain(bool *input, int len, int nP) {
    bool mask[len];
    bool **shares;
    shares = new bool*[nP];
    for (int i = 0; i < nP; ++i)
        shares[i] = new bool[len];

    memcpy(shares[0], input, len);
    for (int i = 1; i < nP; ++i) {
        PRG prg;
	    prg.random_bool(shares[i], len);
        for (int j = 0; j < len; ++j) {
            shares[0][j] ^= shares[i][j];
        }
    }
    
    // print share
    for (int i = 0; i < nP; ++i) {
        std::cout << "Share " << i << ":";
        for (int j = 0; j < len; ++j) {
            std::cout << shares[i][j];
        }
        std::cout << std::endl;
    }
    return shares;
}

// vector<string> to_xor_shares(bool *input, int len, int nP) {
//     bool **shares = to_xor_shares_plain(input, len, nP);

//     // Create a vector of strings to store the shares
//     vector<string> share_strings(nP);

//     // Convert the bool arrays to strings and store them in the vector
//     for (int i = 0; i < nP; ++i) {
//         for (int j = 0; j < len; ++j) {
//             share_strings[i] += shares[i][j] ? '1' : '0';
//         }
//     }

//     // Free the memory allocated for the shares
//     for (int i = 0; i < nP; ++i) {
//         delete[] shares[i];
//     }
//     delete[] shares;

//     // Return the vector of strings
//     return share_strings;
// }

// vector<string> to_xor_shares(vector<bool> input, int nP) {
//     int len = key.size();
//     bool *input = new bool[key.size()];
//     vector<string> shares = to_xor_shares(input, key.size(), nP);
//     delete[] input;
//     return shares;
// }

vector<string> to_xor_shares(const vector<bool>& input, int nP) {
    int len = input.size();
    bool **shares = new bool*[nP];
    for (int i = 0; i < nP; ++i) {
        shares[i] = new bool[len];
    }

    // Copy input to shares[0]
    for (int i = 0; i < len; ++i) {
        shares[0][i] = input[i];
    }

    for (int i = 1; i < nP; ++i) {
        PRG prg;
        prg.random_bool(shares[i], len);
        for (int j = 0; j < len; ++j) {
            shares[0][j] ^= shares[i][j];
        }
    }

    // Create a vector of strings to store the shares
    vector<string> share_strings(nP);

    // Convert the bool arrays to strings and store them in the vector
    for (int i = 0; i < nP; ++i) {
        for (int j = 0; j < len; ++j) {
            share_strings[i] += shares[i][j] ? '1' : '0';
        }
    }

    // Free the memory allocated for the shares
    for (int i = 0; i < nP; ++i) {
        delete[] shares[i];
    }
    delete[] shares;

    // Return the vector of strings
    return share_strings;
}


std::vector<bool> convert_to_binary(const std::string& input) {
    std::vector<bool> binary_array;
    binary_array.reserve(input.size() * 8); // Reserve enough space for the binary representation
    for (char c : input) {
        for (int i = 7; i >= 0; --i) {
            binary_array.push_back((c >> i) & 1);
        }
    }
    return binary_array;
}

// bool* convert_to_binary(const std::string& input) {
//     if (input.size() > 32) {
//         std::cerr << "Only support string below 32 bytes" << std::endl;
//     }
//     int array_size = 256;
//     bool* binary_array = new bool[array_size];
//     memset(binary_array, 0, array_size);
//     for (size_t i = 0; i < input.size(); ++i) {
//         char c = input[i];
//         for (int j = 7; j >= 0; --j) {
//             binary_array[i * 8 + (7 - j)] = (c >> j) & 1;
//         }
//     }
//     return binary_array;
// }

// bool* convert_to_binary(const std::string& input, int &array_size) {
//     array_size = input.size() * 8;
//     bool* binary_array = new bool[array_size];

//     for (size_t i = 0; i < input.size(); ++i) {
//         char c = input[i];
//         for (int j = 7; j >= 0; --j) {
//             binary_array[i * 8 + (7 - j)] = (c >> j) & 1;
//         }
//     }

//     return binary_array;
// }

// After storing the passcode and the key as plaintext, upload the whole code block into cloud

// When checking for correctness, each party receieves a share as input, and then compare to the locally. If correct, return the key.


int test_comparison(int argc, char** argv) {
	int port, party;
	parse_party_and_port(argv, &party, &port);

	std::string enc_key = "82290e51cae1aced3d03a01bbae34b4baccefa313c8cc340ad91771869464a4f"; // 256-bit key

	const static int nP = 2;
	auto addr = "tcp://127.0.0.1:6379";
	std::string username = "user1";

	NetIOMP<nP> io(party, addr, username+"_io_", enc_key);
	NetIOMP<nP> io2(party, addr, username+"_io2_", enc_key);
	NetIOMP<nP> *ios[2] = {&io, &io2};
	ThreadPool pool(4);	
	string file = circuit_file_location+"/comparison256.txt";

	BristolFormat cf(file.c_str());
	std::cout << cf.n1 << " " << cf.n2 << " " << cf.n3;

	CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
	cout <<"Setup:\t"<<party<<"\n";

	mpc->function_independent();
	cout <<"FUNC_IND:\t"<<party<<"\n";

	mpc->function_dependent();
	cout <<"FUNC_DEP:\t"<<party<<"\n";

    FlexIn<nP> in(cf.n1+cf.n2, party);
    FlexOut<nP> out(cf.n3, party);

    // Both party 1 and party 2 has unauthenticated shares
    for (int i = 0; i < cf.n1+cf.n2; ++i) {
        in.assign_party(i, -2);
    }
    for (int i = 0; i < cf.n1; ++i){
        if (party == 1) {
            in.assign_plaintext_bit(i, share21[i]=='1');
        } else if (party == 2) {
            in.assign_plaintext_bit(i, share22[i]=='1');
        }
	}
    for(int i = 0; i < cf.n2; ++i){
        if (party == 1) {
            in.assign_plaintext_bit(i+cf.n1, share11[i]=='1');
        } else if (party == 2) {
            in.assign_plaintext_bit(i+cf.n1, share12[i]=='1');
        }
	}
    // Output is plaintext
    for (int i = 0; i < cf.n3; ++i) {
        out.assign_party(i, 0);
    }
	mpc->online(&in, &out);
	uint64_t band2 = io.count();

	cout <<"bandwidth\t"<<party<<"\t"<<band2<<endl;
	cout <<"ONLINE:\t"<<party<<"\n";
    std::cout << "Output:" << out.get_plaintext_bit(0) << std::endl;

	delete mpc;
	return 0;
}


std::pair<std::string, std::string> read_shards(std::string file_path) {
    std::ifstream file(file_path);

    Json::Value root;
    file >> root;
    std::string key_share = root["key_share"].asString();
    std::string passcode_share = root["passcode_share"].asString();

    return std::make_pair(passcode_share, key_share);
}

int main(int argc, char** argv) {
    // bool *input = new bool[256];
    // bool passcode[256];
    // for (int i = 0; i < 256; ++i) {
    //     passcode[i] = i % 2;
    // }
    // bool **shares = to_xor_shares(input, 256, 2);

    // for (int i = 0; i < 10; ++i) {
    //     std::cout << (share11[i]=='1') << std::endl;
    // }

    // auto pair = read_shards("../data/shard1.json");

    // std::string passcode = "12345678";
    // std::string key = "82290e51cae1aced3d03a01bbae34b4baccefa313c8cc340ad91771869464a4";
    // upload_sk<2>(passcode, key);
    
    test_comparison(argc, argv);
}