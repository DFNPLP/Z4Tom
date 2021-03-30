# Z4Tom
Program I wrote in Python to help a friend get to bed on time, and maybe he'll learn some Python along the way.

Currently this script only works with Windows. This can be pretty easily modified in the "os" calls to be Linux compatible. Make sure to "pip install -r requirements.txt" before running.

Run python Sandman.py to do a one off run. You may need to run with admin permissions (launch your console as an administrator) in order to affect a shutdown. MAKE SURE THAT YOU TRUST ALL THE PACKAGES THAT ARE BEING USED BEFORE DOING THIS.

If you want this to run every time you start your computer, take a look around online: https://stackoverflow.com/questions/4438020/how-to-start-a-python-file-while-windows-starts


## Configuration
The code has values which you can change.

1. _WARNING_TIME: The time in 24 hour time as an integer. Time when your warning will occur.
2. _TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES: The time past the _WARNING_TIME in minutes you want the deadline to be.
3. _HARD_CUTOFF: False for hibernating. True for shutdown at the deadline.
4. _WARNING_AUDIO_FILE_PATH: Path to the audio file used for the warning. Defaults to "./warning_sound.mp3".


## Gotchas and Things to Note

1. It is theoretically possible if you return from a hibernate or sleep where the machine will warn you, or just shut down, right when you start the machine if it's right at the end time you've set. Just keep that in mind.