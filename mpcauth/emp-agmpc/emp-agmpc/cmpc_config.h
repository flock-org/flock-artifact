#ifndef __CMPC_CONFIG
#define __CMPC_CONFIG
const static int abit_block_size = 1024;
const static int fpre_threads = 1;
#define LOCALHOST
// #define USE_ROUTER

#ifdef __clang__
	#define __MORE_FLUSH
#endif

// const static char *IP[] = {"",
// 	"34.102.85.227",
// 	"13.52.217.80",
// 	"13.52.182.120"
// };

const static char *IP[] = {"",
	"127.0.0.1",
	"127.0.0.1",
	"127.0.0.1"
};

const static bool lan_network = false;
#endif// __C2PC_CONFIG
