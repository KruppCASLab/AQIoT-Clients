# Raspberry pi 3 B+ IP script and systemd service file

The `send_ip.sh` file is a bash script that sends the current IP address of your pi to `https://caslab.case.edu/team/` when you reboot/power on your pi. It requires one command line argument: a label which represents the owner of the pi.

The `send-ip.service` file is a systemd service file that runs the script on the pi on reboot.

Please follow the steps below to set up the script and service file.

## 1. Get path to send_ip.sh file
Get the path to the `send_ip.sh` file. You can leave it in this pi3/utils directory of the repo or move it somewhere else.

## 2. Move send-ip.service file
Move `send-ip.service` to the `/etc/systemd/system/` directory.

## 3. Fill in send-ip.service file with your information
Replace the comments with the correct information for your pi's configuration. Remember to include a label argument!

## 4. Enable service with systemctl
After you have finished the previous steps and saved your changes, run `sudo systemctl enable send-ip.service` to enable the service file. Now, the script should be fully working! You can test by running `sudo reboot` and visiting `https://caslab.case.edu/team/` after. Your pi's IP address should appear with the label that you used in the service folder.

## Troubleshooting
There are a few helpful commands you can run on your pi to troubleshoot:
`sudo systemctl status send-ip.service` - tells you the status of the service. It should say 'active' if working.
`sudo journalctl -u send-ip.service' - logging information for the service. Check here to see any possible errors that occurred when the service attempted to run.

## Extra info
Here is some more information about the different fields in the `send-ip.service` file:
`Description` - simple description of what the service does. Appears in logging information.
`After` - service should run after this condition has been met.
`Wants` - service wants this condition to be met.

`ExecStart` - specifying the main process to run.
`Type` - configures how the service notifies the manager that start-up has finished. Here, we use `oneshot`, which starts up the service after the main process has finished. This gives the pi time to set up/initialize before we try to grab its IP address.
`RemainAfterExit` - used in conjunction with `oneshot`, this means the service will still be marked as `active` even after its process (the IP script) has finished.

`WantedBy` - designating at what point to run the service. `multi-user.target` means that the system is in a state where all network services have started up and is accepting logins.

If you want to read more about systemd services, please feel free to look here: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
