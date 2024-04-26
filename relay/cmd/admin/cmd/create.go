package admin

import (
	"github.com/relay/pkg/api"
	"github.com/spf13/cobra"
)

var createCmd = &cobra.Command{
	Use:   "create",
	Short: "Create a relay/party",
	Long:  `Create a relay/party `,
	Run: func(cmd *cobra.Command, args []string) {

	},
}

var createRelayCmd = &cobra.Command{
	Use:   "relay",
	Short: "Create a relay",
	Long:  `Create a relay `,
	Run: func(cmd *cobra.Command, args []string) {
		api.CreateRelay()
	},
}

var createUserCmd = &cobra.Command{
	Use:   "user",
	Short: "Create a user domain",
	Long:  `Create a user domain `,
	Run: func(cmd *cobra.Command, args []string) {
		name, _ := cmd.Flags().GetString("name")
		api.CreateUser(name)
	},
}

var createPartyCmd = &cobra.Command{
	Use:   "party",
	Short: "Create a party within user domain",
	Long:  `Create a party within user domain`,
	Run: func(cmd *cobra.Command, args []string) {
		name, _ := cmd.Flags().GetString("name")
		user, _ := cmd.Flags().GetString("user")
		api.CreateParty(name, user)
	},
}

func init() {
	rootCmd.AddCommand(createCmd)
	createCmd.AddCommand(createRelayCmd)
	createCmd.AddCommand(createUserCmd)
	createUserCmd.Flags().String("name", "", "User name.")
	createCmd.AddCommand(createPartyCmd)
	createPartyCmd.Flags().String("name", "", "Party name.")
	createPartyCmd.Flags().String("user", "", "User name associated.")

}
