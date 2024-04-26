#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
#include "network/comm.h"
using namespace std;
using namespace emp;


const std::string circuit_file_location = "../files";

// const string circuit_file_location = macro_xstr(EMP_CIRCUIT_PATH) + string("bristol_format/");
static char out3[] = "92b404e556588ced6c1acd4ebf053f6809f73a93";//bafbc2c87c33322603f38e06c3e0f79c1f1b1475";

int flushall() {
	auto addr = "tcp://127.0.0.1:6379";
	Redis client(addr);
	client.flushall();
}

void clear_channels(int nP, int party, std::string addr, std::string username) {
	Redis redis(addr);
	for (int i = 0; i < nP; ++i) {
		if (party == i) continue;
		std::vector<std::string> keys;
		auto key1 = username+"_io_"+std::to_string(party)+"_"+std::to_string(i);
		auto key2 = username+"_io2_"+std::to_string(party)+"_"+std::to_string(i);

		redis.del(key1);
		redis.del(key2);
	}
}

int test_agmpc(int argc, char** argv) {
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
	// string file = circuit_file_location+"/AES-non-expanded.txt";
	string file = circuit_file_location+"/comparison256.txt";

	BristolFormat cf(file.c_str());
	std::cout << cf.n1 << " " << cf.n2 << " " << cf.n3;

	CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
	cout <<"Setup:\t"<<party<<"\n";

	mpc->function_independent();
	cout <<"FUNC_IND:\t"<<party<<"\n";

	mpc->function_dependent();
	cout <<"FUNC_DEP:\t"<<party<<"\n";

	bool *in = new bool[cf.n1+cf.n2]; bool *out = new bool[cf.n3];
	memset(in, false, cf.n1+cf.n2);
	mpc->online(in, out);
	uint64_t band2 = io.count();

	cout <<"bandwidth\t"<<party<<"\t"<<band2<<endl;
	cout <<"ONLINE:\t"<<party<<"\n";
	if(party == 1) {
		string res = "";
		for(int i = 0; i < cf.n3; ++i)
			res += (out[i]?"1":"0");
		cout << hex_to_binary(string(out3))<<endl;
		cout << res<<endl;
	}
	delete mpc;
	return 0;
}

int main(int argc, char** argv) {
    test_agmpc(argc, argv);
}