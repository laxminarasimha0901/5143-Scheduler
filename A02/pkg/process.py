# process.py

class Process:
    """
    Represents a process with CPU and I/O bursts
    Attributes:
        pid: unique process ID
        bursts: list of bursts [{"cpu": X}, {"io": {"type": T, "duration": D}}, ...]
        priority: scheduling priority (0 = highest)
        state: current state ("new", "ready", "running", "waiting", "finished")
    Methods:
        current_burst(): returns the current burst or None if done
        advance_burst(): advances the burst by one time unit, returns True if burst completed
        __repr__(): string representation for debugging
        __str__(): user-friendly string representation
    """

    def __init__(self, pid, bursts, priority=0, arrival_time=0, quantum=4):
        """Initialize process with pid, bursts, and priority"""
        self.pid = pid
        self.bursts = bursts[:]  # [{"cpu": X}, {"io": {...}}, ...]
        self.priority = priority
        self.arrival_time = arrival_time
        self.quantum = quantum
        self.state = "new"
        
        # Track progress within current burst
        self.current_burst_index = 0
        self.time_in_burst = 0

        self.wait_time = 0  # Total time spent waiting in wait queue or ready queue
        self.turnaround_time = 0  # Total time from arrival to completion
        self.runtime = 0  # Total CPU time used
        self.io_time = 0  # Total I/O time used
        self.start_time = 0  # Time when the process started execution
        self.end_time = 0  # Time when the process finished execution
        self.init_cpu_bursts = 0
        self.init_io_bursts = 0
        for burst in bursts:
            if "cpu" in burst:
                self.init_cpu_bursts += burst["cpu"]
            elif "io" in burst:
                self.init_io_bursts += burst["io"]["duration"]
        self.TotalBursts = self.init_cpu_bursts + self.init_io_bursts

    def current_burst(self):
        """Get the current burst"""
        if self.current_burst_index < len(self.bursts):
            return self.bursts[self.current_burst_index]
        return None

    def advance_burst(self):
        """
        Advance the current burst by one time unit
        Returns True if the burst is completed, False otherwise
        """
        if self.current_burst_index >= len(self.bursts):
            return False
        
        burst = self.bursts[self.current_burst_index]
        self.time_in_burst += 1
        
        # Check if burst is complete
        burst_complete = False
        if "cpu" in burst:
            if self.time_in_burst >= burst["cpu"]:
                burst_complete = True
                self.runtime += burst["cpu"]
        elif "io" in burst:
            if self.time_in_burst >= burst["io"]["duration"]:
                burst_complete = True
                self.io_time += burst["io"]["duration"]
        
        # Move to next burst if current one is complete
        if burst_complete:
            self.current_burst_index += 1
            self.time_in_burst = 0
            return True
        
        return False

    def is_complete(self):
        """Check if all bursts have been completed"""
        return self.current_burst_index >= len(self.bursts)

    def __repr__(self):
        return f"{self.pid}"

    def __str__(self):
        return f"Process[pid:{self.pid}, priority:{self.priority}, runtime:{self.runtime}, io_time:{self.io_time}, start_time:{self.start_time}]"
        