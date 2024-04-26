package frelay

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "relay",
	Short: "Serverless Relay proxy process for function/job",
	Long: `Serverless Relay acts as a proxy for a serverless function/job which doesnt want to receive active connections. 
			Instead, it receives the messages from the functi0on, and maintains a persistent connection`,
	Run: func(cmd *cobra.Command, args []string) {

	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Whoops. There was an error while executing your CLI '%s'", err)
		os.Exit(1)
	}
}
