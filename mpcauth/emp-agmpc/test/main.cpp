// #include <aws/lambda-runtime/runtime.h>
#include <emp-tool/emp-tool.h>
#include "emp-agmpc/emp-agmpc.h"
// #include <sw/redis++/redis++.h>

// #include "network/comm.h"
#include <iostream>
#include <string>
#include <vector>
#include <memory>
#include <thread>
#include <condition_variable>


using namespace sw::redis;
using namespace std;
using namespace emp;

// using namespace aws::lambda_runtime;

const string circuit_file_location = macro_xstr(EMP_CIRCUIT_PATH) + string("bristol_format/");
static char out3[] = "92b404e556588ced6c1acd4ebf053f6809f73a93";//bafbc2c87c33322603f38e06c3e0f79c1f1b1475";

// static invocation_response test_agmpc(invocation_request const& req)
// {
//     if (req.payload.length() > 42) {
//         return invocation_response::failure("error message here"/*error_message*/,
//                                             "error type here" /*error_type*/);
//     }

//     int port, party;
//     port = 8000;
//     party = 1;
// 	// // parse_party_and_port(argv, &party, &port);

// 	const static int nP = 3;
// 	NetIOMP<nP> io(party, port);
// 	NetIOMP<nP> io2(party, port+2*(nP+1)*(nP+1)+1);
// 	NetIOMP<nP> *ios[2] = {&io, &io2};
// 	ThreadPool pool(4);	
// 	string file = circuit_file_location+"/AES-non-expanded.txt";
// 	file = circuit_file_location+"/sha-1.txt";
// 	BristolFormat cf(file.c_str());

// 	CMPC<nP>* mpc = new CMPC<nP>(ios, &pool, party, &cf);
// 	cout <<"Setup:\t"<<party<<"\n";

// 	mpc->function_independent();
// 	cout <<"FUNC_IND:\t"<<party<<"\n";

// 	mpc->function_dependent();
// 	cout <<"FUNC_DEP:\t"<<party<<"\n";

// 	bool in[512]; bool out[160];
// 	memset(in, false, 512);
// 	mpc->online(in, out);
// 	uint64_t band2 = io.count();
// 	cout <<"bandwidth\t"<<party<<"\t"<<band2<<endl;
// 	cout <<"ONLINE:\t"<<party<<"\n";
// 	if(party == 1) {
// 		string res = "";
// 		for(int i = 0; i < cf.n3; ++i)
// 			res += (out[i]?"1":"0");
// 		cout << hex_to_binary(string(out3))<<endl;
// 		cout << res<<endl;
// 		cout << (res == hex_to_binary(string(out3))? "GOOD!":"BAD!")<<endl<<flush;
// 	}
// 	delete mpc;
//     return invocation_response::success("json payload here" /*payload*/,
//                                         "application/json" /*MIME type*/);
// }


// struct CommConfig {
// 	int rank;
// 	int party_size;
// 	int enc_key;
// 	std::string addr;
// 	std::string username;
// };

// class RedisComm {
// public:
//     RedisComm(CommConfig &config)
//     {
// 		conf_ = config;
// 		client_ = new Redis(config.addr);
	
// 		for (int i = 0; i < config.party_size; ++i) {
// 			if (config.rank == i) continue;
// 			std::string chan = config.username + "-" + std::to_string(i) + "-" + std::to_string(config.rank);
// 			channels_.emplace_back(chan);
// 		}

//         for (const auto& channel : channels_) {
//             subscribers_.emplace_back(client_->subscriber());
//         }

//     	// Subscribe to each channel
// 		for (size_t i = 0; i < channels_.size(); i++) {
//             subscribers_[i].on_message([this](const std::string& channel, const std::string& msg) {
// 				// std::unique_lock<std::mutex> lock(mutex_);
// 				mutex_.lock();
// 				std::cout << "received messages!" << std::endl;
// 				messages_[channel].push(msg);
// 				mutex_.unlock();
// 				// cond_var_.notify_all();
// 			});
//             subscribers_[i].subscribe(channels_[i]);
//         }

// 		// std::vector<std::thread> threads(subscribers_.size());
// 		listeners_.resize(subscribers_.size());
// 		for (int i = 0; i < subscribers_.size(); ++i) {
// 			listeners_[i] = std::thread(listen, std::ref(subscribers_[i]));
// 			listeners_[i].detach();
// 		}
//     }

// 	void send(int dst, const std::string& message) {
// 		std::string chan = conf_.username + "-" + std::to_string(conf_.rank) + "-" + std::to_string(dst);
// 		std::cout << "Published to channel: " << chan << std::endl;
//         client_->publish(chan, message);
//     }

// 	std::string recv(int src) {
// 		std::string chan = conf_.username + "-" + std::to_string(src) + "-" + std::to_string(conf_.rank);
//         std::cout << "recv from channel: " << chan << std::endl;

//         // Wait for a message to be received
//         while (messages_[chan].empty()) {
// 			continue;
//         }
//         // Get the message from the queue and remove it
// 		mutex_.lock();
//         std::string msg = messages_[chan].front();
//         messages_[chan].pop();
// 		mutex_.unlock();

// 		return msg;
//     }

// 	static void listen(sw::redis::Subscriber &sub) {
// 		while (true) {
// 			try {
// 				sub.consume();
// 			} catch (const Error &err) {
// 				std::cout << "terminate" << std::endl;
// 			}
// 		}
// 	}

// private:
//     Redis* client_;
//     std::vector<Subscriber> subscribers_;
//     std::vector<std::string> channels_;
//     std::unordered_map<std::string, std::queue<std::string>> messages_;
//     std::mutex mutex_;
//     std::condition_variable cond_var_;
// 	std::vector<std::thread> listeners_;

// 	CommConfig conf_;
// };


int main(int argc, char **argv) {
	int rank = atoi(argv[1]);
	std::cout << "rank: " << rank << std::endl;

	CommConfig config = {};
	config.addr = "tcp://127.0.0.1:6379";
	config.rank = rank;
	config.party_size = 2;
	config.username = "sijun";

	std::string chan = "channel_0_1";
	RedisChan channel(chan);

	if (rank == 0) {
		channel.send("hello world");
	} else {
		auto msg = channel.recv();
		std::cout << "msg: " << msg << std::endl; 
	}

    return 0;
}