# schedulers/srtf.py

from collections import deque

class SRTFScheduler:
    def __init__(self, num_cpus=1, num_ios=1, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.verbose = verbose
        
        # Queues
        self.ready_queue = deque()        # Ready processes
        self.wait_queue = deque()         # Processes waiting for I/O
        self.cpu_queue = [None] * num_cpus  # Processes running on each CPU
        self.io_queue = [None] * num_ios    # Processes on I/O devices
        self.finished = []                # Completed processes
        
        self.clock = 0
    
    def add_process(self, process):
        """Add a process to the ready queue"""
        process.state = "ready"
        self.ready_queue.append(process)
    
    def step(self):
        """Execute one time step of the simulation"""
        self.clock += 1
        
        self._process_cpus()
        self._process_io_devices()
        self._dispatch_to_cpus()
        self._dispatch_to_io_devices()
    
    def _get_shortest_remaining_process(self):
        """Return the ready process with smallest remaining CPU burst"""
        shortest_process = None
        shortest_remaining_time = float('inf')
        
        for process in self.ready_queue:
            burst = process.current_burst()
            if burst and "cpu" in burst:
                remaining = burst["cpu"]
                if remaining < shortest_remaining_time:
                    shortest_remaining_time = remaining
                    shortest_process = process
        
        return shortest_process
    
    def _preemption_check(self, cpu_index):
        """Check if a ready process has shorter remaining burst than CPU process"""
        current = self.cpu_queue[cpu_index]
        if current is None:
            return
        
        shortest_ready = self._get_shortest_remaining_process()
        if shortest_ready is None:
            return
        
        current_burst = current.current_burst()
        if current_burst is None or "cpu" not in current_burst:
            return
        
        if shortest_ready.current_burst()["cpu"] < current_burst["cpu"]:
            # Preempt!
            if self.verbose:
                print(f"[Time {self.clock}] Preempting P{current.pid} with P{shortest_ready.pid}")

            # Move current CPU process back to ready queue
            current.state = "ready"
            self.ready_queue.append(current)

            # Put shortest ready process on this CPU
            self.ready_queue.remove(shortest_ready)
            shortest_ready.state = "running"
            self.cpu_queue[cpu_index] = shortest_ready

    def _process_cpus(self):
        """Process jobs currently running on CPUs and handle burst completion."""
        for cpu_index in range(self.num_cpus):
            current_process = self.cpu_queue[cpu_index]
            if current_process is not None:
                burst_done = current_process.advance_burst()

                if burst_done:
                    self.cpu_queue[cpu_index] = None

                    if current_process.is_complete():
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        # Must be an I/O burst
                        current_process.state = "waiting"
                        self.wait_queue.append(current_process)
                
                else:
                    # Check for preemption
                    self._preemption_check(cpu_index)

    def _process_io_devices(self):
        """Process I/O bursts on devices."""
        for io_index in range(self.num_ios):
            current_process = self.io_queue[io_index]
            if current_process is not None:
                burst_done = current_process.advance_burst()

                if burst_done:
                    self.io_queue[io_index] = None

                    if current_process.is_complete():
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        current_process.state = "ready"
                        self.ready_queue.append(current_process)
    
    def _dispatch_to_cpus(self):
        """Assign shortest remaining time process to any free CPU."""
        for cpu_index in range(self.num_cpus):
            if self.cpu_queue[cpu_index] is None:
                process = self._get_shortest_remaining_process()
                if process:
                    self.ready_queue.remove(process)
                    process.state = "running"
                    self.cpu_queue[cpu_index] = process

    def _dispatch_to_io_devices(self):
        """Assign waiting processes to free I/O devices."""
        for io_index in range(self.num_ios):
            if self.io_queue[io_index] is None and self.wait_queue:
                process = self.wait_queue.popleft()
                process.state = "io"
                self.io_queue[io_index] = process
