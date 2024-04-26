#include "emp-tool/emp-tool.h"
#include "emp-agmpc/emp-agmpc.h"
using namespace std;
using namespace emp;

void test_netio(int party) {
	auto addr = "35.88.19.4";
	int port = 6666;
	std::string username = "user1";
	std::string tag = "channel1";

	std::string enc_key = "82290e51cae1aced3d03a01bbae34b4baccefa313c8cc340ad91771869464a4f"; 
	auto io = NetIO(addr, port, tag, enc_key);
	std::string str = "hello world";

	char recv_msg[20];
	if (party == 1) {
		io.send_data_internal(str.c_str(), str.length());
		io.recv_data_internal(recv_msg, str.length());
		std::cout << recv_msg << std::endl;
	} else {
		io.recv_data_internal(recv_msg, str.length());
		io.send_data_internal(str.c_str(), str.length());
		std::cout << recv_msg << std::endl;
	}
}

int main(int argc, char** argv) {
	int party = atoi(argv[1]);
    test_netio(party);
}