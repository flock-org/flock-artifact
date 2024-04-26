#include <emp-tool/emp-tool.h>
#include "emp-agmpc/emp-agmpc.h"

#include "emp-agmpc/flexible_input_output.h"

using namespace std;
using namespace emp;

const string filename = "../files/AES-non-expanded.txt";

const static int nP = 2;
int party, port;
std::string addr = "tcp://127.0.0.1:6379";
std::string username = "user1";
std::string enc_key = "82290e51cae1aced3d03a01bbae34b4baccefa313c8cc340ad91771869464a4f";


int delete_keys(std::string addr, std::string prefix) {
    Redis client(addr);
    std::vector<std::string> keys;
    client.keys(prefix, std::back_inserter(keys));
    // Use the DEL command to delete all keys
    for (const auto& key : keys) {
        client.del(key);
    }
}

void test_non_in_out(int party, int port) {
	cout << "Standard in/out without using FlexIn/FlexOut" << endl;
	cout << "compute: K = E_{010101...}(101010...); E_{010101...}(K)" << endl;

	// NetIOMP<nP> io(party, port);
	// NetIOMP<nP> io2(party, port+2*(nP+1)*(nP+1)+1);

    NetIOMP<nP> io(party, addr, username+"_io_", enc_key);
	NetIOMP<nP> io2(party, addr, username+"_io2_", enc_key);

	NetIOMP<nP> *ios[2] = {&io, &io2};
	ThreadPool pool(2*(nP-1)+2);

	BristolFormat cf(filename.c_str());

	CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
	ios[0]->flush();
	ios[1]->flush();

	mpc->function_independent();
	ios[0]->flush();
	ios[1]->flush();

	mpc->function_dependent();
	ios[0]->flush();
	ios[1]->flush();

	bool *in = new bool[cf.n1+cf.n2];
	memset(in, false, cf.n1+cf.n2);
	bool *out = new bool[cf.n3];

	if(party == ALICE) {
		for (int i = 0; i < cf.n1; i++) {
			in[i] = i % 2 == 0;
		}
	} else if (party == BOB){
		for (int i = 0; i < cf.n2; i++) {
			in[cf.n1 + i] = i % 2 == 1;
		}
	}

	mpc->online(in, out);
	ios[0]->flush();
	ios[1]->flush();

	delete mpc;

	CMPC<nP>* mpc2 = new CMPC<nP>(ios, &pool, party, &cf);
	ios[0]->flush();
	ios[1]->flush();

	mpc2->function_independent();
	ios[0]->flush();
	ios[1]->flush();

	mpc2->function_dependent();
	ios[0]->flush();
	ios[1]->flush();

	bool *in2 = new bool[cf.n1+cf.n2];
	memset(in2, false, cf.n1+cf.n2);
	bool *out2 = new bool[cf.n3];

	if(party == ALICE) {
		for (int i = 0; i < cf.n1; i++) {
			in2[i] = out[i];
		}
	} else if (party == BOB){
		for (int i = 0; i < cf.n2; i++) {
			in2[cf.n1 + i] = i % 2 == 1;
		}
	}

	mpc2->online(in2, out2);
	ios[0]->flush();
	ios[1]->flush();

	if(party == ALICE) {
		cout << "output:" << endl;
		for (int i = 0; i < cf.n3; i++) {
			cout << out2[i] << " ";
		}
		cout << endl;
	}

	delete mpc2;
}

void test_in_out(int party, int port) {
	cout << "FlexIn/FlexOut" << endl;
	cout << "compute: K = E_{010101...}(101010...); E_{010101...}(K)" << endl;

	// NetIOMP<nP> io(party, port);
	// NetIOMP<nP> io2(party, port+2*(nP+1)*(nP+1)+1);
    NetIOMP<nP> io(party, addr, username+"_io_", enc_key);
	NetIOMP<nP> io2(party, addr, username+"_io2_", enc_key);
	NetIOMP<nP> *ios[2] = {&io, &io2};
	ThreadPool pool(2*(nP-1)+2);

	BristolFormat cf(filename.c_str());

	CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
	ios[0]->flush();
	ios[1]->flush();

	mpc->function_independent();
	ios[0]->flush();
	ios[1]->flush();

	mpc->function_dependent();
	ios[0]->flush();
	ios[1]->flush();

	FlexIn<nP> in(cf.n1 + cf.n2, party);
	for(int i = 0; i < 64; i++) {
		in.assign_party(i, ALICE);
	}
	for(int i = 64; i < cf.n1; i++) {
		in.assign_party(i, -2);
	}
	for(int i = 0; i < 64; i++) {
		in.assign_party(cf.n1 + i, 0);
	}
	for(int i = 64; i < cf.n2; i++) {
		in.assign_party(cf.n1 + i, BOB);
	}

	FlexOut<nP> out(cf.n3, party);
	for(int i = 0; i < cf.n3; i++) {
		out.assign_party(i, -1);
	}

	if(party == ALICE) {
		for(int i = 0; i < 64; i++){
			in.assign_plaintext_bit(i, i % 2 == 0);
		}
		for(int i = 64; i < cf.n1; i++){
			in.assign_plaintext_bit(i, i % 2 == 0);
		}
		for(int i = 0; i < 64; i++) {
			in.assign_plaintext_bit(cf.n1 + i, i % 2 == 1);
		}
	} else {
		for(int i = 64; i < cf.n1; i++){
			in.assign_plaintext_bit(i, false);
		}
		for(int i = 0; i < 64; i++) {
			in.assign_plaintext_bit(cf.n1 + i, i % 2 == 1);
		}
		for(int i = 64; i < cf.n2; i++) {
			in.assign_plaintext_bit(cf.n1 + i, i % 2 == 1);
		}
	}

	mpc->online(&in, &out);
	ios[0]->flush();
	ios[1]->flush();

	CMPC<nP>* mpc2 = new CMPC<nP>(ios, &pool, party, &cf);
	ios[0]->flush();
	ios[1]->flush();

	mpc2->function_independent();
	ios[0]->flush();
	ios[1]->flush();

	mpc2->function_dependent();
	ios[0]->flush();
	ios[1]->flush();

	FlexIn<nP> in2(cf.n1 + cf.n2, party);
	for(int i = 0; i < cf.n1; i++) {
		in2.assign_party(i, -1);
	}
	for(int i = cf.n1; i < cf.n1 + cf.n2; i++) {
		in2.assign_party(i, BOB);
	}

	FlexOut<nP> out2(cf.n3, party);
	for(int i = 0; i < 32; i++) {
		out2.assign_party(i, ALICE);
	}
	for(int i = 32; i < 64; i++) {
		out2.assign_party(i, BOB);
	}
	for(int i = 64; i < cf.n3; i++) {
		out2.assign_party(i, 0);
	}

	for(int i = 0; i < cf.n1; i++) {
		AuthBitShare<nP> mabit = out.get_authenticated_bitshare(i);
		in2.assign_authenticated_bitshare(i, &mabit);
	}

	if(party == BOB) {
		for(int i = 0; i < cf.n2; i++) {
			in2.assign_plaintext_bit(cf.n1 + i, i % 2 == 1);
		}
	}

	mpc2->online(&in2, &out2);
	ios[0]->flush();
	ios[1]->flush();

	cout << "output:" << endl;
	if(party == ALICE) {
		for (int i = 0; i < 32; i++) {
			cout << out2.get_plaintext_bit(i) << " ";
		}
		for (int i = 32; i < 64; i++) {
			cout << "x" << " ";
		}
		for (int i = 64; i < cf.n3; i++) {
			cout << out2.get_plaintext_bit(i) << " ";
		}
	} else {
		for (int i = 0; i < 32; i++) {
			cout << "x" << " ";
		}
		for (int i = 32; i < 64; i++) {
			cout << out2.get_plaintext_bit(i) << " ";
		}
		for (int i = 64; i < cf.n3; i++) {
			cout << out2.get_plaintext_bit(i) << " ";
		}
	}
	cout << endl;

	delete mpc;
	delete mpc2;
}

int main(int argc, char** argv) {
	parse_party_and_port(argv, &party, &port);
	if(party > nP)return 0;

    if (party == 1) {
        delete_keys(addr, username);
    }

	test_non_in_out(party, port);
	cout << "============================" << endl;

    if (party == 1) {
        delete_keys(addr, username);
    }

	test_in_out(party, port);

	return 0;
}