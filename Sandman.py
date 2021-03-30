# importing the datetime package and calling it by the name dt
import datetime as dt
# importing the threading package and calling it thd
import threading as thd
# importing the queue package and calling it q
import queue as q
# import the OS module so we can execute script commands
import os
# import playsound module as ps in order to be able to play a sound
import playsound as ps

"""
This is a python class. Think of it as an "object" or "box" that both contains data and has the ability to do things.
Currently works with Windows only as OS commands used are Windows based. This is an easy fix to support Linux, but I'm 
too lazy at the moment.
"""


class Sandman(thd.Thread):
    # Here we have some variable declarations. Note convention of putting a _ before variable and function names.
    # Basically a convention saying "If you mess with this outside of how it's designed to be used by the class,
    # good luck. I make no guarantees."

    # ALL VARIABLES IN THIS BLOCK ARE ASSUMED BY THE CODE TO BE STATIC DURING EXECUTION!
    # When do we want the warning to occur? Note, this is always treated as being <= 2400.
    _WARNING_TIME = 2130
    # How much time do we want between the warning and the deadline?
    _TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES = 30
    # How much time do we allow to pass before we reset (this is to prevent you from sleeping your computer and
    # having it shut itself back off right when you boot it)
    _RESET_GATE_IN_MINUTES = 1
    # Hard cut off (shutdown, true) or soft (hibernate, false)
    _HARD_CUTOFF = False
    # Path to the audio file we want to play for a warning.
    _WARNING_AUDIO_FILE_PATH = "./warning_sound.mp3"
    # Flag to allow dry runs so I don't shutdown my computer while testing a bunch.
    _TEST = False

    # Lock used to prevent multiple threads from accessing the below variables at once.
    # This isn't a "hard" lock, you as the programmer have to know to acquire it before you touch the variables below.
    _timer_lock = thd.Lock()
    # Variable to cache the warning timestamp.
    _cached_warning_timestamp = None
    # Variable to cache the reference to the threading time so we can cancel it if we choose to. Using a queue as
    # Python's queue class is good for messaging between threads. Setting max size to 1.
    _timer_cache = q.Queue(1)
    # Flag to note if we've already fired the warning.

    """
    Constructor which does things when an instance of the class is first instantiated.
    """
    def __init__(self):
        # Because this class inherits from Thread (meaning this is a thread, but a Thread is not necessarily a Sandman),
        # we need to call the constructor of Thread.
        thd.Thread.__init__(self)
        # Tell Python to acquire the lock before continuing and to release it when done.
        with self._timer_lock:
            self._cached_warning_timestamp = self._get_next_warning_timestamp()

    """
    This is a function which finds a timestamp for when the warning should be sent to you. Uses system time.
    """
    def _get_next_warning_timestamp(self):
        # create a timestamp based on the current date, but at 0 minutes into the day.
        beginning_of_day = dt.datetime.combine(dt.datetime.now().date(), dt.time.min)
        now = dt.datetime.now()
        h_and_m = self._get_hour_minute_tuple_for_warning()
        next_warning_stamp = beginning_of_day+dt.timedelta(hours=h_and_m["hours"], minutes=h_and_m["minutes"])

        while now > next_warning_stamp:
            next_warning_stamp += dt.timedelta(days=1)

        return next_warning_stamp

    """
    This function gets a dictionary containing the number of hours and minutes from the beginning of a day for the warning to occur. Forces values into range of [0, midnight) and assumes the time will be an integer representing 24 hour time.
    """
    def _get_hour_minute_tuple_for_warning(self):
        # the 100s here are to convert from/to 24 hour time.
        warning_time_above_zero = max(0, self._WARNING_TIME)
        warning_time_hours_only = int(warning_time_above_zero/100)
        warning_time_minutes_only = int(min(warning_time_above_zero-warning_time_hours_only*100, 59))
        return {"hours": warning_time_hours_only, "minutes": warning_time_minutes_only}

    """
    This is a function which finds a timestamp for when the computer should be shutdown/hibernated. Uses system time.
    Must only be called if _timer_lock has been acquired by the caller.
    """
    def _get_deadline_timestamp(self):
        # Use "is" to compare things to None,
        # https://stackoverflow.com/questions/14247373/python-none-comparison-should-i-use-is-or
        if self._cached_warning_timestamp is None:
            self._cached_warning_timestamp = self._get_next_warning_timestamp()

        return self._cached_warning_timestamp + dt.timedelta(minutes=int(max(0, self._TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES)))

    """
    This is a function handles restarting the timer or shutting down/hibernating your computer.
    """
    def _shutdown_hibernate_or_restart_timer(self):
        # Tell Python to acquire the lock before continuing and to release it when done.
        with self._timer_lock:
            if self._should_warn():
                if self._TEST:
                    print("Warning fires. " + dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                try:
                    ps.playsound(self._WARNING_AUDIO_FILE_PATH)
                    ps.playsound(self._WARNING_AUDIO_FILE_PATH)
                except ps.PlaysoundException:
                    print("Error playing warning sound. " + dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                self._mark_task_as_done_and_reset_if_needed(self._get_deadline_timestamp())
            elif self._should_shutdown_or_hibernate():
                if self._TEST:
                    print("Deadline passed. Hard cutoff:" + str(self._HARD_CUTOFF) + " " + dt.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
                    self._mark_task_as_done_and_reset_if_needed()
                else:
                    if self._HARD_CUTOFF:
                        # shutdown command, shutdown, force applications, time of 0
                        os.system("shutdown /s /f /t 0")
                    else:
                        # shutdown command, hibernate, force applications
                        os.system("shutdown /h /f")
                        # reset the timestamp and start again
                        self._cached_warning_timestamp = self._get_next_warning_timestamp()
                        self._mark_task_as_done_and_reset_if_needed(self._cached_warning_timestamp)
            else:
                self._mark_task_as_done_and_reset_if_needed(self._cached_warning_timestamp)

    """
    Function to clear _timer_cache and then call task_done on it, if the timestamp_to_use parameter is not None it calls _start_timer 
    before clearing using that parameter. 
    Must only be called if _timer_lock has been acquired by the caller.
    """
    def _mark_task_as_done_and_reset_if_needed(self, timestamp_to_use=None):
        try:
            self._timer_cache.get_nowait()  # try to clear the queue
        except q.Empty:
            pass  # if the attempt to get something from the queue fails, we don't care, just keep going

        if timestamp_to_use is not None:
            self._start_timer(timestamp_to_use)
        self._timer_cache.task_done()

    """
    Function which checks if warning time has passed, but we're not past the deadline.
    Must only be called if _timer_lock has been acquired by the caller.
    """
    def _should_warn(self):
        # shorthand for variable, it's the same reference
        ts = self._cached_warning_timestamp

        if ts is None:
            raise Exception("No timestamp for the warning was cached before it was checked.")

        # Python allows this rather mathematical looking comparison
        return ts <= dt.datetime.now() < self._get_deadline_timestamp()

    """
    Function which checks if deadline time has passed, but we're not past the reset gate.
    Must only be called if _timer_lock has been acquired by the caller.
    """
    def _should_shutdown_or_hibernate(self):
        # shorthand for variable, it's the same reference
        deadline_ts = self._get_deadline_timestamp()

        # Python allows this rather mathematical looking comparison. The \ just says "this continues on the next line"
        return deadline_ts <= dt.datetime.now() < \
            self._get_deadline_timestamp() + dt.timedelta(minutes=self._RESET_GATE_IN_MINUTES)

    """
    Function to figure out how much time to place on a timer in minutes or partial minutes. Returns 0 if the time has passed.
    Must only be called if _timer_lock has been acquired by the caller.
    """
    @staticmethod
    # Note function is static (no reference to "self")! It belongs to the class, but not any instance of the class.
    # All instances of the class can access it, though!
    def _get_time_to_next_timer_execution_in_minutes(timestamp, max_interval_time_in_minutes):
        diff = timestamp - dt.datetime.now()
        amt = min(max(0, diff.total_seconds() / 60), max_interval_time_in_minutes)
        return amt

    """
    This function starts a timer that fires every _TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES/2 minutes. Does nothing if a
    timer is currently running.
    """
    def run(self):
        # Tell Python to acquire the lock before continuing and to release it when done.
        with self._timer_lock:
            self._start_timer(self._cached_warning_timestamp)
        self._timer_cache.join()  # wait until the same number of timers have been started and completed

    """
    This function starts a timer that fires every _TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES/2 minutes. 
    Does nothing if the timer queue is full.
    Must only be called if _timer_lock has been acquired by the caller.
    """
    def _start_timer(self, timestamp):
        # Cache our timer. If there's already an active timer, this operation will fail.
        # Also note that this thread timing isn't "real time", it's a best effort based on the OS's
        # scheduling/Python's ability to execute it.
        self._timer_cache.put_nowait(thd.Timer((self._get_time_to_next_timer_execution_in_minutes(timestamp, self._TIME_FROM_WARNING_TO_DEADLINE_IN_MINUTES / 2)) * 60, self._shutdown_hibernate_or_restart_timer).start())
#Need to add a warning chime or something.>>

"""
Script that gets run immediately. Basically, if the entry point for your Python code was this script, whatever is in this if gets executed. Otherwise it's ignored. Think of it like a "main" function, but it's only "main" if this script is the entry point for all of your code.
"""
if __name__ == "__main__":
    sm = Sandman()  # create an instance of sandman
    sm.start()  # starts the SM as a thread
    sm.join()  # waits until the Sandman's run method completes.
