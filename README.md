# my_scripts
Repository for various small scripts I have written over the years

## Bash
- `cfn_checking` - a pair of scripts used to lint and validate CFN templates. Was used in a client's CI pipeline

## Python
- `browser_session` - Opens commonly used browser tabs at work.
- `buildkite_pipeline_generation` - automation to read a set of `pipeline.yml` files and turn them into pipelines
- `cluster_provision_by_version` - pulls version information from a web dashboard and injects it into buildkite metadata
- `geocoder_test` - Using pygeocoder to output a latitude and longitude.
- `outlook` - Uses pyautogui to open up a commonly used outlook email template.
- `rotate_ecs_ami` - zero downtime ami rotation for an ecs cluster that was using gRPC
- `QoS_switcher` - Logs into my router and enables/ disables bandwidth control.
- `sms_troll` - Using clockwork API, sends the lines of Bohemian Rhapsody one line at a time in 5~10 minute intervals
- `toTitle` - Takes whatever text is on the clipboard, and returns it in title case.
- `udp_tictactoe` - A quick experiment in using python sockets for a small project, in this case, commandline tic-tac-toe!
- `wake_on_lan` - Will wake a networked computer that has WOL enabled.

