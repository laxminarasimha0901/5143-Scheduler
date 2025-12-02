# schedulers/rr.py

from collections import deque

class RRScheduler:
    def __init__(self, num_cpus=1, num_ios=1, quantum=4, verbose=False):
        self.num_cpus = num_cpus
        self.num_ios = num_ios
        self.quantum = quantum
        self.verbose = verbose
        
        # Queues
        self.ready_queue = deque()      # Ready processes
        self.wait_queue = deque()      # Processes waiting for I/O
        self.cpu_queue = [None] * num_cpus  # Currently running processes on each CPU
        self.io_queue = [None] * num_ios   # Currently running processes on each I/O device
        self.finished = []              # Completed processes
        
        self.clock = 0
        self.total_context_switches = 0
    
    def add_process(self, process):
        """Add a process to the ready queue"""
        process.remaining_quantum = process.quantum
        self.ready_queue.append(process)
    
    def step(self):
        """Execute one time step of the simulation"""
        self.clock += 1
        
        # Handle process arrivals
        self._handle_arrivals()
        
        # Process currently running jobs on CPUs
        self._process_cpus()
        
        # Process currently running jobs on I/O devices
        self._process_io_devices()
        
        # Dispatch ready processes to available CPUs
        self._dispatch_to_cpus()
        
        # Dispatch waiting processes to available I/O devices
        self._dispatch_to_io_devices()

    def has_jobs(self):
        return (len(self.ready_queue) > 0 or 
                len(self.wait_queue) > 0 or 
                any(p is not None for p in self.cpu_queue) or 
                any(p is not None for p in self.io_queue))
    
    def _handle_arrivals(self):
        """Move processes from new state to ready queue when they arrive"""
        arrived_processes = []
        for process in self.ready_queue:
            if process.state == "new" and process.arrival_time <= self.clock:
                process.state = "ready"
                arrived_processes.append(process)
        
        # Move arrived processes to the end of the ready queue
        for process in arrived_processes:
            self.ready_queue.append(self.ready_queue.popleft())
    
    def _process_cpus(self):
        """Process currently running jobs on all CPUs"""
        for cpu_index in range(self.num_cpus):
            current_process = self.cpu_queue[cpu_index]
            if current_process is not None:
                # Decrement remaining quantum
                current_process.remaining_quantum -= 1
                
                # Advance the current burst
                burst_completed = current_process.advance_burst()
                
                # Check if process should be preempted due to quantum expiration
                if current_process.remaining_quantum <= 0 and not burst_completed:
                    # Quantum expired, preempt the process
                    current_process.state = "ready"
                    self.ready_queue.append(current_process)
                    self.cpu_queue[cpu_index] = None
                    self.total_context_switches += 1
                elif burst_completed:
                    # Burst completed
                    self.cpu_queue[cpu_index] = None
                    if current_process.is_complete():
                        # Process is completely finished
                        current_process.state = "finished"
                        current_process.end_time = self.clock
                        current_process.turnaround_time = self.clock - current_process.arrival_time
                        self.finished.append(current_process)
                    else:
                        # Next burst is I/O, move to wait queue
                        current_process.state = "waiting"
                        self.wait_queue.append(current_process)
    
